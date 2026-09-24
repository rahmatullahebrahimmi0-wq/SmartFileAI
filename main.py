import asyncio
import base64
import json
import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from starlette.requests import Request

try:
    from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
    from aiortc.sdp import candidate_from_sdp
except Exception:  # pragma: no cover
    RTCIceCandidate = None
    RTCPeerConnection = None
    RTCSessionDescription = None
    candidate_from_sdp = None

try:
    from google import genai
    from google.genai import types as genai_types
except Exception:  # pragma: no cover
    genai = None
    genai_types = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


APP_ENV = os.getenv("APP_ENV", "local")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
GEMINI_LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-2.0-flash-exp")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "")
REPLICATE_VERSION = os.getenv("REPLICATE_VERSION", "")
REPLICATE_API_BASE = "https://api.replicate.com/v1"

FFMPEG_PATH = os.getenv("FFMPEG_PATH", "/usr/bin/ffmpeg")

CORS_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "*",
]


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========================
# Data models
# =========================

class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class CompileRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=20000)
    engine: str = Field(default="gemini")


class VideoRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=20000)
    duration: int = Field(default=5, ge=1, le=60)
    title: Optional[str] = None
    voice: str = "fa-IR-Standard-A"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_EXPIRE_MINUTES * 60


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    output_url: Optional[str] = None
    error: Optional[str] = None
    created_at: str


class GenericResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# =========================
# In-memory store
# =========================

users_db: Dict[str, Dict[str, Any]] = {}
compile_jobs: Dict[str, Dict[str, Any]] = {}
video_jobs: Dict[str, Dict[str, Any]] = {}
peer_connections: Dict[str, Any] = {}
live_sessions: Dict[str, Any] = {}


# =========================
# Auth helpers
# =========================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_token(user_id: str, email: str, full_name: str, tenant_id: str = "local-tenant") -> str:
    expires_at = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": email,
        "user_id": user_id,
        "full_name": full_name,
        "tenant_id": tenant_id,
        "exp": expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


async def get_current_user_from_token(authorization: Optional[str]) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empty token")

    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = payload.get("user_id")
    email = payload.get("sub")

    if not user_id or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incomplete token payload")

    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return {
        "user_id": user_id,
        "email": email,
        "full_name": user["full_name"],
        "tenant_id": user["tenant_id"],
    }


async def get_current_user_from_websocket(websocket: WebSocket) -> Dict[str, Any]:
    token = websocket.query_params.get("token") or websocket.headers.get("authorization")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = token.replace("Bearer ", "").strip()

    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = payload.get("user_id")
    email = payload.get("sub")
    if not user_id or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return {
        "user_id": user_id,
        "email": email,
        "full_name": user["full_name"],
        "tenant_id": user["tenant_id"],
    }


# =========================
# Gemini Live client
# =========================

class GeminiLiveClient:
    def __init__(self):
        if genai is None:
            raise RuntimeError("google-genai is not installed")
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    async def open_live_session(self):
        if genai_types is None:
            raise RuntimeError("google.genai.types is not available")

        live_config = genai_types.LiveConnectConfig(
            response_modalities=["AUDIO", "TEXT"],
            system_instruction=genai_types.Content(
                parts=[
                    genai_types.Part.from_text(
                        text=(
                            "You are a senior enterprise AI assistant. "
                            "Reply clearly and briefly. "
                            "Use Persian when appropriate. "
                            "Keep answers concise and technically precise."
                        )
                    )
                ]
            ),
        )

        return await self.client.aio.live.connect(
            model=GEMINI_LIVE_MODEL,
            config=live_config,
        )

    async def send_text(self, session: Any, text: str) -> None:
        if not text:
            return
        await session.send_realtime_input(text=text)

    async def send_pcm(self, session: Any, pcm_bytes: bytes, sample_rate: int = 16000) -> None:
        try:
            await session.send_realtime_input(
                audio=genai_types.Blob(
                    data=pcm_bytes,
                    mime_type=f"audio/pcm;rate={sample_rate}",
                )
            )
        except Exception:
            # Some SDK versions use a different shape; keep fallback path in a strict way.
            await session.send_realtime_input(
                audio={"data": pcm_bytes, "mime_type": f"audio/pcm;rate={sample_rate}"}
            )

    async def receive_stream(self, session: Any):
        async for event in session.receive():
            if hasattr(event, "text") and event.text:
                yield {"type": "text", "text": event.text}
            elif hasattr(event, "audio") and event.audio:
                audio_payload = event.audio
                audio_data = getattr(audio_payload, "data", None)
                mime_type = getattr(audio_payload, "mime_type", "audio/pcm;rate=24000")
                sample_rate = getattr(audio_payload, "sample_rate", 24000)

                if isinstance(audio_data, (bytes, bytearray)):
                    yield {"type": "audio", "data": base64.b64encode(bytes(audio_data)).decode("ascii"), "mime_type": mime_type, "sample_rate": sample_rate}
                elif audio_data is not None:
                    yield {"type": "audio", "data": base64.b64encode(bytes(audio_data)).decode("ascii"), "mime_type": mime_type, "sample_rate": sample_rate}
            else:
                yield {"type": "event", "raw": str(event)}


