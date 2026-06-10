"""Potential Agent: weighted local prediction with optional Claude enrichment."""
from __future__ import annotations

from core.explainer import claude_enrich


def _confidence(score: float) -> str:
    return "high" if score >= 82 else "medium" if score >= 62 else "low"


async def analyze(candidate: dict, job_description: str, scores: dict) -> dict:
    signals = candidate.get("india_signals", {})
    computed = scores["skill_score"] * 0.25 + scores["velocity_score"] * 0.35 + scores["problem_score"] * 0.25 + scores["communication_score"] * 0.15
    computed += 8 if candidate.get("background_type") == "self-taught" else 0
    computed += 5 if candidate.get("background_type") == "career-switcher" else 0
    computed += 5 if scores.get("service_to_product_switch") or signals.get("service_to_product_switch") else 0
    computed += 3 if signals.get("tier2_tier3_city") else 0
    computed -= 10 if scores.get("plateau_detected") and float(candidate.get("experience_years") or 0) > 4 else 0
    local_score = round(max(0, min(100, computed)), 1)
    top = max([("skill evidence", scores["skill_score"]), ("learning velocity", scores["velocity_score"]), ("problem-solving depth", scores["problem_score"]), ("communication clarity", scores["communication_score"])], key=lambda x: x[1])[0]
    outcome = "become a strong independent contributor" if local_score >= 82 else "ramp into a reliable contributor" if local_score >= 62 else "need guided onboarding before independent ownership"
    timeframe = "60–90 days" if local_score >= 82 else "the first 6 months"
    prediction = f"Based on {scores.get('velocity_pattern', 'steady growth')} and {top}, predicted to {outcome} within {timeframe}."
    local = {
        "potential_score": local_score,
        "prediction": prediction,
        "key_strengths": [top.title(), scores.get("velocity_pattern", "steady growth").title(), "India-scale hidden talent signal"],
        "red_flags": ["Plateau risk after 4+ years"] if scores.get("plateau_detected") else [],
        "hire_confidence": _confidence(local_score),
    }
    enriched = await claude_enrich(candidate, job_description, {**scores, **local})
    if enriched:
        enriched["potential_score"] = round(max(0, min(100, float(enriched.get("potential_score", local_score)))), 1)
        return {**local, **enriched, "enhanced": True}
    return {**local, "enhanced": False}
