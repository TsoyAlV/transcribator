"""Local speech recognition; no audio is sent to an API."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

ALLOWED_EXTENSIONS = {".m4a", ".mp4", ".mp3"}
MAX_BYTES = 500 * 1024 * 1024


def validate_upload(name: str, size: int) -> str:
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Выберите файл M4A, MP4 или MP3.")
    if size <= 0:
        raise ValueError("Файл пустой.")
    if size > MAX_BYTES:
        raise ValueError("Файл больше 500 МБ. Разделите запись на части.")
    return suffix


def timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"


@dataclass(frozen=True)
class Transcript:
    text: str
    timed_text: str
    language: str
    duration: float


def collect_segments(
    segments: Iterable, info, progress: Callable[[float], None] | None = None
) -> Transcript:
    lines, timed = [], []
    duration = float(info.duration or 0)
    for segment in segments:
        text = segment.text.strip()
        if text:
            lines.append(text)
            timed.append(f"[{timestamp(segment.start)} — {timestamp(segment.end)}] {text}")
        if progress and duration > 0:
            progress(min(0.99, max(0.0, segment.end / duration)))
    if progress:
        progress(1.0)
    return Transcript("\n".join(lines), "\n".join(timed), info.language, duration)


def transcribe_file(model, path: Path, language: str | None, progress=None) -> Transcript:
    segments, info = model.transcribe(
        str(path), language=language, task="transcribe", beam_size=5,
        vad_filter=True, condition_on_previous_text=False,
    )
    # faster-whisper performs recognition lazily while segments are consumed.
    return collect_segments(segments, info, progress)
