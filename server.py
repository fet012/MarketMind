"""
MarketMind — FastAPI Server
server.py

The bridge between the mobile app and the local Gemma model.
Runs on http://0.0.0.0:8000 so the mobile app can reach it over Wi-Fi.

Endpoints:
  POST /chat      — main text chat
  POST /voice     — audio → STT → chat → TTS → audio
  POST /ingest    — mobile app pushes a transaction directly
  GET  /summary   — today's financial summary (for app dashboard)
  GET  /health    — health check / model warm-up

QUERY_PROFIT never touches the LLM — reads SQLite directly (<50ms).
"""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

# ── Internal modules ──────────────────────────────────────────
from db.ledger import (
    init_db,
    get_or_create_user,
    log_transaction,
    get_today_summary,
    get_recent_summaries,
    get_item_breakdown,
)
from language_detector import detect_language
from intent_classifier import classify_intent
from rag.vectorstore import index_user_summaries
from rag.retriever import retrieve_context, retrieve_item_context

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMMA_MODEL = "gemma-4-26b-a4b-it"
genai.configure(api_key=GOOGLE_API_KEY)
PORT = int(os.getenv("PORT", 8000))

# Load prompt files
_PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT    = (_PROMPTS_DIR / "system_prompt.txt").read_text(encoding="utf-8")
FEW_SHOT_EXAMPLES = json.loads((_PROMPTS_DIR / "few_shot_examples.json").read_text(encoding="utf-8"))

from contextlib import asynccontextmanager

# ── FastAPI App ───────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"[Server] MarketMind API started on port {PORT}")
    print(f"[Server] Gemma model: {GEMMA_MODEL} via Google AI Studio")
    # Warm up Ollama so the first real request isn't slow
    try:
        _gemma_client.generate_content("hi")
        print("[Server] Gemma warm-up complete ✅")
    except Exception as e:
        print(f"[Server] ⚠ Gemma warm-up failed: {e}")
        
    yield

app = FastAPI(
    title="MarketMind AI",
    description="Local AI assistant for Nigerian market traders",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Mobile app on same LAN
    allow_methods=["*"],
    allow_headers=["*"],
)

_gemma_client = genai.GenerativeModel(GEMMA_MODEL)


# ── Request / Response Models ─────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    stream: bool = False

class IngestRequest(BaseModel):
    user_id: str = "default"
    type: str                    # "sale" or "expense"
    item: str
    amount: float
    quantity: Optional[str] = None
    language: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    action: str
    data: dict
    language: str


# ── Helpers ───────────────────────────────────────────────────

def _build_few_shot_messages() -> list[dict]:
    """Convert few_shot_examples.json into Ollama chat message format."""
    messages = []
    
    # ── SPEED OPTIMIZATION ──
    # Sending all 25+ examples causes a massive CPU bottleneck during 
    # the 'Prompt Evaluation' phase (takes ~40s on a 10th Gen i5).
    # We only send 5 carefully selected examples to keep the context 
    # window tiny and lightning fast.
    
    # Pick indices: 0 (sale), 4 (expense), 7 (profit), and the last 2 (mixed/edge cases)
    selected_indices = [0, 4, 7, -2, -1]
    
    for idx in selected_indices:
        try:
            ex = FEW_SHOT_EXAMPLES[idx]
            if "user" in ex and "assistant" in ex:
                messages.append({"role": "user",      "content": ex["user"]})
                messages.append({"role": "assistant", "content": ex["assistant"]})
        except IndexError:
            continue

    return messages


def _call_gemma(user_message: str, extra_context: str = "") -> dict:
    system = SYSTEM_PROMPT
    if extra_context:
        system = system + "\n\nRELEVANT BUSINESS DATA:\n" + extra_context

    # Build full prompt for Google AI Studio
    few_shots = _build_few_shot_messages()
    few_shot_text = ""
    for msg in few_shots:
        role = "User" if msg["role"] == "user" else "Assistant"
        few_shot_text += f"{role}: {msg['content']}\n"

    full_prompt = f"{system}\n\n{few_shot_text}\nUser: {user_message}\nAssistant:"

    response = _gemma_client.generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=2048,
        )
    )

    raw = response.text.strip()

    # Gemma 4's thinking mode often outputs reasoning text before/around
    # the real JSON answer, and sometimes repeats it. Instead of naively
    # slicing from the first { to the last } (which grabs across unrelated
    # braces), we scan for every well-formed {...} block by tracking brace
    # depth, then try the LAST one first — Gemma tends to put its final
    # answer at the end.
    candidates = []
    depth = 0
    start = None
    for i, ch in enumerate(raw):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    candidates.append(raw[start:i+1])
                    start = None

    for json_str in reversed(candidates):
        try:
            parsed = json.loads(json_str)
            # Sanity check: we expect at least a "reply" or "data" key
            if isinstance(parsed, dict) and ("reply" in parsed or "data" in parsed):
                return parsed
        except json.JSONDecodeError:
            continue

    # Middle ground: if the model replies in plain text instead of JSON,
    # or if JSON parsing entirely fails, pass the raw text directly to the user!
    return {
        "reply": raw,
        "action": "NONE",
        "data": {"transactions": []},
    }

