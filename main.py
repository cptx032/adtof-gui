"""FastAPI application for Onirógrafo audio-to-MIDI transcription."""

from __future__ import annotations

import os
import pathlib
import tempfile

import audio_formats
import fastapi
from fastapi import responses
from fastapi import staticfiles
from fastapi.middleware import trustedhost
import uvicorn

WEB_DIRECTORY: pathlib.Path = pathlib.Path(__file__).resolve().parent / "web"
MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024
UPLOAD_CHUNK_BYTES: int = 1024 * 1024
HOST: str = "127.0.0.1"
DEFAULT_PORT: int = 8888


def configured_port() -> int:
    """Return the HTTP listen port from PORT or the default."""
    raw: str = os.environ.get("PORT", str(DEFAULT_PORT))
    if not raw.isdigit():
        return DEFAULT_PORT
    value: int = int(raw)
    if value < 1 or value > 65535:
        return DEFAULT_PORT
    return value


PORT: int = configured_port()
ALLOWED_HOST: str = os.environ.get("ALLOWED_HOST", "").strip()
DEBUG: bool = os.environ.get("DEBUG", "").strip() == "1"


def allowed_hosts() -> list[str]:
    """Return Host headers the server accepts."""
    hosts: list[str] = []
    if ALLOWED_HOST:
        hosts.append(ALLOWED_HOST)
    if DEBUG:
        hosts.append("localhost")
        hosts.append("127.0.0.1")
    return hosts


app: fastapi.FastAPI = fastapi.FastAPI(title="Onirógrafo")
hosts: list[str] = allowed_hosts()
if hosts:
    app.add_middleware(
        trustedhost.TrustedHostMiddleware,
        allowed_hosts=hosts,
    )


def json_error(message: str, status_code: int) -> responses.JSONResponse:
    """Build a JSON error response."""
    return responses.JSONResponse(
        content={"ok": False, "message": message},
        status_code=status_code,
    )


def midi_download_name(upload: fastapi.UploadFile) -> str:
    """Return a safe MIDI filename derived from the upload."""
    raw_name: str = pathlib.Path(upload.filename or "drums.wav").name
    stem: str = pathlib.Path(raw_name).stem or "drums"
    return f"{stem}.mid"


def make_temp_path(prefix: str, suffix: str) -> pathlib.Path | None:
    """Create an empty temporary file path."""
    try:
        handle: int
        name: str
        handle, name = tempfile.mkstemp(prefix=prefix, suffix=suffix)
        os.close(handle)
        return pathlib.Path(name)
    except OSError:
        return None


def remove_path(path: pathlib.Path) -> bool:
    """Delete a file if it exists."""
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        return False
    return True


def write_upload_to_temp(
    upload: fastapi.UploadFile,
    extension: str,
) -> tuple[pathlib.Path | None, str]:
    """Save the uploaded file to a temporary audio path.

    Returns the path and an empty message when valid.
    """
    path: pathlib.Path | None = make_temp_path("adtof-upload-", f".{extension}")
    if path is None:
        return (None, "Não foi possível receber o arquivo.")
    total: int = 0
    too_large: bool = False
    try:
        with path.open("wb") as dest:
            while True:
                chunk: bytes = upload.file.read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    too_large = True
                    break
                dest.write(chunk)
    except OSError:
        remove_path(path)
        return (None, "Não foi possível receber o arquivo.")
    if too_large:
        remove_path(path)
        return (None, "O arquivo ultrapassa 50MB.")
    if total == 0:
        remove_path(path)
        return (None, "Envie um arquivo de áudio.")
    return (path, "")


def transcribe_audio_to_midi(audio_path: pathlib.Path, midi_path: pathlib.Path) -> bool:
    """Transcribe an audio file to a MIDI file with ADTOF-pytorch."""
    try:
        import adtof_pytorch
    except Exception:
        return False
    try:
        written: pathlib.Path = adtof_pytorch.transcribe_to_midi(audio_path, midi_path)
    except Exception:
        return False
    try:
        return written.is_file() and written.stat().st_size > 0
    except OSError:
        return False


@app.post("/api/convert")
def convert_audio(
    file: fastapi.UploadFile,
    tasks: fastapi.BackgroundTasks,
) -> responses.Response:
    """Transcribe an uploaded audio file and return a MIDI download."""
    extension: str = audio_formats.extension_for_upload(
        file.filename or "",
        file.content_type or "",
    )
    if not extension:
        return json_error("Envie um arquivo de áudio suportado.", 400)

    audio_path: pathlib.Path | None
    message: str
    audio_path, message = write_upload_to_temp(file, extension)
    if audio_path is None:
        return json_error(message, 400)

    midi_path: pathlib.Path | None = make_temp_path("adtof-", ".mid")
    if midi_path is None:
        remove_path(audio_path)
        return json_error("Não foi possível criar o arquivo MIDI.", 500)

    if not transcribe_audio_to_midi(audio_path, midi_path):
        remove_path(audio_path)
        remove_path(midi_path)
        return json_error("Não foi possível transcrever o áudio.", 500)

    tasks.add_task(remove_path, audio_path)
    tasks.add_task(remove_path, midi_path)
    return responses.FileResponse(
        path=str(midi_path),
        filename=midi_download_name(file),
        media_type="audio/midi",
    )


app.mount(
    "/",
    staticfiles.StaticFiles(directory=str(WEB_DIRECTORY), html=True),
    name="web",
)


def main() -> bool:
    """Start the FastAPI server."""
    try:
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    except KeyboardInterrupt:
        return True
    except Exception:
        return False
    return True


if __name__ == "__main__":
    main()
