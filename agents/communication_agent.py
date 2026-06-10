"""Communication Agent: rule-only readability, structure, and specificity."""
from __future__ import annotations

import re
try:
    import textstat
except Exception:
    textstat = None

BUZZWORDS = ["passionate", "hardworking", "team player", "results-driven", "self motivated", "go getter"]


async def analyze(candidate: dict, job_description: str = "") -> dict:
    sample = candidate.get("writing_sample") or ""
    github = candidate.get("github_summary") or ""
    text = f"{sample}\n{github}"
    if len(text.strip()) < 30:
        return {"communication_score": 20, "communication_reasoning": "Very little writing evidence was available."}
    flesch = textstat.flesch_reading_ease(sample or text) if textstat else max(0, min(100, 100 - (len((sample or text).split()) / max(1, len(re.split(r"[.!?]+", sample or text))) * 2)))
    readability = max(0, min(40, (flesch + 20) / 120 * 40))
    sentences = re.split(r"[.!?]+", sample)
    avg_len = sum(len(s.split()) for s in sentences if s.strip()) / max(1, len([s for s in sentences if s.strip()]))
    structure = 8
    if "readme" in github.lower():
        structure += 8
    if any(x in text for x in ["\n-", "1.", "2.", "Setup", "Architecture"]):
        structure += 8
    if 10 <= avg_len <= 24:
        structure += 6
    numbers = len(re.findall(r"\d+", text))
    concrete = len(re.findall(r"users|latency|orders|commits|api|pipeline|database|reduced|improved|deployed", text, re.I))
    vague = sum(text.lower().count(b) for b in BUZZWORDS)
    specificity = max(0, min(30, (numbers * 3 + concrete * 2) - vague * 4 + 10))
    score = round(max(0, min(100, readability + structure + specificity)), 1)
    reason = f"Writing has Flesch readability {flesch:.0f}, average sentence length {avg_len:.0f}, and {numbers} concrete numeric signals."
    if vague:
        reason += " Buzzword-heavy phrasing reduced the score."
    return {"communication_score": score, "communication_reasoning": reason}
