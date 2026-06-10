"""Skill Agent: SBERT-backed skill match with project evidence checks."""
from __future__ import annotations

from core.embeddings import cosine_similarity


def _text(candidate: dict) -> str:
    skills = ", ".join(candidate.get("skills_listed", []))
    projects = " ".join(p.get("description", "") for p in candidate.get("projects", []))
    timeline = " ".join(" ".join(t.get("skills_added", [])) for t in candidate.get("career_timeline", []))
    return f"Skills: {skills}. Projects: {projects}. Recent learning: {timeline}."


def _evidence_ratio(candidate: dict) -> float:
    skills = [s.lower() for s in candidate.get("skills_listed", [])]
    evidence = (" ".join(p.get("description", "") for p in candidate.get("projects", [])) + " " + candidate.get("github_summary", "") + " " + " ".join(" ".join(t.get("skills_added", [])) for t in candidate.get("career_timeline", []))).lower()
    if not skills:
        return 0.25
    proved = sum(1 for skill in skills if skill.lower() in evidence)
    return proved / len(skills)


def _recent_bonus(candidate: dict, jd: str) -> float:
    jd_lower = jd.lower()
    recent = []
    timeline = candidate.get("career_timeline", [])[-2:]
    for item in timeline:
        recent.extend(item.get("skills_added", []))
    return min(10.0, sum(3.0 for skill in recent if skill.lower() in jd_lower))


async def analyze(candidate: dict, job_description: str) -> dict:
    semantic = cosine_similarity(_text(candidate), job_description)
    evidence = _evidence_ratio(candidate)
    penalty = 18 if evidence < 0.25 and len(candidate.get("skills_listed", [])) >= 6 else 0
    jd_lower = job_description.lower()
    listed = candidate.get("skills_listed", [])
    exact_overlap = sum(1 for skill in listed if skill.lower() in jd_lower) / max(1, len(listed))
    score = (semantic * 45) + (evidence * 25) + (exact_overlap * 25) + _recent_bonus(candidate, job_description) - penalty
    score = round(max(0, min(100, score)), 1)
    if evidence < 0.25:
        reason = "Listed skills have weak project evidence, so PRISM penalized possible keyword stuffing."
    elif semantic > 0.55:
        reason = "Skills and project evidence semantically align with the role requirements."
    else:
        reason = "Some transferable skills exist, but the direct semantic match to this JD is moderate."
    return {"skill_score": score, "skill_reasoning": reason, "skill_evidence_ratio": round(evidence, 2)}
