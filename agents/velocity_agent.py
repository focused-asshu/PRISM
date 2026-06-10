"""Learning Velocity Agent: rule-only date math and growth patterns."""
from __future__ import annotations

from datetime import date, datetime

SERVICE_COMPANIES = {"tcs", "wipro", "infosys", "hcl", "cognizant", "tech mahindra", "ltimindtree", "mindtree", "capgemini", "accenture"}


def parse_month(value: str) -> date:
    if not value or str(value).lower() == "present":
        return date.today()
    return datetime.strptime(value + "-01", "%Y-%m-%d").date()


def _months(start: str, end: str) -> int:
    s, e = parse_month(start), parse_month(end)
    return max(1, (e.year - s.year) * 12 + e.month - s.month)


def detect_service_to_product(candidate: dict) -> bool:
    timeline = candidate.get("career_timeline", [])
    for prev, curr in zip(timeline, timeline[1:]):
        prev_name = prev.get("company", "").lower()
        prev_service = prev.get("company_type") == "service" or any(x in prev_name for x in SERVICE_COMPANIES)
        curr_product = curr.get("company_type") in {"product", "startup"}
        if prev_service and curr_product:
            return True
    return bool(candidate.get("india_signals", {}).get("service_to_product_switch"))


def detect_plateau(candidate: dict) -> bool:
    timeline = candidate.get("career_timeline", [])
    if not timeline:
        return False
    last = timeline[-1]
    stagnant_months = _months(last.get("start", "2020-01"), last.get("end", "present"))
    few_skills = len(last.get("skills_added", [])) <= 1
    return stagnant_months >= 36 and few_skills


async def analyze(candidate: dict, job_description: str = "") -> dict:
    timeline = candidate.get("career_timeline", [])
    exp = max(float(candidate.get("experience_years") or 0.5), 0.5)
    all_skills = sum((item.get("skills_added", []) for item in timeline), [])
    skills_per_year = len(set(all_skills)) / exp
    max_observed = 3.0
    base = min(60.0, (skills_per_year / max_observed) * 60.0)
    recent_count = 0
    for item in timeline[-2:]:
        if _months(item.get("start", "2020-01"), item.get("end", "present")) <= 24 or item.get("end") == "present":
            recent_count += len(item.get("skills_added", []))
    recency_boost = min(30.0, recent_count * 4.0) * 0.3
    switch = detect_service_to_product(candidate)
    plateau = detect_plateau(candidate)
    rates = [len(i.get("skills_added", [])) / max(1, _months(i.get("start", "2020-01"), i.get("end", "present"))) for i in timeline]
    acceleration = len(rates) > 1 and rates[-1] >= rates[0]
    score = base + recency_boost + (10 if switch else 0) + (-15 if plateau else 0)
    score = round(max(0, min(100, score)), 1)
    pattern = "strong acceleration" if (acceleration or recent_count >= 3) and score >= 65 else "steady growth"
    if plateau:
        pattern = "plateau"
    reason = f"Career shows {pattern}: {len(set(all_skills))} new skills across {exp:g} years"
    if switch:
        reason += ", including a service→product intent signal"
    reason += "."
    return {"velocity_score": score, "velocity_reasoning": reason, "service_to_product_switch": switch, "plateau_detected": plateau, "velocity_pattern": pattern}
