"""
MarketMind — Speech-to-Text (STT)
voice/stt.py

Uses faster-whisper (large-v3-turbo, INT8 quantized) for local,
offline transcription. Handles audio from the mobile app (/voice endpoint).

Supports: English, Nigerian Pidgin (transcribed as English),
          Yoruba, Hausa, Igbo (Whisper's multilingual model).

Performance on 10th gen i5 (CPU-only):
  - 5-second audio clip: ~2–5 seconds transcription time
  - INT8 quantization cuts memory and compute vs FP16
  - beam_size=1 for maximum speed
  - VAD filter skips silence
"""

import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

WHISPER_MODEL   = os.getenv("WHISPER_MODEL", "base") # Changed to 'base' (approx 140MB) to save download time.
COMPUTE_TYPE    = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
DEVICE          = "cpu"  # CPU-only machine

# Lazy-load the model so it's only initialised when voice/ is used
_model = None


def _get_model():
    """Initialise faster-whisper model once, reuse across requests."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        print(f"[STT] Loading faster-whisper ({WHISPER_MODEL}, {COMPUTE_TYPE})...")
        # Use the existing models directory as the download root
        download_root = os.path.join(os.getcwd(), "models")
        
        _model = WhisperModel(
            WHISPER_MODEL,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
            cpu_threads=6,          # Match Modelfile num_thread setting
            num_workers=1,          # Single worker on CPU
            download_root=download_root,
        )
        print("[STT] Model loaded.")
    return _model


def transcribe(audio_bytes: bytes, language_hint: str | None = None) -> dict:
    """
    Transcribe raw audio bytes to text.

    Args:
        audio_bytes:   Raw audio data (WAV, WebM, MP4, OGG, etc.)
        language_hint: Optional ISO 639-1 code ("yo", "ha", "ig", "en")
                       Whisper auto-detects if None.

    Returns:
        {
          "text":     "transcribed text",
          "language": "detected language code",
          "duration": float seconds
        }
    """
    model = _get_model()

    # Write to a temp file (faster-whisper needs a file path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments, info = model.transcribe(
            tmp_path,
            language=language_hint,     # None = auto-detect
            beam_size=1,                # Fastest on CPU
            vad_filter=True,            # Skip silence (saves CPU)
            vad_parameters={
                "min_silence_duration_ms": 300,  # Trim trailing silence
            },
            condition_on_previous_text=False,    # Each utterance is independent
        )

        text = " ".join(seg.text.strip() for seg in segments).strip()
        return {
            "text": text,
            "language": info.language,
            "duration": info.duration,
        }

    finally:
        # Always clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
