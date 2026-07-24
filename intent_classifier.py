"""
MarketMind — Intent Classifier
intent_classifier.py

Fast rule-based router. Classifies user messages into one of four intents
WITHOUT calling the LLM — saves a full model roundtrip for common cases.

Critical: QUERY_PROFIT never reaches Gemma at all. The server reads
SQLite directly and formats a reply in < 50ms.
"""

import re
from typing import Literal

Intent = Literal["LOG_SALE", "LOG_EXPENSE", "QUERY_PROFIT", "ADVISORY", "GREETING", "UNKNOWN"]


# ── Keyword Banks (multi-language) ────────────────────────────

# Signals that the user logged a SALE
SALE_KEYWORDS = {
    # English
    "sell", "sold", "sale", "selling",
    # Pidgin
    "i sell", "don sell",
    # Yoruba
    "ta", "mo ta", "àtajà",
    # Igbo
    "rere", "agwara", "azụ",
    # Hausa
    "sayar", "na sayar", "mun sayar",
}

# Signals that the user logged an EXPENSE / PURCHASE
EXPENSE_KEYWORDS = {
    # English
    "buy", "bought", "spend", "spent", "expense", "cost", "purchase",
    "transport", "loading", "market fee", "levy", "tax", "pay", "paid",
    # Pidgin
    "i buy", "i spend", "i spend money", "cost me", "transport cost",
    # Yoruba
    "ra", "mo ra", "náwó", "owó tí mo ná",
    # Igbo
    "zụta", "were ego", "kasụ",
    # Hausa
    "kashe", "saye", "na kashe", "na saya", "sufuri", "jigilar kaya",
}

# Signals that the user wants profit/summary info
PROFIT_KEYWORDS = {
    # English
    "profit", "how much", "total", "summary", "balance",
    "how much did", "how much have", "what is my", "today's",
    # Pidgin
    "how much profit", "i dey make profit", "wetin be my profit",
    "wetin be my total", "how much i make", "how e dey",
    # Yoruba
    "èrè", "melo ni", "owó melo", "àpapọ̀",
    # Igbo
    "ego ole", "uru ole", "nwetara", "ego m",
    # Hausa
    "riba", "nawa", "jimla", "kuɗi nawa",
}

# Signals that the user wants business advice / analytics
ADVISORY_KEYWORDS = {
    # English
    "best", "which item", "most profit", "advice", "suggest",
    "why", "improve", "analyse", "analyze", "compare", "week",
    "monday", "trend", "margin", "reduce", "increase",
    # Pidgin
    "which item", "wetin i do well", "why my profit dey small",
    "which one better", "how to improve", "wetin bring", "abeg advise",
    # Yoruba
    "èyí tó dára jù", "kí ni mo lè ṣe", "ìmọ̀ràn",
    # Igbo
    "nke kacha", "gwa m ihe", "enyere m aka",
    # Hausa
    "wanne", "mafi kyau", "shawarar", "me zan yi",
}


# Signals that the user is just saying hello
GREETING_KEYWORDS = {
    # English
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening", "greetings",
    # Pidgin
    "how far", "how you dey", "how bodi", "i hail", "how market",
    # Yoruba
    "ẹ n lẹ", "bawo ni", "ẹ káàárọ̀", "ẹ káàsán",
    # Igbo
    "ndewo", "kedu", "ụtụtụ ọma",
    # Hausa
    "sannu", "ina kwana", "barka da safiya",
}

# ── Classifier ────────────────────────────────────────────────

def classify_intent(text: str) -> Intent:
    """
    Classify a user message into one of 5 intents using keyword matching.

    Matching is done on lowercase text. Multi-word phrases are checked
    first (more specific), then single words (broader).

    Returns:
        "LOG_SALE"     — user recorded a sale
        "LOG_EXPENSE"  — user recorded an expense / purchase
        "QUERY_PROFIT" — user wants profit / summary data
        "ADVISORY"     — user wants business advice / analytics
        "UNKNOWN"      — couldn't classify; route to Gemma anyway
    """
    lower = text.lower().strip()

    # Score each intent
    scores = {
        "LOG_SALE": _score(lower, SALE_KEYWORDS),
        "LOG_EXPENSE": _score(lower, EXPENSE_KEYWORDS),
        "QUERY_PROFIT": _score(lower, PROFIT_KEYWORDS),
        "ADVISORY": _score(lower, ADVISORY_KEYWORDS),
        "GREETING": _score(lower, GREETING_KEYWORDS),
    }

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score == 0:
        return "UNKNOWN"

    # Disambiguation: "sell" can appear in advisory ("which item I sell most")
    # If advisory also scored, prefer ADVISORY if its score is >= LOG_SALE score
    if best_intent == "LOG_SALE" and scores["ADVISORY"] >= scores["LOG_SALE"]:
        return "ADVISORY"

    return best_intent  # type: ignore


def _score(text: str, keywords: set) -> int:
    """
    Count how many keywords from the set appear in text.
    Multi-word phrases score +2 (more specific signal).
    Single words score +1.
    """
    score = 0
    for kw in keywords:
        if " " in kw:
            if kw in text:
                score += 2
        else:
            # Word-boundary match to avoid "sell" matching "seller"
            if re.search(rf"\b{re.escape(kw)}\b", text):
                score += 1
    return score


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("I sell rice two mudu, four thousand",        "LOG_SALE"),
        ("I spend 500 for transport today",             "LOG_EXPENSE"),
        ("How much profit I make today?",               "QUERY_PROFIT"),
        ("I dey make profit?",                          "QUERY_PROFIT"),
        ("which item I dey make the most money?",       "ADVISORY"),
        ("why my profit dey small?",                    "ADVISORY"),
        ("Mo ta ẹyin ₦5000",                           "LOG_SALE"),
        ("Agwara m tomato ego ₦8000",                  "LOG_SALE"),
        ("Na kashe ₦600 don sufuri",                   "LOG_EXPENSE"),
        ("Nawa riba na samu yau?",                      "QUERY_PROFIT"),
        ("Sold 3 bags of garri for ₦9000",              "LOG_SALE"),
        ("Bought tomatoes ₦40,000",                    "LOG_EXPENSE"),
        ("Which product brings the most profit?",       "ADVISORY"),
        ("How much did I make today?",                  "QUERY_PROFIT"),
        ("Eggs bring highest profit margin this week",  "ADVISORY"),
    ]

    print("Intent Classification Tests\n" + "─" * 50)
    all_pass = True
    for text, expected in tests:
        result = classify_intent(text)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_pass = False
        print(f"{status} [{expected:15s} → {result:15s}] {text[:45]}")
    print("─" * 50)
    print("ALL PASS ✅" if all_pass else "SOME FAILED ❌")
