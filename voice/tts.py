"""
MarketMind — Text-to-Speech (TTS)
voice/tts.py

Dual-engine TTS strategy:
  - YarnGPT-local  → Yoruba, Igbo, Nigerian Pidgin, English
                     (authentic Nigerian accents, runs offline via PyTorch)
  - Piper TTS      → Hausa
                     (ONNX model, ~<1s on CPU, adab-tech/murya-piper-hausa)

Both engines are loaded lazily on first use and cached for the session.

Model download (one-time, run scripts/download_models.bat):
  huggingface-cli download saheedniyi/YarnGPT2 --local-dir ./voice/models/yarngpt
  huggingface-cli download novateur/WavTokenizer-medium-speech-75token --local-dir ./voice/models/wavtokenizer
"""

import io
import os
import sys
import wave
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

YARNGPT_MODEL_DIR   = os.getenv("YARNGPT_MODEL_DIR",   "./voice/models/yarngpt")
WAVTOKENIZER_DIR    = os.getenv("WAVTOKENIZER_DIR",     "./voice/models/wavtokenizer")
PIPER_HAUSA_MODEL   = os.getenv("PIPER_HAUSA_MODEL",   "./voice/models/piper_hausa/ha_NE-rmtts-medium.onnx")
PIPER_HAUSA_CONFIG  = os.getenv("PIPER_HAUSA_CONFIG",  "./voice/models/piper_hausa/ha_NE-rmtts-medium.onnx.json")

# YarnGPT speaker names (choose the clearest voice per language)
YARNGPT_SPEAKERS = {
    "yoruba":  "idera",    # Clear Yoruba female voice
    "igbo":    "tunde",    # Igbo-accented speaker
    "pidgin":  "idera",    # Pidgin works well with Nigerian English voices
    "english": "idera",    # Nigerian-accented English
}

# Lazy-loaded engine handles
_yarngpt_model     = None
_yarngpt_tokenizer = None
_piper_voice       = None


# ── YarnGPT ───────────────────────────────────────────────────

def _load_yarngpt():
    """Initialise YarnGPT model + WavTokenizer once."""
    global _yarngpt_model, _yarngpt_tokenizer
    if _yarngpt_model is None:
        # Force offline mode — we downloaded the models already
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

        # YarnGPT repo must be on path for AudioTokenizerV2
        yarngpt_src = Path(YARNGPT_MODEL_DIR)
        if str(yarngpt_src) not in sys.path:
            sys.path.insert(0, str(yarngpt_src))

        try:
            import torch
            from transformers import AutoModelForCausalLM
            from yarngpt.audiotokenizer import AudioTokenizerV2
        except ImportError as e:
            raise RuntimeError(
                f"YarnGPT dependencies missing: {e}. "
                "Run: pip install torch torchaudio transformers uroman"
            )

        wav_config = str(
            Path(WAVTOKENIZER_DIR)
            / "wavtokenizer_mediumdata_frame75_3s_nq1_code4096_dim512_kmeans200_attn.yaml"
        )
        wav_ckpt = str(
            Path(WAVTOKENIZER_DIR)
            / "wavtokenizer_large_speech_320_24k.ckpt"
        )

        print("[TTS] Loading YarnGPT (this takes ~15s first time)...")
        _yarngpt_tokenizer = AudioTokenizerV2(
            tokenizer_path=YARNGPT_MODEL_DIR,
            wav_tokenizer_model_path=wav_ckpt,
            wav_tokenizer_config_path=wav_config,
        )
        _yarngpt_model = AutoModelForCausalLM.from_pretrained(
            YARNGPT_MODEL_DIR,
            torch_dtype="auto",
        ).to(_yarngpt_tokenizer.device)
        print("[TTS] YarnGPT loaded.")


def _synthesize_yarngpt(text: str, language: str) -> bytes:
    """Synthesize speech using YarnGPT. Returns WAV bytes."""
    _load_yarngpt()
    import torchaudio

    speaker = YARNGPT_SPEAKERS.get(language, "idera")
    prompt = _yarngpt_tokenizer.create_prompt(text, lang=language, speaker_name=speaker)
    input_ids = _yarngpt_tokenizer.tokenize_prompt(prompt)

    output = _yarngpt_model.generate(
        input_ids=input_ids,
        temperature=0.1,
        repetition_penalty=1.1,
        max_length=4000,
    )
    codes = _yarngpt_tokenizer.get_codes(output)
    audio = _yarngpt_tokenizer.get_audio(codes)

    # Convert tensor to WAV bytes
    buf = io.BytesIO()
    torchaudio.save(buf, audio, sample_rate=24000, format="wav")
    buf.seek(0)
    return buf.read()


# ── Piper TTS (Hausa) ─────────────────────────────────────────

def _load_piper():
    """Initialise Piper voice once."""
    global _piper_voice
    if _piper_voice is None:
        try:
            from piper.voice import PiperVoice
        except ImportError:
            raise RuntimeError(
                "piper-tts not installed. Run: pip install piper-tts"
            )
        if not Path(PIPER_HAUSA_MODEL).exists():
            raise FileNotFoundError(
                f"Piper Hausa model not found at {PIPER_HAUSA_MODEL}. "
                "Download it from https://huggingface.co/adab-tech/murya-piper-hausa-tts"
            )
        print("[TTS] Loading Piper Hausa voice...")
        _piper_voice = PiperVoice.load(PIPER_HAUSA_MODEL, config_path=PIPER_HAUSA_CONFIG)
        print("[TTS] Piper loaded.")


def _synthesize_piper(text: str) -> bytes:
    """Synthesize Hausa speech using Piper. Returns WAV bytes."""
    _load_piper()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        _piper_voice.synthesize(text, wav_file)
    buf.seek(0)
    return buf.read()


# ── Public API ────────────────────────────────────────────────

def synthesize(text: str, language: str) -> bytes:
    """
    Synthesize speech for the given text and language.

    Args:
        text:     The text to speak (in the trader's language).
        language: One of: english | pidgin | yoruba | igbo | hausa

    Returns:
        WAV audio bytes ready to stream back to the mobile app.
    """
    if not text or not text.strip():
        return b""

    if language == "hausa":
        return _synthesize_piper(text)
    else:
        return _synthesize_yarngpt(text, language)