# =========================
# Replicate orchestrator
# =========================

class ReplicateError(RuntimeError):
    pass


class ReplicateOrchestrator:
    def __init__(self, token: Optional[str] = None, model: Optional[str] = None, version: Optional[str] = None):
        self.token = token or REPLICATE_API_TOKEN
        self.model = model or REPLICATE_MODEL
        self.version = version or REPLICATE_VERSION
        self.base_url = REPLICATE_API_BASE.rstrip("/")

        if not self.token:
            raise ReplicateError("REPLICATE_API_TOKEN is required")
        if not self.model:
            raise ReplicateError("REPLICATE_MODEL is required")
        if not self.version:
            raise ReplicateError("REPLICATE_VERSION is required")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

    def create_prediction(self, prompt: str, duration: int = 300, aspect_ratio: str = "16:9", frames_per_second: int = 24, extra_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "input": {
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "frames_per_second": frames_per_second,
            }
        }
        if extra_input:
            payload["input"].update(extra_input)

        url = f"{self.base_url}/models/{self.model}/versions/{self.version}/predictions"
        resp = httpx.post(url, headers=self._headers(), json=payload, timeout=90.0)
        if resp.status_code >= 300:
            raise ReplicateError(f"Replicate create failed: {resp.status_code} {resp.text[:2000]}")
        data = resp.json()
        return data

    def poll_prediction(self, prediction_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            resp = httpx.get(f"{self.base_url}/predictions/{prediction_id}", headers=self._headers(), timeout=90.0)
            if resp.status_code >= 300:
                raise ReplicateError(f"Replicate poll failed: {resp.status_code} {resp.text[:2000]}")
            data = resp.json()
            status = str(data.get("status", "")).lower()

            if status in {"succeeded", "completed"}:
                return data
            if status in {"failed", "canceled", "cancelled", "error"}:
                raise ReplicateError(f"Replicate prediction failed: {data}")
            time.sleep(5)

        raise ReplicateError(f"Replicate prediction timed out: {prediction_id}")

    def extract_output_url(self, output: Any) -> str:
        if isinstance(output, str):
            return output
        if isinstance(output, list):
            for item in output:
                if isinstance(item, str):
                    return item
                if isinstance(item, dict):
                    for key in ("url", "video_url", "mp4_url", "output_url", "download_url"):
                        if key in item and isinstance(item[key], str):
                            return item[key]
            raise ReplicateError(f"Unable to extract output URL from list output: {output}")
        if isinstance(output, dict):
            for key in ("url", "video_url", "mp4_url", "output_url", "download_url"):
                if key in output and isinstance(output[key], str):
                    return output[key]
            if "data" in output and isinstance(output["data"], list):
                for item in output["data"]:
                    if isinstance(item, str):
                        return item
                    if isinstance(item, dict):
                        for key in ("url", "video_url", "mp4_url", "output_url", "download_url"):
                            if key in item and isinstance(item[key], str):
                                return item[key]
        raise ReplicateError(f"Unable to extract output URL from Replicate response: {output}")


# =========================
# FFmpeg pipeline
# =========================

class FFmpegPipeline:
    def __init__(self, ffmpeg_path: str = FFMPEG_PATH):
        self.ffmpeg_path = ffmpeg_path

    def _download_file(self, url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", url, follow_redirects=True, timeout=240.0) as resp:
            resp.raise_for_status()
            with open(destination, "wb") as fh:
                for chunk in resp.iter_bytes():
                    fh.write(chunk)

    def _format_srt_time(self, seconds: int) -> str:
        total_ms = seconds * 1000
        hours = total_ms // 3600000
        minutes = (total_ms % 3600000) // 60000
        secs = (total_ms % 60000) // 1000
        ms = total_ms % 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

    def _wrap_prompt_for_subtitles(self, prompt: str, max_chars: int = 38) -> List[str]:
        words = prompt.split()
        lines: List[str] = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines[:10]

    def _generate_persian_srt(self, prompt: str, output_path: Path) -> None:
        lines = self._wrap_prompt_for_subtitles(prompt)
        blocks: List[str] = []

        for idx, line in enumerate(lines, start=1):
            start = self._format_srt_time((idx - 1) * 2)
            end = self._format_srt_time(idx * 2)
            blocks.append(str(idx))
            blocks.append(f"{start} --> {end}")
            blocks.append(line)
            blocks.append("")

        output_path.write_text("\n".join(blocks), encoding="utf-8")

    def _build_silent_audio(self, duration_seconds: int, output_path: Path) -> None:
        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(duration_seconds),
                "-q:a", "9",
                "-acodec", "pcm_s16le",
                str(output_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def _build_tts_or_silence(self, prompt: str, output_path: Path, duration_seconds: int) -> None:
        if OPENAI_API_KEY and OpenAI is not None:
            try:
                client = OpenAI(api_key=OPENAI_API_KEY)
                response = client.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice="alloy",
                    input=prompt,
                )
                response.stream_to_file(str(output_path))
                return
            except Exception:
                pass

        self._build_silent_audio(duration_seconds, output_path)

    def render_final_video(self, source_video_url: str, prompt: str, output_dir: Optional[str] = None) -> str:
        temp_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="lumina_ffmpeg_"))
        temp_dir.mkdir(parents=True, exist_ok=True)

        source_path = temp_dir / "source.mp4"
        audio_path = temp_dir / "voiceover.wav"
        srt_path = temp_dir / "captions.srt"
        normalized_path = temp_dir / "normalized.mp4"
        final_path = temp_dir / "final_output.mp4"

        self._download_file(source_video_url, source_path)
        self._generate_persian_srt(prompt, srt_path)

        duration_seconds = max(3, int(5 * 60))  # default fallback duration
        self._build_tts_or_silence(prompt, audio_path, duration_seconds)

        command = [
            self.ffmpeg_path,
            "-y",
            "-i", str(source_path),
            "-i", str(audio_path),
            "-vf",
            (
                "scale=1920:1080:force_original_aspect_ratio=decrease,"
                "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
                f"subtitles={str(srt_path)}:force_style='Fontname=Tahoma,Fontsize=26,"
                "PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=3,"
                "Outline=2,Shadow=0,Alignment=2'"
            ),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-movflags", "+faststart",
            "-shortest",
            str(normalized_path),
        ]

        proc = subprocess.run(command, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg render failed: {proc.stderr[:3000]}")

        final_path.write_bytes(normalized_path.read_bytes())
        return str(final_path)


# =========================
# Background video task
# =========================

async def process_video_job(job_id: str) -> None:
    job = video_jobs.get(job_id)
    if not job:
        return

    try:
        job["status"] = "processing"
        job["progress"] = 10
        orchestration = ReplicateOrchestrator()
        result = orchestration.create_prediction(
            prompt=job["prompt"],
            duration=job["duration"] * 60,
            aspect_ratio="16:9",
            frames_per_second=24,
        )
        prediction_id = result.get("id")
        if not prediction_id:
            raise ReplicateError(f"Replicate did not return a prediction id: {result}")
        job["prediction_id"] = prediction_id
        job["progress"] = 25

        final = orchestration.poll_prediction(prediction_id, timeout_seconds=1800)
        output_url = orchestration.extract_output_url(final.get("output"))
        job["progress"] = 75

        ffmpeg = FFmpegPipeline()
        local_path = ffmpeg.render_final_video(output_url, job["prompt"], str(Path(tempfile.mkdtemp(prefix="lumina_video_"))))
        job["output_url"] = local_path
        job["status"] = "completed"
        job["progress"] = 100
        job["error"] = None
    except Exception as exc:
        job["status"] = "failed"
        job["progress"] = 0
        job["error"] = str(exc)


# =========================
# FastAPI app
# =========================

app = FastAPI(title="SmartFile AI Elite", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# seed demo user
# -------------------------

def ensure_demo_user() -> None:
    email = "admin@lumina.local"
    if email not in users_db:
        users_db[email] = {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "full_name": "Admin User",
            "tenant_id": "local-tenant",
            "password_hash": hash_password("StrongPassword123!"),
        }


ensure_demo_user()


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "env": APP_ENV}


# =========================
# Auth routes
# =========================

@app.post("/api/auth/register", response_model=TokenResponse)
async def register_user(payload: UserRegisterRequest):
    if payload.email.lower() in {u["email"].lower() for u in users_db.values()}:
        raise HTTPException(status_code=409, detail="User already exists")

    user_id = str(uuid.uuid4())
    users_db[user_id] = {
        "user_id": user_id,
        "email": payload.email.lower(),
        "full_name": payload.full_name.strip(),
        "tenant_id": "local-tenant",
        "password_hash": hash_password(payload.password),
    }

    token = create_token(user_id, payload.email.lower(), payload.full_name.strip(), "local-tenant")
    return TokenResponse(access_token=token, token_type="bearer", expires_in=JWT_EXPIRE_MINUTES * 60)


@app.post("/api/auth/login", response_model=TokenResponse)
async def login_user(payload: UserLoginRequest):
    matched = None
    for user in users_db.values():
        if user["email"].lower() == payload.email.lower():
            matched = user
            break

    if not matched:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, matched["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(matched["user_id"], matched["email"], matched["full_name"], matched["tenant_id"])
    return TokenResponse(access_token=token, token_type="bearer", expires_in=JWT_EXPIRE_MINUTES * 60)


@app.get("/api/auth/me")
async def me(current_user: Dict[str, Any] = Depends(lambda: None)):
    # This endpoint is intentionally simple; use Authorization header in real deployment.
    raise HTTPException(status_code=501, detail="me endpoint not enabled in local mode")


# =========================
# Compile routes
# =========================

@app.post("/api/compile")
async def compile_code(payload: CompileRequest, authorization: Optional[str] = None):
    try:
        user = await get_current_user_from_token(authorization)
    except HTTPException:
        # local mode allows demo auth for convenience
        user = {
            "user_id": next(iter(users_db.keys())),
            "email": "admin@lumina.local",
            "full_name": "Admin User",
            "tenant_id": "local-tenant",
        }

    job_id = str(uuid.uuid4())
    compile_jobs[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "provider": payload.engine,
        "prompt": payload.prompt,
        "created_at": datetime.utcnow().isoformat(),
        "code": "",
        "error": None,
    }

    try:
        if payload.engine == "gemini":
            if not GEMINI_API_KEY:
                raise RuntimeError("GEMINI_API_KEY is required")
            if genai is None:
                raise RuntimeError("google-genai package not installed")

            client = genai.Client(api_key=GEMINI_API_KEY)
            result = client.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=payload.prompt,
            )
            response_text = getattr(result, "text", None) or str(result)
            compile_jobs[job_id]["status"] = "completed"
            compile_jobs[job_id]["code"] = response_text
            compile_jobs[job_id]["provider"] = "gemini"

        elif payload.engine == "gpt":
            if not OPENAI_API_KEY or OpenAI is None:
                raise RuntimeError("OPENAI_API_KEY is required")
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.responses.create(
                model="gpt-4o-mini",
                input=payload.prompt,
            )
            response_text = resp.output_text if hasattr(resp, "output_text") else str(resp)
            compile_jobs[job_id]["status"] = "completed"
            compile_jobs[job_id]["code"] = response_text
            compile_jobs[job_id]["provider"] = "gpt"
        else:
            raise ValueError(f"Unsupported engine: {payload.engine}")

    except Exception as exc:
        compile_jobs[job_id]["status"] = "failed"
        compile_jobs[job_id]["error"] = str(exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "job_id": job_id,
        "status": compile_jobs[job_id]["status"],
        "provider": compile_jobs[job_id]["provider"],
        "code": compile_jobs[job_id]["code"],
        "created_at": compile_jobs[job_id]["created_at"],
    }


@app.get("/api/compile/{job_id}")
async def get_compile_job(job_id: str):
    job = compile_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Compile job not found")

    return {
        "job_id": job_id,
        "status": job["status"],
        "provider": job["provider"],
        "code": job.get("code"),
        "error": job.get("error"),
        "created_at": job["created_at"],
    }


# =========================
# Video routes
# =========================

@app.post("/api/video/jobs")
async def create_video_job(payload: VideoRequest, authorization: Optional[str] = None):
    try:
        user = await get_current_user_from_token(authorization)
    except HTTPException:
        user = {
            "user_id": next(iter(users_db.keys())),
            "email": "admin@lumina.local",
            "full_name": "Admin User",
            "tenant_id": "local-tenant",
        }

    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    video_jobs[job_id] = {
        "job_id": job_id,
        "user_id": user["user_id"],
        "tenant_id": user["tenant_id"],
        "prompt": payload.prompt,
        "duration": payload.duration,
        "title": payload.title or "SmartFile AI Render",
        "voice": payload.voice,
        "status": "queued",
        "progress": 0,
        "output_url": None,
        "error": None,
        "created_at": now,
    }

    asyncio.create_task(process_video_job(job_id))

    return {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "output_url": None,
        "error": None,
        "created_at": now,
    }


@app.get("/api/video/jobs/{job_id}")
async def get_video_job(job_id: str):
    job = video_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "output_url": job.get("output_url"),
        "error": job.get("error"),
        "created_at": job["created_at"],
    }


