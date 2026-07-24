"""
MarketMind — RAG Retriever
rag/retriever.py

Queries ChromaDB to find the most relevant daily summaries for a
given user query, then formats them as a compact context block
that gets injected into the Gemma prompt for ADVISORY queries.
"""

from rag.vectorstore import get_collection


def retrieve_context(user_id: str, query: str, top_k: int = 4) -> str:
    """
    Find the top_k most relevant daily summaries for this user+query.

    Returns a formatted string like:
        --- Business History ---
        Monday 2026-07-21: Sales ₦18,000 | Expenses ₦5,500 | Profit ₦12,500. Top item: tomatoes (₦8,000).
        Tuesday 2026-07-22: Sales ₦14,000 | Expenses ₦4,000 | Profit ₦10,000. Top item: pepper (₦6,000).
        ...
        -----------------------

    This block is inserted between the system prompt and the user message
    so Gemma has real data to reason over.

    Returns an empty string if no summaries exist yet (new user).
    """
    collection = get_collection()

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
            where={"user_id": user_id},
        )
    except Exception as e:
        print(f"[RAG] Retrieval error: {e}")
        return ""

    docs = results.get("documents", [[]])[0]
    if not docs:
        return ""

    lines = "\n".join(f"• {doc}" for doc in docs)
    return f"\n--- Business History ---\n{lines}\n-----------------------\n"


def retrieve_item_context(user_id: str, top_k: int = 4) -> str:
    """
    Retrieve summaries specifically mentioning top items.
    Used when query is about item-level analysis.
    """
    return retrieve_context(user_id, "top item profit margin sales", top_k)
