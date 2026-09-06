"""Supported audio formats for ADTOF transcription."""

from __future__ import annotations

import pathlib

AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {
        "aac",
        "aif",
        "aiff",
        "flac",
        "m4a",
        "mp3",
        "mpga",
        "oga",
        "ogg",
        "opus",
        "wav",
        "wma",
    }
)
AUDIO_FILETYPES: list[tuple[str, str]] = [
    (
        "Audio files",
        " ".join(f"*.{extension}" for extension in sorted(AUDIO_EXTENSIONS)),
    )
]
AUDIO_MIME_TO_EXTENSION: dict[str, str] = {
    "audio/aac": "aac",
    "audio/aiff": "aiff",
    "audio/flac": "flac",
    "audio/m4a": "m4a",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/mpeg": "mp3",
    "audio/ogg": "ogg",
    "audio/opus": "opus",
    "audio/wav": "wav",
    "audio/wave": "wav",
    "audio/x-aiff": "aiff",
    "audio/x-flac": "flac",
    "audio/x-m4a": "m4a",
    "audio/x-ms-wma": "wma",
    "audio/x-wav": "wav",
    "audio/wma": "wma",
}


def is_supported_audio_path(path: pathlib.Path) -> bool:
    """Return whether the path uses a supported audio extension."""
    suffix: str = path.suffix.lower().lstrip(".")
    return suffix in AUDIO_EXTENSIONS


def extension_for_upload(filename: str, content_type: str) -> str:
    """Return a supported audio extension from a filename or MIME type."""
    name: str = pathlib.Path(filename).name
    suffix: str = pathlib.Path(name).suffix.lower().lstrip(".")
    if suffix in AUDIO_EXTENSIONS:
        return suffix
    mapped: str = AUDIO_MIME_TO_EXTENSION.get(content_type, "")
    if mapped in AUDIO_EXTENSIONS:
        return mapped
    return ""
