"""Problem Solving Agent: SBERT complexity matching plus explicit signal rules."""
from __future__ import annotations

from core.embeddings import best_similarity

BENCHMARKS = {
    "simple CRUD app": 35,
    "basic utility script": 25,
    "REST API with auth and database": 60,
    "distributed system": 85,
    "ML pipeline": 82,
    "real-time processing": 82,
    "open source library": 78,
    "production system with scaling and monitoring": 90,
}


async def analyze(candidate: dict, job_description: str = "") -> dict:
    projects = candidate.get("projects", [])
    if not projects:
        return {"problem_score": 15, "problem_reasoning": "No project descriptions were available to prove problem complexity."}
    scores, matched = [], []
    for project in projects:
        desc = project.get("description", "")
        sim, phrase = best_similarity(desc, BENCHMARKS.keys())
        scores.append(BENCHMARKS.get(phrase, 40) * (0.75 + sim * 0.25))
        matched.append(phrase)
    base = sum(scores) / len(scores)
    text = " ".join([p.get("description", "") for p in projects] + candidate.get("hackathon_history", []) + [candidate.get("github_summary", "")]).lower()
    bonus = 0
    if "win" in text or "winner" in text:
        bonus += 15
    if candidate.get("open_source") or "open source" in text:
        bonus += 10
    if "system design" in text or "distributed" in text:
        bonus += 10
    if any(x in text for x in ["tutorial", "clone", "following along"]):
        bonus -= 10
    if "readme" not in text:
        bonus -= 5
    score = round(max(0, min(100, base + bonus)), 1)
    reason = f"Projects map closest to {', '.join(sorted(set(matched))[:2])}; rule signals adjusted for hackathons, open source, and tutorial risk."
    return {"problem_score": score, "problem_reasoning": reason}