@app.get("/api/video/jobs/{job_id}/download")
async def download_video(job_id: str):
    job = video_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")

    if not job.get("output_url"):
        raise HTTPException(status_code=400, detail="Video not ready yet")

    file_path = Path(str(job["output_url"]))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Output file does not exist")

    return FileResponse(file_path, media_type="video/mp4", filename=file_path.name)


# =========================
# WebRTC routes
# =========================

@app.post("/api/live/webrtc/offer")
async def webrtc_offer(payload: Dict[str, Any], authorization: Optional[str] = None):
    if RTCPeerConnection is None:
        raise HTTPException(status_code=500, detail="aiortc is not installed")

    try:
        user = await get_current_user_from_token(authorization)
    except HTTPException:
        # local demo mode
        user = {
            "user_id": "demo-user",
            "tenant_id": "local-tenant",
            "email": "admin@lumina.local",
            "full_name": "Admin User",
        }

    sdp = payload.get("sdp")
    if not sdp:
        raise HTTPException(status_code=400, detail="sdp is required")

    pc = RTCPeerConnection()

    @pc.on("connectionstatechange")
    async def _on_state_change():
        if pc.connectionState in {"failed", "closed", "disconnected"}:
            peer_connections.pop(user["user_id"], None)

    @pc.on("track")
    def _on_track(track):
        pass

    await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="offer"))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    peer_connections[user["user_id"]] = pc

    return {
        "type": pc.localDescription.type,
        "sdp": pc.localDescription.sdp,
    }


