"""Cloud routing checks without credentials; optional real Firestore emulator CAS checks."""
import os
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import server
from persistence import LocalStore, CloudStore


def test_cloud_auth_isolates_users_and_never_accepts_local_token(monkeypatch, tmp_path):
    import cloud_identity
    monkeypatch.setenv('CLOUD_MODE', 'true')
    monkeypatch.setenv('FIREBASE_PROJECT_ID', 'demo-dose-timer')
    monkeypatch.setenv('IMAGE_BUCKET', 'synthetic-private-bucket')
    monkeypatch.setenv('FIREBASE_WEB_API_KEY', 'synthetic-public-auth-key')
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic-secret-not-real')
    monkeypatch.setenv('WEB_DIST', str(Path(__file__).parents[1] / 'frontend' / 'dist'))
    monkeypatch.setattr(server, 'CloudStore', lambda *args: LocalStore(tmp_path))

    def verify(value):
        if value in ('Bearer firebase-a', 'Bearer firebase-b'):
            return value[-1]
        raise HTTPException(401)

    monkeypatch.setattr(cloud_identity, 'verifier', lambda project: verify)
    with TestClient(server.create_app(mode='gemini')) as client:
        assert client.get('/').status_code == 200
        assert client.get('/config').json() == {'cloud': True, 'firebase_api_key': 'synthetic-public-auth-key'}
        assert 'synthetic-secret' not in client.get('/config').text
        assert client.get('/api/state').status_code == 401
        client.headers['Authorization'] = 'Bearer local-token-at-least-thirty-two-characters'
        assert client.get('/api/state').status_code == 401
        client.headers['Authorization'] = 'Bearer firebase-a'
        image = (Path(__file__).parents[1] / 'samples' / 'medication.png').read_bytes()
        result = client.post('/api/documents?kind=medication', files={'file': ('sample.png', image, 'image/png')})
        assert result.status_code == 200
        id = result.json()['id']
        assert len(client.get('/api/state').json()['documents']) == 1
        client.headers['Authorization'] = 'Bearer firebase-b'
        assert client.get('/api/state').json()['documents'] == []
        assert client.get(f'/api/documents/{id}/image').status_code == 404
        assert client.post(f'/api/documents/{id}/extract').status_code == 404
        client.headers['Authorization'] = 'Bearer firebase-a'
        assert client.get(f'/api/documents/{id}/image').content == image


@pytest.mark.skipif(not os.environ.get('DOSE_FIRESTORE_TEST'), reason='Requires local Firestore emulator')
def test_firestore_cas_and_global_quota():
    import uuid
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore
    assert os.environ.get('FIRESTORE_EMULATOR_HOST'), 'Never run this against a real cloud project'
    store = CloudStore.__new__(CloudStore)
    store.firestore = firestore
    store.client = firestore.Client(project='demo-dose-timer', credentials=AnonymousCredentials())
    store.bucket = None
    owner = uuid.uuid4().hex
    with store.session(owner) as con:
        con.put('routine', 'one', {'id': 'one', 'created_at': '2026-10-18T01:00:00Z'})
    with pytest.raises(HTTPException) as error:
        with store.session(owner) as first:
            first.put('routine', 'one', {'id': 'one', 'name': 'stale'})
            with store.session(owner) as second:
                second.put('routine', 'one', {'id': 'one', 'name': 'current'})
    assert error.value.status_code == 409
    with store.session(owner) as con:
        assert con.get('routine', 'one')['name'] == 'current'
    from datetime import datetime, timezone
    quota_kind = 'test-' + uuid.uuid4().hex
    day = datetime.now(timezone.utc).date().isoformat()
    ref = store.client.collection('dose_timer_limits').document(f'{quota_kind}-{day}')
    ref.set({'count': 99})
    store.reserve(quota_kind)
    with pytest.raises(HTTPException) as error:
        store.reserve(quota_kind)
    assert error.value.status_code == 429
    assert ref.get().to_dict()['count'] == 100