def _format_profit_reply(summary: dict, language: str) -> str:
    """Format a profit summary reply in the trader's language — no LLM needed."""
    sales    = summary["total_sales"]
    expenses = summary["total_expenses"]
    profit   = summary["net_profit"]

    if sales == 0 and expenses == 0:
        replies = {
            "english": "No records yet for today. Start logging your sales!",
            "pidgin":  "No record for today yet. Start enter your sales!",
            "yoruba":  "Ko sí ìgbàsilẹ fún ọjọ́ oni. Bẹ̀rẹ̀ títẹ àwọn tàtà rẹ!",
            "igbo":    "Ọ dịghị ndekọ maka taa. Bido idekọ ahịa gị!",
            "hausa":   "Babu bayanan yau tukuna. Fara rikodin sayarwarku!",
        }
        return replies.get(language, replies["english"])

    top = ""
    if summary.get("top_item"):
        if language == "pidgin":
            top = f" {summary['top_item']} bring you the most — ₦{summary['top_item_amount']:,.0f}."
        elif language == "yoruba":
            top = f" {summary['top_item']} mú owó jù lọ — ₦{summary['top_item_amount']:,.0f}."
        elif language == "igbo":
            top = f" {summary['top_item']} wetara ego karịa — ₦{summary['top_item_amount']:,.0f}."
        elif language == "hausa":
            top = f" {summary['top_item']} ya kawo kuɗi mafi yawa — ₦{summary['top_item_amount']:,.0f}."
        else:
            top = f" Top item: {summary['top_item']} (₦{summary['top_item_amount']:,.0f})."

    templates = {
        "english": f"Today you sold ₦{sales:,.0f} and spent ₦{expenses:,.0f}. Your profit is ₦{profit:,.0f}.{top}",
        "pidgin":  f"Today you sell ₦{sales:,.0f} and you spend ₦{expenses:,.0f}. Profit wey remain na ₦{profit:,.0f}.{top}",
        "yoruba":  f"Lónìí o ta ₦{sales:,.0f} o sì náwó ₦{expenses:,.0f}. Èrè rẹ jẹ ₦{profit:,.0f}.{top}",
        "igbo":    f"Taa i rere ₦{sales:,.0f} ma i were ₦{expenses:,.0f}. Uru gị bụ ₦{profit:,.0f}.{top}",
        "hausa":   f"Yau ka sayar da ₦{sales:,.0f} kuma ka kashe ₦{expenses:,.0f}. Ribar gida ₦{profit:,.0f}.{top}",
    }
    return templates.get(language, templates["english"])


# ── Routes ────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "model": GEMMA_MODEL}


@app.get("/summary")
async def get_summary(user_id: str = Query(default="default")):
    """Return today's financial summary for the app dashboard."""
    get_or_create_user(user_id)
    summary = get_today_summary(user_id)
    return summary


@app.get("/transactions")
async def get_transactions(user_id: str = Query(default="default"), limit: int = Query(default=50)):
    """Return recent transactions for the app dashboard."""
    get_or_create_user(user_id)
    from db.ledger import get_recent_transactions
    transactions = get_recent_transactions(user_id, limit)
    return {"transactions": transactions}


