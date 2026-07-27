import requests
import sys

# Check if audio file exists
audio_file = "test_audio.aac"
try:
    with open(audio_file, "rb") as f:
        files = {"audio": (audio_file, f, "audio/aac")}
        print(f"📤 Sending {audio_file} to /voice endpoint...")
        response = requests.post(
            "http://localhost:8000/voice?user_id=test2",
            files=files,
            timeout=60  # STT model loading might take a few seconds
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")
            print(f"📝 Transcription: {data.get('transcription', 'N/A')}")
            print(f"💬 AI Reply: {data.get('reply', 'N/A')}")
            print(f"🎯 Intent: {data.get('intent', 'N/A')}")
            if data.get('transaction'):
                print(f"📊 Logged: {data['transaction']}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
except FileNotFoundError:
    print(f"❌ Audio file '{audio_file}' not found in current directory")
    print("📌 Make sure test_audio.aac exists in the project root")
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to server at http://localhost:8000")
    print("📌 Is the server running? (python server.py)")
except Exception as e:
    print(f"❌ Unexpected error: {e}")