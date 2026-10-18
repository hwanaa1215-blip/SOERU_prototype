import io
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
from server import create_app

TOKEN = "synthetic-test-access-token-at-least-32-characters"
SAMPLES = Path(__file__).parents[1] / "samples"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(TOKEN, tmp_path, mode="sample", demo=True)) as c:
        c.headers["Authorization"] = f"Bearer {TOKEN}"
        yield c


def upload(client, kind="medication", content=None):
    return client.post(f"/api/documents?kind={kind}", files={"file": ("image.png", content or (SAMPLES / f"{kind}.png").read_bytes(), "image/png")})


def routine(client, doc, attempt=None, **updates):
    now = datetime.fromisoformat(client.get('/api/state').json()['now']).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Seoul'))
    return {"request_key": uuid.uuid4().hex, "document_id": doc['id'], "attempt_id": attempt, "kind": doc['kind'], "name": "Fictional item", "strength": "5 mg", "dose": "1 tablet", "instruction": "Fictional fixed daily instructions", "times": [(now + timedelta(minutes=2)).strftime('%H:%M')], "start_date": now.date().isoformat(), "end_date": (now + timedelta(days=1)).date().isoformat(), "confirmed": True, **updates}


def test_full_dual_source_confirmation_and_reminder(client):
    for kind in ['medication', 'supplement']:
        doc = upload(client, kind).json()
        attempt = client.post(f"/api/documents/{doc['id']}/extract").json()
        assert attempt['source'] == 'sample' and attempt['status'] == 'unverified'
        if kind == 'medication':
            assert client.get('/api/state').json()['routines'] == []
        payload = routine(client, doc, attempt['id'], name=f'Fictional {kind}')
        assert client.post('/api/routines', json=payload).status_code == 200
    state = client.get('/api/state').json()
    assert {o['kind'] for o in state['occurrences']} == {'medication', 'supplement'}
    event = state['occurrences'][0]
    assert client.post(f"/api/occurrences/{event['id']}/taken").status_code == 409
    assert client.put('/api/demo/clock', json={'at': event['due']}).status_code == 200
    assert all(o['status'] == 'due' for o in client.get('/api/state').json()['occurrences'])
    first = client.post(f"/api/occurrences/{event['id']}/taken")
    assert first.status_code == 200
    assert client.post(f"/api/occurrences/{event['id']}/taken").json() == first.json()
    assert client.get('/api/state').json()['occurrences'][0]['status'] == 'taken'
    assert client.post(f"/api/routines/{event['routine_id']}/stop").status_code == 200
    assert len(client.get('/api/state').json()['occurrences']) == 1


def test_confirmation_and_time_validation(client):
    doc = upload(client).json()
    for update in [{'confirmed': False}, {'times': ['24:00']}, {'times': ['09:00','09:00']}, {'times': []}, {'dose': ' '}, {'end_date': '2099-01-01'}]:
        assert client.post('/api/routines', json=routine(client, doc, **update)).status_code == 422
    assert not client.get('/api/state').json()['routines']
    assert client.post('/api/routines', json=routine(client, doc, kind='supplement')).status_code == 409


def test_failed_reading_stays_separate_from_manual_confirmation(client):
    from PIL import Image
    output = io.BytesIO(); Image.new('RGB', (30, 30), 'blue').save(output, format='PNG')
    doc = upload(client, content=output.getvalue()).json()
    assert client.post(f"/api/documents/{doc['id']}/extract").status_code == 503
    attempt = client.get(f"/api/documents/{doc['id']}/attempts").json()[0]
    assert attempt['status'] == 'failed'
    assert client.post('/api/routines', json=routine(client, doc, attempt['id'])).status_code == 409
    saved = client.post('/api/routines', json=routine(client, doc))
    assert saved.json()['provenance'] == 'manual'
    assert client.get(f"/api/documents/{doc['id']}/attempts").json()[0]['status'] == 'failed'


def test_authentication_and_cross_identity_ownership(client, tmp_path):
    doc = upload(client).json()
    # A separate authenticated local identity sharing a database cannot access records.
    with TestClient(create_app('a-different-synthetic-token-over-32-characters', tmp_path, 'sample', True)) as other:
        other.headers['Authorization'] = 'Bearer a-different-synthetic-token-over-32-characters'
        assert other.get(f"/api/documents/{doc['id']}/image").status_code == 404
        assert other.post(f"/api/documents/{doc['id']}/extract").status_code == 404
        assert other.get(f"/api/documents/{doc['id']}/attempts").status_code == 404
        assert other.post('/api/routines', json=routine(client, doc)).status_code == 404
        assert other.get('/api/state').json()['documents'] == []
    client.headers.pop('Authorization')
    assert client.get('/api/state').status_code == 401
    assert upload(client).status_code == 401


def test_image_limits_and_original_preservation(client):
    assert upload(client, content=b'not an image').status_code == 422
    assert upload(client, content=b'0' * (5 * 1024 * 1024 + 1)).status_code == 413
    doc = upload(client).json()
    result = client.get(f"/api/documents/{doc['id']}/image")
    assert result.content == (SAMPLES / 'medication.png').read_bytes()
    assert result.headers['cache-control'] == 'no-store'


def test_attempt_ownership_and_real_clock_gate(client, tmp_path):
    doc1, doc2 = upload(client).json(), upload(client).json()
    attempt = client.post(f"/api/documents/{doc1['id']}/extract").json()
    assert client.post('/api/routines', json=routine(client, doc2, attempt['id'])).status_code == 409
    with TestClient(create_app(TOKEN, tmp_path, 'sample', False)) as real:
        real.headers['Authorization'] = f'Bearer {TOKEN}'
        assert real.put('/api/demo/clock', json={'at': '2026-10-17T10:00:00+09:00'}).status_code == 404
        assert real.delete('/api/demo/clock').status_code == 404


def test_reading_limit_does_not_block_manual_entry(client):
    doc = upload(client).json()
    for _ in range(20):
        assert client.post(f"/api/documents/{doc['id']}/extract").status_code == 200
    assert client.post(f"/api/documents/{doc['id']}/extract").status_code == 429
    assert client.post('/api/routines', json=routine(client, doc)).status_code == 200


def test_confirmation_retry_does_not_duplicate_routine(client):
    doc = upload(client).json()
    payload = routine(client, doc)
    first = client.post('/api/routines', json=payload)
    assert client.post('/api/routines', json=payload).json() == first.json()
    assert len(client.get('/api/state').json()['routines']) == 1
    assert client.post('/api/routines', json={**payload, 'dose': 'changed'}).status_code == 409