@app.post("/api/live/webrtc/ice")
async def webrtc_ice(payload: Dict[str, Any], authorization: Optional[str] = None):
    if RTCPeerConnection is None:
        raise HTTPException(status_code=500, detail="aiortc is not installed")

    try:
        user = await get_current_user_from_token(authorization)
    except HTTPException:
        user = {
            "user_id": "demo-user",
            "tenant_id": "local-tenant",
            "email": "admin@lumina.local",
            "full_name": "Admin User",
        }

    candidate_data = payload.get("candidate")
    if not candidate_data:
        raise HTTPException(status_code=400, detail="candidate is required")

    pc = peer_connections.get(user["user_id"])
    if not pc:
        raise HTTPException(status_code=404, detail="No active peer connection")

    candidate = candidate_data.get("candidate")
    if not candidate:
        raise HTTPException(status_code=400, detail="candidate.candidate is required")

    if candidate_from_sdp is None:
        raise HTTPException(status_code=500, detail="aiortc candidate parser is unavailable")

    try:
        parsed = candidate_from_sdp(candidate)
        ice_candidate = RTCIceCandidate(
            foundation=parsed.foundation,
            component=parsed.component,
            protocol=parsed.protocol,
            priority=parsed.priority,
            ip=parsed.ip,
            port=parsed.port,
            type=parsed.type,
            relatedAddress=parsed.relatedAddress,
            relatedPort=parsed.relatedPort,
            sdpMid=candidate_data.get("sdpMid"),
            sdpMLineIndex=candidate_data.get("sdpMLineIndex"),
            tcpType=getattr(parsed, "tcpType", None),
        )
        await pc.addIceCandidate(ice_candidate)
        return {"success": True, "status": "accepted"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to add ICE candidate: {exc}") from exc


# =========================
# Gemini live WebSocket
# =========================

@app.websocket("/api/live/gemini")
async def gemini_live_ws(websocket: WebSocket):
    await websocket.accept()

    token = websocket.query_params.get("token") or websocket.headers.get("authorization")
    if token:
        token = token.replace("Bearer ", "").strip()

    if not token:
        await websocket.close(code=4401, reason="Missing token")
        return

    try:
        claims = decode_token(token)
    except ValueError:
        await websocket.close(code=4401, reason="Invalid token")
        return

    user_id = claims.get("user_id")
    if not user_id:
        await websocket.close(code=4401, reason="Invalid token payload")
        return

    if genai is None:
        await websocket.send_text(json.dumps({"type": "error", "message": "google-genai is not installed"}, ensure_ascii=False))
        await websocket.close()
        return

    if not GEMINI_API_KEY:
        await websocket.send_text(json.dumps({"type": "error", "message": "GEMINI_API_KEY is not configured"}, ensure_ascii=False))
        await websocket.close()
        return

    try:
        client = GeminiLiveClient()
        session = await client.open_live_session()

        async def forward_events():
            async for event in client.receive_stream(session):
                try:
                    await websocket.send_text(json.dumps(event, ensure_ascii=False, default=str))
                except Exception:
                    pass

        receiver_task = asyncio.create_task(forward_events())

        await websocket.send_text(json.dumps({"type": "system", "text": "Gemini Live session connected."}, ensure_ascii=False))

        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON."}, ensure_ascii=False))
                continue

            kind = payload.get("type")
            if kind == "text":
                text = str(payload.get("text", "")).strip()
                if text:
                    await client.send_text(session, text)
            elif kind == "audio":
                encoded = payload.get("data")
                if not isinstance(encoded, str):
                    await websocket.send_text(json.dumps({"type": "error", "message": "Audio data must be base64 string."}, ensure_ascii=False))
                    continue
                sample_rate = int(payload.get("sample_rate", 16000))
                try:
                    pcm = base64.b64decode(encoded, validate=True)
                except Exception:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Invalid base64 audio."}, ensure_ascii=False))
                    continue
                await client.send_pcm(session, pcm, sample_rate=sample_rate)
            elif kind == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            else:
                await websocket.send_text(json.dumps({"type": "error", "message": f"Unsupported message type: {kind}"}, ensure_ascii=False))

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False))
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# =========================
# Local host bootstrap
# =========================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=APP_ENV == "local",
    )