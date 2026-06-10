"""Score combination rules for PRISM."""
from __future__ import annotations


def combine_final(agent_scores: dict, candidate: dict) -> dict:
    skill = agent_scores["skill_score"]
    velocity = agent_scores["velocity_score"]
    problem = agent_scores["problem_score"]
    communication = agent_scores["communication_score"]
    potential = agent_scores["potential_score"]
    raw = skill * 0.20 + velocity * 0.25 + problem * 0.20 + communication * 0.10 + potential * 0.25
    signals = candidate.get("india_signals", {})
    trajectory_bonus = 5 if signals.get("career_switcher") or signals.get("self_taught") or candidate.get("background_type") in {"self-taught", "career-switcher"} else 0
    india_signal = 3 if agent_scores.get("service_to_product_switch") or signals.get("service_to_product_switch") else 0
    score = round(min(100, raw + trajectory_bonus + india_signal))
    if score >= 90:
        tier = "Exceptional"
    elif score >= 75:
        tier = "Strong"
    elif score >= 60:
        tier = "Promising"
    else:
        tier = "Developing"
    return {"final_score": score, "tier": tier, "trajectory_bonus": trajectory_bonus, "india_signal_bonus": india_signal}
