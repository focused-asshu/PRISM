"""Local explanation templates and optional Claude enrichment."""
from __future__ import annotations

import json
import os
from typing import Any


def mode() -> str:
    return "enhanced" if os.getenv("ANTHROPIC_API_KEY") else "local"


def recent_skill(candidate: dict) -> str:
    for item in reversed(candidate.get("career_timeline", [])):
        skills = item.get("skills_added", [])
        if skills:
            return skills[-1]
    return (candidate.get("skills_listed") or ["a relevant skill"])[0]


def background_callout(candidate: dict, agent_scores: dict) -> str:
    signals = candidate.get("india_signals", {})
    parts = []
    if candidate.get("background_type") == "self-taught" or signals.get("self_taught"):
        parts.append("Self-taught background with evidence of real production learning")
    if candidate.get("background_type") == "career-switcher" or signals.get("career_switcher"):
        parts.append("Career-switcher path suggests deliberate reinvention")
    if signals.get("tier2_tier3_city"):
        parts.append("tier-2/tier-3 India signal highlights under-discovered talent")
    if agent_scores.get("service_to_product_switch"):
        parts.append("service→product move signals strong ownership intent")
    return "; ".join(parts) + "." if parts else "Background signal is conventional, so PRISM relies more on proof of work."


def local_explanation(candidate: dict, rank: int, final_score: float, agent_scores: dict, prediction: str) -> str:
    strengths = {
        "learning velocity": agent_scores.get("velocity_score", 0),
        "validated skill evidence": agent_scores.get("skill_score", 0),
        "problem complexity": agent_scores.get("problem_score", 0),
        "communication clarity": agent_scores.get("communication_score", 0),
        "6-month potential": agent_scores.get("potential_score", 0),
    }
    top_strength = max(strengths, key=strengths.get)
    skill = recent_skill(candidate)
    jd_match = "a direct match" if skill.lower() in json.dumps(candidate).lower() else "a useful adjacent signal"
    return (
        f"Ranked #{rank} — {candidate.get('name', 'Candidate')} | PRISM Score: {final_score}\n\n"
        f"{candidate.get('name', 'Candidate')}'s {top_strength} stands out most. Their career shows a "
        f"{agent_scores.get('velocity_pattern', 'steady growth')} pattern over {candidate.get('experience_years', 'unknown')} years, "
        f"with {skill} added recently — {jd_match} to your JD requirements. "
        f"{background_callout(candidate, agent_scores)} Predicted: {prediction}"
    )


async def claude_enrich(candidate: dict, job_description: str, scores: dict) -> dict[str, Any] | None:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=key)
        prompt = """You are an expert hiring intelligence agent. Given the candidate data and job description below, predict this candidate's success probability after 6 months in the role. Focus on trajectory, growth rate, and raw potential — NOT just current skill match. Specifically reward self-taught backgrounds, non-traditional paths, tier-2/tier-3 India city candidates, career switchers. Return ONLY valid JSON: {"potential_score": number, "prediction": string, "key_strengths": [string,string,string], "red_flags": [string], "hire_confidence": "low|medium|high"}."""
        message = await client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=500,
            messages=[{"role": "user", "content": f"{prompt}\nJD: {job_description}\nCandidate: {json.dumps(candidate)}\nScores: {json.dumps(scores)}"}],
        )
        return json.loads(message.content[0].text)
    except Exception:
        return None
