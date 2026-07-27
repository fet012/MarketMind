import os
import google.generativeai as genai

def transcribe(audio_bytes: bytes) -> str:
    """Send audio bytes to Gemini for transcription."""
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel("gemini-3.1-flash-lite")# Fast, good for audio

    # Gemini accepts audio as a file-like object
    audio_file = {
        "mime_type": "audio/aac",  # your file is AAC
        "data": audio_bytes
    }

    prompt = "Transcribe the audio exactly as spoken."
    response = model.generate_content([prompt, audio_file])

    transcript = response.text.strip() or "[No speech detected]"
    print(f"[STT] Transcribed: {transcript}")
    return transcript