"""PRISM FastAPI application."""
from __future__ import annotations

import asyncio
import csv
import importlib.util
import io
import json
import os
import time
from pathlib import Path
from typing import Any

if not os.getenv("PRISM_FORCE_MINI_FASTAPI") and importlib.util.find_spec("fastapi") and importlib.util.find_spec("pydantic"):
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field
else:
    from core.minifastapi import BaseModel, CORSMiddleware, FastAPI, Field, File, HTMLResponse, HTTPException, StaticFiles, UploadFile

from agents import communication_agent, potential_agent, problem_solver_agent, skill_agent, velocity_agent
from core.embeddings import sbert_loaded
from core.explainer import local_explanation, mode
from core.scorer import combine_final

app = FastAPI(title="PRISM", description="Potential Ranking with Intelligent Signal Modeling", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ROOT = Path(__file__).parent
FRONTEND = ROOT / "frontend" / "index.html"
CANDIDATE_DETAIL_CACHE: dict[str, dict[str, Any]] = {}


class AnalyzeRequest(BaseModel):
    job_description: str = Field(..., min_length=10)
    candidates: list[dict[str, Any]] = Field(..., min_length=1)


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    return FRONTEND.read_text(encoding="utf-8")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "model": "prism-v1", "mode": mode(), "sbert_loaded": sbert_loaded()}


def _validate_candidate(candidate: dict[str, Any], index: int) -> list[str]:
    required = ["id", "name", "city", "background_type", "experience_years", "career_timeline", "skills_listed", "projects", "writing_sample"]
    return [f"candidate[{index}] missing {field}" for field in required if field not in candidate]


async def analyze_one(candidate: dict[str, Any], job_description: str) -> dict[str, Any]:
    skill_task = skill_agent.analyze(candidate, job_description)
    velocity_task = velocity_agent.analyze(candidate, job_description)
    problem_task = problem_solver_agent.analyze(candidate, job_description)
    comm_task = communication_agent.analyze(candidate, job_description)
    skill, velocity, problem, comm = await asyncio.gather(skill_task, velocity_task, problem_task, comm_task)
    merged = {**skill, **velocity, **problem, **comm}
    potential = await potential_agent.analyze(candidate, job_description, merged)
    merged.update(potential)
    final = combine_final(merged, candidate)
    merged.update(final)
    result = {"candidate": candidate, "scores": merged, "mode": "enhanced" if potential.get("enhanced") else "local"}
    return result


@app.post("/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    start = time.perf_counter()
    errors = []
    for idx, candidate in enumerate(request.candidates):
        errors.extend(_validate_candidate(candidate, idx))
    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors[:20]})
    analyzed = await asyncio.gather(*(analyze_one(c, request.job_description) for c in request.candidates))
    analyzed.sort(key=lambda item: item["scores"]["final_score"], reverse=True)
    averages = _averages(analyzed)
    ranked = []
    CANDIDATE_DETAIL_CACHE.clear()
    for rank, item in enumerate(analyzed, 1):
        candidate, scores = item["candidate"], item["scores"]
        scores["rank"] = rank
        scores["explanation"] = local_explanation(candidate, rank, scores["final_score"], scores, scores["prediction"])
        payload = {**candidate, **scores, "agent_scores": scores, "dataset_average": averages}
        candidate_id = str(candidate["id"])
        CANDIDATE_DETAIL_CACHE[candidate_id] = payload
        ranked.append(payload)
    return {"ranked_list": ranked, "processing_time": round(time.perf_counter() - start, 3), "mode": mode(), "dataset_average": averages}


def _averages(items: list[dict[str, Any]]) -> dict[str, float]:
    keys = ["skill_score", "velocity_score", "problem_score", "communication_score", "potential_score"]
    return {key: round(sum(item["scores"].get(key, 0) for item in items) / max(1, len(items)), 1) for key in keys}


@app.get("/candidate/{candidate_id}")
async def candidate_detail(candidate_id: str) -> dict[str, Any]:
    """Return the cached detail payload created by the latest /analyze run."""
    cached = CANDIDATE_DETAIL_CACHE.get(str(candidate_id))
    if cached is None:
        raise HTTPException(status_code=404, detail="Candidate not found. Click Analyze Candidates first, then select a candidate.")
    return cached


@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    raw = await file.read()
    try:
        if file.filename and file.filename.endswith(".csv"):
            text = raw.decode("utf-8")
            rows = list(csv.DictReader(io.StringIO(text)))
            candidates = [_coerce_csv(row) for row in rows]
        else:
            parsed = json.loads(raw.decode("utf-8"))
            candidates = parsed.get("candidates", parsed) if isinstance(parsed, dict) else parsed
        if not isinstance(candidates, list):
            raise ValueError("dataset must be a list or object with candidates")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse upload: {exc}") from exc
    errors = []
    for idx, cand in enumerate(candidates):
        errors.extend(_validate_candidate(cand, idx))
    return {"candidate_count": len(candidates), "validation_summary": {"valid": not errors, "errors": errors[:20]}, "candidates": candidates}


def _coerce_csv(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    for key in ["career_timeline", "skills_listed", "projects", "hackathon_history", "india_signals", "education"]:
        if key in out and isinstance(out[key], str):
            try:
                out[key] = json.loads(out[key])
            except json.JSONDecodeError:
                out[key] = [x.strip() for x in out[key].split(";") if x.strip()]
    out["experience_years"] = float(out.get("experience_years") or 0)
    return out

app.mount("/data", StaticFiles(directory=str(ROOT / "data")), name="data")
