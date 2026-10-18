"""Local SQLite or bounded Firestore metadata with private immutable GCS originals."""
import copy
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException


class LocalSession:
    def __init__(self, con, owner):
        self.con, self.owner = con, owner

    def get(self, kind, id):
        row = self.con.execute('SELECT data FROM records WHERE owner=? AND kind=? AND id=?', (self.owner, kind, id)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, kind):
        return [json.loads(row[0]) for row in self.con.execute('SELECT data FROM records WHERE owner=? AND kind=? ORDER BY rowid', (self.owner, kind))]

    def put(self, kind, id, value):
        self.con.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?)', (self.owner, kind, id, json.dumps(value)))

    def delete(self, kind, id):
        self.con.execute('DELETE FROM records WHERE owner=? AND kind=? AND id=?', (self.owner, kind, id))

    def image_put(self, id, mime, body):
        self.con.execute('INSERT INTO images VALUES(?,?,?,?)', (self.owner, id, mime, body))

    def image_get(self, id):
        row = self.con.execute('SELECT mime,body FROM images WHERE owner=? AND id=?', (self.owner, id)).fetchone()
        return dict(row) if row else None


class LocalStore:
    def __init__(self, root):
        Path(root).mkdir(parents=True, exist_ok=True)
        self.path = Path(root) / 'dose-timer.sqlite3'
        with sqlite3.connect(self.path) as con:
            con.execute('CREATE TABLE IF NOT EXISTS records (owner TEXT, kind TEXT, id TEXT, data TEXT, PRIMARY KEY(owner,kind,id))')
            con.execute('CREATE TABLE IF NOT EXISTS images (owner TEXT, id TEXT, mime TEXT, body BLOB, PRIMARY KEY(owner,id))')

    @contextmanager
    def session(self, owner):
        con = sqlite3.connect(self.path, timeout=15)
        con.row_factory = sqlite3.Row
        try:
            con.execute('BEGIN IMMEDIATE')
            yield LocalSession(con, owner)
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def reserve(self, kind):
        pass


class CloudSession:
    def __init__(self, snapshot, bucket, owner):
        self.snapshot, self.bucket, self.owner = snapshot, bucket, owner
        self.records = copy.deepcopy((snapshot.to_dict() or {}).get('records', {}))
        self.before = copy.deepcopy(self.records)

    def get(self, kind, id):
        return copy.deepcopy(self.records.get(kind, {}).get(id))

    def all(self, kind):
        values = copy.deepcopy(list(self.records.get(kind, {}).values()))
        return sorted(values, key=lambda v: (v.get('created_at') or v.get('confirmed_at') or v.get('reported_at') or '', v.get('id', '')))

    def put(self, kind, id, value):
        self.records.setdefault(kind, {})[id] = copy.deepcopy(value)

    def delete(self, kind, id):
        self.records.get(kind, {}).pop(id, None)

    def image_put(self, id, mime, body):
        blob = self.bucket.blob(f'dose-timer/{self.owner}/{id}')
        blob.upload_from_string(body, content_type=mime, if_generation_match=0, timeout=30)
        self.put('image', id, {'name': blob.name, 'generation': int(blob.generation), 'mime': mime,
            'sha256': hashlib.sha256(body).hexdigest()})

    def image_get(self, id):
        record = self.get('image', id)
        if not record:
            return None
        body = self.bucket.blob(record['name'], generation=record['generation']).download_as_bytes(timeout=30)
        if hashlib.sha256(body).hexdigest() != record['sha256']:
            raise HTTPException(409, 'Original image integrity check failed.')
        return {'body': body, 'mime': record['mime']}


class CloudStore:
    def __init__(self, project, bucket):
        from google.cloud import firestore, storage
        self.firestore = firestore
        self.client = firestore.Client(project=project)
        self.bucket = storage.Client(project=project).bucket(bucket)

    @contextmanager
    def session(self, owner):
        from google.api_core.exceptions import AlreadyExists, FailedPrecondition, Conflict
        ref = self.client.collection('dose_timer_users').document(owner)
        snapshot = ref.get()
        session = CloudSession(snapshot, self.bucket, owner)
        yield session
        if session.records == session.before:
            return
        if len(json.dumps(session.records).encode()) > 800000:
            raise HTTPException(409, 'Prototype storage limit reached; existing data was retained.')
        try:
            # One owner aggregate changes atomically. No blind last-write-wins.
            if snapshot.exists:
                ref.update({'records': session.records}, option=self.firestore.LastUpdateOption(snapshot.update_time))
            else:
                ref.create({'records': session.records})
        except (AlreadyExists, FailedPrecondition, Conflict):
            raise HTTPException(409, 'Data changed in another request. Refresh and retry.') from None
        # A failed metadata commit can leave an unreferenced private image. It is
        # intentionally retained, never deleted on an ambiguous commit result.

    def reserve(self, kind):
        day = datetime.now(timezone.utc).date().isoformat()
        ref = self.client.collection('dose_timer_limits').document(f'{kind}-{day}')

        @self.firestore.transactional
        def increment(transaction):
            snapshot = ref.get(transaction=transaction)
            count = (snapshot.to_dict() or {}).get('count', 0)
            limit = 100
            if count >= limit:
                raise HTTPException(429, 'Daily shared demo limit reached. Please try again tomorrow.')
            transaction.set(ref, {'count': count + 1})

        increment(self.client.transaction())