@app.post("/ingest")
async def ingest(req: IngestRequest):
    """
    Mobile app pushes a transaction directly (bypassing AI parsing).
    Use this for structured form-entry in the app UI.
    After writing, rebuilds the RAG index for this user.
    """
    get_or_create_user(req.user_id, req.language or "english")
    tx_id = log_transaction(
        user_id=req.user_id,
        tx_type=req.type,
        item=req.item,
        amount=req.amount,
        quantity=req.quantity,
        language=req.language,
    )
    # Rebuild RAG index with fresh summaries
    summaries = get_recent_summaries(req.user_id, days=30)
    index_user_summaries(req.user_id, summaries)

    return {"status": "ok", "transaction_id": tx_id}


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Main chat endpoint. Routes by intent:
      - QUERY_PROFIT → SQLite only, no LLM (<50ms)
      - LOG_*        → Gemma parses, writes to SQLite
      - ADVISORY     → RAG + Gemma
      - UNKNOWN      → Gemma (fallback)
    """
    user = get_or_create_user(req.user_id)
    language = detect_language(req.message)
    intent = classify_intent(req.message)
    

    # ── QUERY_PROFIT: fast path, no LLM ──────────────────────
    if intent == "QUERY_PROFIT":
        summary = get_today_summary(req.user_id)
        reply   = _format_profit_reply(summary, language)
        return ChatResponse(
            reply=reply,
            action="QUERY_PROFIT",
            data={
                "total_sales":     summary["total_sales"],
                "total_expenses":  summary["total_expenses"],
                "net_profit":      summary["net_profit"],
            },
            language=language,
        )

    # ── GREETING: fast path, no LLM ───────────────────────────
    if intent == "GREETING":
        greetings = {
            "english": "Hello! How can I help you track your sales or expenses today?",
            "pidgin":  "I hail! Wetin you wan record today?",
            "yoruba":  "Ẹ n lẹ! Bawo ni mo ṣe le ran ọ lọwọ lati ṣajọ rẹ loni?",
            "igbo":    "Ndewo! Kedu ka m ga-esi nyere gị aka idetu ahịa gị taa?",
            "hausa":   "Sannu! Yaya zan iya taimaka maka game da tallace-tallace yau?",
        }
        return ChatResponse(
            reply=greetings.get(language, greetings["english"]),
            action="NONE",
            data={"transactions": []},
            language=language,
        )

    # ── ADVISORY: RAG + Gemma ─────────────────────────────────
    if intent == "ADVISORY":
        rag_context = retrieve_context(req.user_id, req.message, top_k=4)
        item_ctx    = retrieve_item_context(req.user_id, top_k=3)
        context     = rag_context + item_ctx
        result = _call_gemma(req.message, extra_context=context)
        return ChatResponse(
            reply=result.get("reply", ""),
            action=result.get("action", "ADVISORY"),
            data=result.get("data", {}),
            language=language,
        )

    # ── LOG_SALE / LOG_EXPENSE: Gemma parses, write to DB ────
    if intent in ("LOG_SALE", "LOG_EXPENSE"):
        result = _call_gemma(req.message)
        data   = result.get("data", {})
        
        transactions = data.get("transactions", [])
        if not transactions:
            # Fallback for old model behavior
            if data.get("item") and data.get("amount") is not None:
                transactions = [data]

        logged_any = False
        for tx in transactions:
            if tx.get("item") and tx.get("amount") is not None:
                tx_type = tx.get("type") or ("sale" if intent == "LOG_SALE" else "expense")
                log_transaction(
                    user_id  = req.user_id,
                    tx_type  = tx_type,
                    item     = tx["item"],
                    amount   = float(tx["amount"]),
                    quantity = tx.get("quantity"),
                    raw_input= req.message,
                    language = language,
                )
                logged_any = True
                
        if logged_any:
            # Rebuild RAG index ONLY for today! 
            # Re-embedding 30 days sequentially on CPU takes up to a minute.
            # We just need to update today's chunk since older days haven't changed.
            today_summary = get_today_summary(req.user_id)
            index_user_summaries(req.user_id, [today_summary])

        return ChatResponse(
            reply=result.get("reply", ""),
            action=result.get("action", intent),
            data=data,
            language=language,
        )

    # ── UNKNOWN: pass straight to Gemma ──────────────────────
    result = _call_gemma(req.message)
    return ChatResponse(
        reply=result.get("reply", ""),
        action=result.get("action", "NONE"),
        data=result.get("data", {}),
        language=language,
    )


@app.post("/voice")
async def voice(
    audio: UploadFile = File(...),
    user_id: str = Query(default="default"),
):
    """
    Voice endpoint:
      1. Receive audio from mobile app
      2. STT → text (faster-whisper)
      3. Route through /chat logic
      4. Return JSON response (Skipping TTS per user request)
    """
    from voice.stt import transcribe

    audio_bytes = await audio.read()

    # Step 1: Transcribe
    stt_result = transcribe(audio_bytes)
    text = stt_result
    if not text:
        raise HTTPException(status_code=400, detail="Could not transcribe audio.")

    # Step 2: Run through chat logic
    chat_req = ChatRequest(message=text, user_id=user_id)
    chat_resp = await chat(chat_req)

    # Step 3: Return JSON directly
    return {
        "transcript": text,
        "reply": chat_resp.reply,
        "language": chat_resp.language,
        "action": chat_resp.action,
        "data": chat_resp.data,
    }

# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",   # Reachable over local Wi-Fi
        port=PORT,
        reload=True,      # Auto-restart enabled
        log_level="info",
    )
