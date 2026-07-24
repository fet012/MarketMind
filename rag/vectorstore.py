"""
MarketMind — RAG Vector Store
rag/vectorstore.py

Builds and maintains a ChromaDB collection of daily business summaries.
Each chunk = one day's summary for one user (short, factual, retrievable).

Used ONLY for the ADVISORY intent — when the trader asks for business
advice, we retrieve the 3-5 most relevant daily summaries to give
Gemma real context instead of making things up.

Embedding model: nomic-embed-text via Ollama (fully local, fast on CPU).
"""

import os
import json
from typing import Optional
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./rag/chroma_db")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
COLLECTION_NAME = "marketmind_summaries"


# ── Embedding Function (nomic-embed-text via Ollama) ──────────

class OllamaEmbeddingFunction(chromadb.EmbeddingFunction):
    """
    Custom ChromaDB embedding function that calls Ollama's
    nomic-embed-text model locally. No internet required.
    """

    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model
        try:
            import ollama
            self._client = ollama.Client(host=OLLAMA_HOST)
        except ImportError:
            raise RuntimeError("ollama package not installed. Run: pip install ollama")

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        # Pass the entire list of strings to Ollama at once (Batching)
        # instead of looping sequentially. This is exponentially faster.
        response = self._client.embed(model=self.model, input=input)
        return response.embeddings


# ── ChromaDB Client ───────────────────────────────────────────

def get_collection() -> chromadb.Collection:
    """Return (or create) the persistent ChromaDB collection."""
    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False),
    )
    embedding_fn = OllamaEmbeddingFunction()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


# ── Index Builder ─────────────────────────────────────────────

def build_summary_text(summary: dict) -> str:
    """
    Convert a daily summary dict into a short natural-language chunk.
    Example output:
      "Wednesday 2026-07-23: Sales ₦18,000 | Expenses ₦5,500 | Profit ₦12,500.
       Top item: tomatoes (₦8,000)."
    This format is easy to retrieve and gives Gemma clear facts to reason over.
    """
    from datetime import datetime

    try:
        dt = datetime.strptime(summary["date"], "%Y-%m-%d")
        day_name = dt.strftime("%A %Y-%m-%d")
    except Exception:
        day_name = summary["date"]

    top = ""
    if summary.get("top_item"):
        top = f" Top item: {summary['top_item']} (₦{summary['top_item_amount']:,.0f})."

    return (
        f"{day_name}: "
        f"Sales ₦{summary['total_sales']:,.0f} | "
        f"Expenses ₦{summary['total_expenses']:,.0f} | "
        f"Profit ₦{summary['net_profit']:,.0f}."
        f"{top}"
    )


def index_user_summaries(user_id: str, summaries: list[dict]):
    """
    Upsert the last N daily summaries for a user into ChromaDB.
    Called after every /ingest to keep the index fresh.

    Each document ID is "{user_id}_{date}" so re-indexing the same
    day overwrites safely (upsert semantics).
    """
    if not summaries:
        return

    collection = get_collection()

    documents = []
    ids = []
    metadatas = []

    for s in summaries:
        doc_id = f"{user_id}_{s['date']}"
        text = build_summary_text(s)
        documents.append(text)
        ids.append(doc_id)
        metadatas.append({
            "user_id": user_id,
            "date": s["date"],
            "net_profit": s["net_profit"],
            "total_sales": s["total_sales"],
            "total_expenses": s["total_expenses"],
        })

    collection.upsert(
        documents=documents,
        ids=ids,
        metadatas=metadatas,
    )
    print(f"[RAG] Indexed {len(documents)} summaries for user '{user_id}'")
