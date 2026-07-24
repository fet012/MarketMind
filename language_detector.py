"""
MarketMind — Language Detector
language_detector.py

Detects which of the 5 supported languages a message is written in.
Uses keyword heuristics first (fast, no model call) then falls back
to langdetect for Yoruba/Hausa/Igbo.

Nigerian Pidgin is handled by heuristics ONLY because standard detectors
consistently misidentify it as English.
"""

import re
from typing import Literal

Language = Literal["pidgin", "yoruba", "igbo", "hausa", "english"]

# ── Pidgin Keywords ───────────────────────────────────────────
# These words are distinctly Pidgin and rarely appear in standard English.
PIDGIN_MARKERS = {
    "dey", "wahala", "abeg", "na", "wey", "wetin", "oga", "nna",
    "abi", "sabi", "comot", "gbo", "sha", "ehen", "ehn", "jare",
    "don", "fit", "make", "dem", "una", "im", "e don",
    "how e take", "beta", "sef", "chop", "kai"
}

# ── Yoruba Markers ────────────────────────────────────────────
YORUBA_MARKERS = {
    "mo", "ta", "ẹyin", "tomati", "owo", "èrè", "ní", "lónìí",
    "melo", "ó dára", "gbasilẹ", "náwó", "jẹ", "ọja", "dáadáa",
    "àárọ", "ọsẹ", "owó"
}

# ── Igbo Markers ──────────────────────────────────────────────
IGBO_MARKERS = {
    "agwara", "ego", "ọ dị", "edekọtara", "rere", "maka", "taa",
    "ole", "nwetara", "fọdụrụ", "ọbụ", "uru", "ihe", "m",
    "nna m", "nwanne"
}

# ── Hausa Markers ─────────────────────────────────────────────
HAUSA_MARKERS = {
    "na", "kashe", "don", "sufuri", "riba", "samu", "yau",
    "kuma", "nawa", "sayar", "rage", "shi", "ka", "ta",
    "wani", "kudi", "kasuwa", "aiki"
}

# Hausa "na" and "don" also appear in Pidgin/English, so we weight by count


def detect_language(text: str) -> Language:
    """
    Return the most likely language of the input text.
    Order of priority:
      1. Yoruba (unique diacritics are strong signal)
      2. Pidgin (keyword heuristics)
      3. Igbo (keyword heuristics)
      4. Hausa (keyword heuristics, weighted)
      5. English (default fallback)
    """
    text_lower = text.lower()
    tokens = set(re.findall(r"[a-zA-ZÀ-ÿ]+", text_lower))

    # ── 1. Yoruba — unique diacritics are a near-certain signal ──
    yoruba_diacritics = re.compile(r"[ẹọṣ]", re.IGNORECASE)
    if yoruba_diacritics.search(text):
        return "yoruba"

    # ── 2. Nigerian Pidgin — keyword count ───────────────────────
    pidgin_hits = len(tokens & PIDGIN_MARKERS)
    if pidgin_hits >= 1:
        # Single strong marker is enough for Pidgin
        return "pidgin"

    # ── 3. Igbo ──────────────────────────────────────────────────
    igbo_hits = len(tokens & IGBO_MARKERS)
    if igbo_hits >= 1:
        return "igbo"

    # ── 4. Hausa — need 2+ hits to distinguish from Pidgin/EN ────
    hausa_hits = len(tokens & HAUSA_MARKERS)
    if hausa_hits >= 2:
        return "hausa"

    # ── 5. Try langdetect for Yoruba/Hausa that lack diacritics ──
    try:
        from langdetect import detect, LangDetectException
        detected = detect(text)
        lang_map = {
            "yo": "yoruba",
            "ha": "hausa",
            "ig": "igbo",
        }
        if detected in lang_map:
            return lang_map[detected]
    except Exception:
        pass  # langdetect failure is non-fatal

    # ── 6. Default: English ───────────────────────────────────────
    return "english"


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("I sell rice two mudu, four thousand", "pidgin"),
        ("wetin be my profit today?", "pidgin"),
        ("Mo ta ẹyin ₦5000", "yoruba"),
        ("Agwara m tomato ego ₦8000", "igbo"),
        ("Na kashe ₦600 don sufuri", "hausa"),
        ("How much profit did I make today?", "english"),
        ("Sold 3 bags of garri for ₦9000", "english"),
    ]
    print("Language Detection Tests\n" + "─" * 40)
    all_pass = True
    for text, expected in tests:
        result = detect_language(text)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_pass = False
        print(f"{status} [{expected:8s}→{result:8s}] {text[:50]}")
    print("─" * 40)
    print("ALL PASS ✅" if all_pass else "SOME FAILED ❌")
