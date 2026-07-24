@echo off
set PYTHONIOENCODING=utf-8
chcp 65001 >nul
REM MarketMind - One-time model download script
REM Run this ONCE to download YarnGPT and Piper Hausa models.
REM Gemma is already downloaded in Ollama - skipped.
REM After this, everything runs 100% offline.

echo ================================================
echo  MarketMind Model Downloader
echo  (Gemma is already in Ollama - skipping)
echo ================================================
echo.

REM Create model directories
mkdir voice\models\yarngpt      2>nul
mkdir voice\models\wavtokenizer 2>nul
mkdir voice\models\piper_hausa  2>nul

REM YarnGPT2 (Yoruba, Igbo, Pidgin, English TTS)
echo [1/3] Downloading YarnGPT2...
huggingface-cli download saheedniyi/YarnGPT2 --local-dir voice\models\yarngpt
echo Done.
echo.

REM WavTokenizer (required by YarnGPT)
echo [2/3] Downloading WavTokenizer...
huggingface-cli download novateur/WavTokenizer-medium-speech-75token --local-dir voice\models\wavtokenizer
echo Done.
echo.

REM Piper Hausa model
echo [3/3] Downloading Piper Hausa voice...
huggingface-cli download adab-tech/murya-piper-hausa-tts --local-dir voice\models\piper_hausa
echo Done.
echo.

REM Build custom Ollama model
echo [+] Building custom MarketMind Ollama model from Modelfile...
ollama create marketmind -f Modelfile
echo Done.
echo.

echo ================================================
echo  All downloads complete!
echo  Run start.bat to launch the server.
echo ================================================
pause
