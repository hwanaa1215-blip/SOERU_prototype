"""Synthetic-data demo with isolated local and authenticated cloud modes."""
import hashlib
import hmac
import io
import os
import re
import threading
import uuid
import warnings
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator

from extraction import extract
from persistence import LocalStore, CloudStore

SEOUL = ZoneInfo("Asia/Seoul")
MAX_IMAGE = 5 * 1024 * 1024


class Routine(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    document_id: str
    request_key: str = Field(min_length=16, max_length=100)
    attempt_id: str | None = None
    kind: Literal["medication", "supplement"]
    name: str = Field(min_length=1, max_length=160)
    strength: str = Field(default="", max_length=160)
    dose: str = Field(min_length=1, max_length=160)
    instruction: str = Field(default="", max_length=1000)
    times: list[str] = Field(min_length=1, max_length=6)
    start_date: date
    end_date: date
    confirmed: Literal[True]

    @model_validator(mode="after")
    def validate_dates_times(self):
        if not 0 <= (self.end_date - self.start_date).days <= 89:
            raise ValueError("Choose a date range of 1–90 days.")
        if len(set(self.times)) != len(self.times) or any(
            not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", t) for t in self.times
        ):
            raise ValueError("Enter distinct times in HH:MM format.")
        self.times.sort()
        return self


class Clock(BaseModel):
    at: datetime


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        size = 0

        async def bounded_receive():
            nonlocal size
            message = await receive()
            size += len(message.get("body", b""))
            if size > MAX_IMAGE + 65536:
                raise HTTPException(413, "Image must be at most 5 MiB.")
            return message

        return await self.app(scope, bounded_receive, send)


def create_app(token=None, data_dir=None, mode=None, demo=None):
    cloud = os.environ.get("CLOUD_MODE", "false") == "true"
    token = token or os.environ.get("LOCAL_ACCESS_TOKEN", "")
    if not cloud and len(token) < 32:
        raise RuntimeError("Use start.ps1 or provide a private LOCAL_ACCESS_TOKEN of at least 32 characters.")
    mode = mode or os.environ.get("EXTRACTION_MODE", "sample")
    if mode not in {"sample", "gemini"}:
        raise RuntimeError("Unknown extraction mode")
    demo = demo if demo is not None else os.environ.get("DEMO_CLOCK", "true") == "true"
    verify = None
    if cloud:
        project = os.environ["FIREBASE_PROJECT_ID"]
        bucket = os.environ["IMAGE_BUCKET"]
        if not os.environ.get("FIREBASE_WEB_API_KEY") or not os.environ.get("GEMINI_API_KEY"):
            raise RuntimeError("Cloud identity and Gemini configuration are required.")
        if mode != "gemini":
            raise RuntimeError("Cloud submission requires real Gemini extraction.")
        from cloud_identity import verifier
        verify = verifier(project)
        store = CloudStore(project, bucket)
    else:
        store = LocalStore(data_dir or os.environ.get("LOCAL_DATA_DIR", "data"))
    subject = ContextVar("dose_timer_subject", default=None)
    local_owner = hashlib.sha256(token.encode()).hexdigest()
    model_lock = threading.Lock()
    security = HTTPBearer(auto_error=False)

    @contextmanager
    def db():
        owner = subject.get() if cloud else local_owner
        if not owner:
            raise HTTPException(401, "A verified identity is required.")
        with store.session(owner) as session:
            yield session

    def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
        if cloud:
            if not subject.get():
                raise HTTPException(401, "A verified identity is required.")
            return subject.get()
        if not credentials or not hmac.compare_digest(credentials.credentials.encode(), token.encode()):
            raise HTTPException(401, "Local access is required.")
        return local_owner

    def get(con, kind, id):
        value = con.get(kind, id)
        if value is None:
            raise HTTPException(404, "Record not found.")
        return value

    def all_records(con, kind):
        return con.all(kind)

    def put(con, kind, id, value):
        con.put(kind, id, value)

    def now(con):
        row = con.get("clock", "current")
        offset = row["offset"] if demo and row else 0
        return datetime.now(timezone.utc) + timedelta(seconds=offset)

    def occurrences(con):
        current = now(con)
        today = current.astimezone(SEOUL).date()
        taken = {v["id"] for v in all_records(con, "taken")}
        result = []
        for routine in all_records(con, "routine"):
            if not routine["active"] or not routine["start_date"] <= today.isoformat() <= routine["end_date"]:
                continue
            for time in routine["times"]:
                due = datetime.fromisoformat(f"{today}T{time}:00").replace(tzinfo=SEOUL)
                id = f'{routine["id"]}:{today}:{time}'
                result.append({"id": id, "routine_id": routine["id"], "name": routine["name"],
                    "kind": routine["kind"], "dose": routine["dose"], "time": time, "due": due.isoformat(),
                    "status": "taken" if id in taken else "due" if due <= current else "upcoming"})
        return sorted(result, key=lambda v: (v["time"], v["name"]))

    app = FastAPI(title="Dose Timer — synthetic prototype", docs_url=None, redoc_url=None)
    app.add_middleware(BodyLimit)

    @app.middleware("http")
    async def private_responses(request, call_next):
        context = None
        try:
            if request.url.path.startswith("/api/"):
                value = request.headers.get("authorization", "")
                if cloud:
                    try:
                        owner = await run_in_threadpool(verify, value)
                    except HTTPException as error:
                        return Response(status_code=error.status_code, headers={"Cache-Control": "no-store"})
                    context = subject.set(owner)
                elif not hmac.compare_digest(value.encode(), f"Bearer {token}".encode()):
                    return Response(status_code=401)
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            return response
        finally:
            if context is not None:
                subject.reset(context)

    @app.get("/config")
    def public_config():
        return {"cloud": cloud, "firebase_api_key": os.environ.get("FIREBASE_WEB_API_KEY", "") if cloud else ""}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/state", dependencies=[Depends(authenticate)])
    def state():
        with db() as con:
            return {"now": now(con).isoformat(), "real_now": datetime.now(timezone.utc).isoformat(),
                "timezone": "Asia/Seoul", "demo_enabled": demo, "mode": mode,
                "documents": all_records(con, "document"), "routines": all_records(con, "routine"),
                "occurrences": occurrences(con)}

    @app.post("/api/documents", dependencies=[Depends(authenticate)])
    async def upload(kind: Literal["medication", "supplement"], file: UploadFile = File(...)):
        image = await file.read(MAX_IMAGE + 1)
        await file.close()
        if not image or len(image) > MAX_IMAGE:
            raise HTTPException(413, "Choose a JPEG or PNG image up to 5 MiB.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(image)) as opened:
                    if opened.format not in {"JPEG", "PNG"} or opened.width * opened.height > 24000000:
                        raise ValueError()
                    mime = "image/jpeg" if opened.format == "JPEG" else "image/png"
                    opened.verify()
        except Exception:
            raise HTTPException(422, "Choose a valid JPEG or PNG, at most 24 megapixels.") from None
        id = uuid.uuid4().hex
        record = {"id": id, "kind": kind, "created_at": datetime.now(timezone.utc).isoformat()}
        with db() as con:
            if len(all_records(con, "document")) >= 40:
                raise HTTPException(409, "This local prototype supports up to 40 images.")
            store.reserve("uploads")
            con.image_put(id, mime, image)
            put(con, "document", id, record)
        return record

    @app.get("/api/documents/{id}/image", dependencies=[Depends(authenticate)])
    def original(id: str):
        with db() as con:
            row = con.image_get(id)
            if row is None:
                raise HTTPException(404, "Image not found.")
            return Response(content=row["body"], media_type=row["mime"])

    @app.post("/api/documents/{id}/extract", dependencies=[Depends(authenticate)])
    def reading(id: str):
        if not model_lock.acquire(blocking=False):
            raise HTTPException(429, "Another image is being read. Please wait.")
        attempt = None
        try:
            with db() as con:
                document = get(con, "document", id)
                row = con.image_get(id)
                if len(all_records(con, "attempt")) >= 20:
                    raise HTTPException(429, "Local session reading limit reached (20 attempts). Manual entry is available.")
                attempt = {"id": uuid.uuid4().hex, "document_id": id, "source": mode,
                    "status": "pending", "created_at": datetime.now(timezone.utc).isoformat()}
                put(con, "attempt", attempt["id"], attempt)
            try:
                store.reserve("gemini")
                payload = extract(row["body"], row["mime"], document["kind"], mode)
            except HTTPException:
                attempt.update(status="failed", error="Daily shared demo limit reached.")
                with db() as con:
                    put(con, "attempt", attempt["id"], attempt)
                raise
            except ValueError as error:
                attempt.update(status="failed", error=str(error))
                with db() as con:
                    put(con, "attempt", attempt["id"], attempt)
                raise HTTPException(503, str(error)) from None
            attempt.update(status="unverified", result=payload.model_dump())
            with db() as con:
                put(con, "attempt", attempt["id"], attempt)
            return attempt
        finally:
            model_lock.release()

    @app.get("/api/documents/{id}/attempts", dependencies=[Depends(authenticate)])
    def attempts(id: str):
        with db() as con:
            get(con, "document", id)
            return [a for a in all_records(con, "attempt") if a["document_id"] == id]

    @app.post("/api/routines", dependencies=[Depends(authenticate)])
    def confirm(body: Routine):
        with db() as con:
            payload = body.model_dump(mode="json")
            replay = con.get("confirmation", body.request_key)
            if replay:
                saved = replay
                if saved['payload'] != payload:
                    raise HTTPException(409, "This confirmation was already saved with different details.")
                return saved['result']
            document = get(con, "document", body.document_id)
            if document["kind"] != body.kind:
                raise HTTPException(409, "Source type does not match.")
            if body.attempt_id:
                attempt = get(con, "attempt", body.attempt_id)
                if attempt["document_id"] != body.document_id or attempt["status"] != "unverified":
                    raise HTTPException(409, "Choose a successful reading or use manual entry.")
            if len(all_records(con, "routine")) >= 100:
                raise HTTPException(409, "This prototype supports up to 100 saved routines.")
            record = body.model_dump(mode="json") | {"id": uuid.uuid4().hex, "active": True,
                "provenance": "reviewed_extraction" if body.attempt_id else "manual",
                "confirmed_at": datetime.now(timezone.utc).isoformat()}
            put(con, "routine", record["id"], record)
            put(con, "confirmation", body.request_key, {"payload": payload, "result": record})
            return record

    @app.post("/api/routines/{id}/stop", dependencies=[Depends(authenticate)])
    def stop(id: str):
        with db() as con:
            record = get(con, "routine", id)
            record["active"] = False
            put(con, "routine", id, record)
        return record

    @app.post("/api/occurrences/{id}/taken", dependencies=[Depends(authenticate)])
    def taken(id: str):
        with db() as con:
            existing = con.get("taken", id)
            if existing:
                return existing
            occurrence = next((v for v in occurrences(con) if v["id"] == id), None)
            if occurrence is None:
                raise HTTPException(404, "Occurrence not found.")
            if occurrence["status"] != "due":
                raise HTTPException(409, "Only a currently due occurrence can be reported.")
            record = {"id": id, "reported_at": datetime.now(timezone.utc).isoformat(), "demo_at": now(con).isoformat(), "status": "taken"}
            put(con, "taken", id, record)
            return record

    @app.put("/api/demo/clock", dependencies=[Depends(authenticate)])
    def set_clock(body: Clock):
        if not demo:
            raise HTTPException(404)
        if body.at.tzinfo is None:
            raise HTTPException(422, "Provide an explicit timezone offset.")
        with db() as con:
            if body.at < now(con) - timedelta(seconds=2):
                raise HTTPException(409, "Demo time only moves forward. Use real time to end the demonstration.")
            put(con, "clock", "current", {"offset": (body.at - datetime.now(timezone.utc)).total_seconds()})
        return {"ok": True}

    @app.delete("/api/demo/clock", dependencies=[Depends(authenticate)])
    def real_clock():
        if not demo:
            raise HTTPException(404)
        with db() as con:
            con.delete("clock", "current")
        return {"ok": True}

    web = Path(os.environ.get("WEB_DIST", str(Path(__file__).parents[1] / "frontend" / "dist")))
    if cloud:
        if not (web / "index.html").is_file():
            raise RuntimeError("Build the frontend before cloud startup.")
        app.mount("/assets", StaticFiles(directory=web / "assets"), name="assets")
        app.mount("/samples", StaticFiles(directory=web / "samples"), name="samples")

        @app.get("/")
        def index():
            return FileResponse(web / "index.html")

    return app
