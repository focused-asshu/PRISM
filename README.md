# PRISM — Potential Ranking with Intelligent Signal Modeling
> Find India's hidden talent. Predict potential, not pedigree.

## The Problem
India's hiring funnels still over-reward pedigree, metro exposure, and keyword-heavy resumes. Self-taught developers, rural students, service-company switchers, and career changers often show stronger future performance signals than their resumes suggest. Keyword ATS tools ask “who looks like the JD today?” while great hiring needs to ask “who will succeed in this role six months from now?”

## What PRISM Does Differently
PRISM ranks candidates by evidence-backed potential, not resume similarity. It combines semantic skill matching with rule-based growth, project, communication, and India-specific trajectory signals. The result is a ranked dashboard that can surface a Bhubaneswar self-taught developer above a weak IIT profile when the proof of work and learning velocity justify it.

## How It Works

```text
Candidate Dataset + Job Description
              |
              v
+-------------+------------------------------------------------+
|  Five async agents (asyncio.gather)                           |
|  1. Skill Agent          -> SBERT semantic skill evidence      |
|  2. Velocity Agent       -> date math + growth trajectory      |
|  3. Problem Agent        -> SBERT complexity + proof signals   |
|  4. Communication Agent  -> readability + specificity rules   |
|  5. Potential Agent      -> 6-month success prediction         |
+-------------+------------------------------------------------+
              |
              v
Weighted PRISM Score + Local/Enhanced Explanation + Dashboard
```

| Agent | What it measures | Method |
|---|---|---|
| Skill | Real role fit proven by listed skills and projects | SBERT semantic similarity + evidence penalty |
| Velocity | How fast the candidate learns and changes trajectory | Rule-based date math, recency, plateau, service→product detection |
| Problem Solving | Whether projects show production complexity or tutorial work | SBERT benchmark matching + hackathon/open-source/system-design rules |
| Communication | Clear thinking, concrete writing, README quality | textstat readability + structure/specificity checks |
| Potential | Six-month success probability | Weighted formula; optional Claude explanation enrichment |

| Component | Weight |
|---|---:|
| Skill score | 20% |
| Learning velocity | 25% |
| Problem solving | 20% |
| Communication | 10% |
| Potential | 25% |

Bonuses are applied once for non-traditional trajectory and India-specific intent signals.

## Setup (3 steps)

```bash
git clone <your-prism-repo-url>
cd PRISM
pip install -r requirements.txt
./uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`. The sample dataset loads automatically, so judges can click **Analyze Candidates** immediately. In locked-down cloud environments, PRISM includes a text-only `./uvicorn` runner so these commands work without downloading packages or committing binary files.

## No API Key Needed
PRISM runs fully without an API key. Local mode is the primary mode and includes all five working agents, ranking, radar charts, explanations, uploads, and sample data.

Optionally set `ANTHROPIC_API_KEY` to enrich explanation wording with Claude. If the key is absent, PRISM silently stays in **🔒 Local Mode** with no prompts, warnings, or broken features.

## Why This Beats Keyword Matching
- **Self-taught developer:** Ananya Sharma ranks highly because her FastAPI/PostgreSQL projects show production usage, recent acceleration, hackathon proof, and tier-3 hidden-talent signals — not because of college pedigree.
- **Career switcher:** Kavya Nair's mechanical-engineering background becomes a strength when paired with measurable backend delivery and clear systems thinking.
- **Rural student:** Arjun Mishra gets credit for building low-connectivity public-service software with real users, a signal a keyword-only ATS would likely flatten.

## Sample Output
A judge sees five animated agents light up, then a ranked candidate list with color-coded tiers. Selecting a candidate opens a premium detail panel with a Canvas radar chart comparing the candidate against the dataset average, all five agent scores, India signal badges, key strengths, red flags, and a specific explanation such as:

> Ranked #1 — Ananya Sharma | PRISM Score: 91. Ananya's learning velocity stands out most. Her career shows a strong acceleration pattern over 2.5 years, with FastAPI added recently — a direct match to your JD requirements. Self-taught background with evidence of real production work. Predicted: strong independent contributor within 60–90 days.

## API Endpoints

- `GET /health` — status, model, local/enhanced mode, SBERT availability.
- `POST /analyze` — accepts `{ job_description, candidates }`, returns ranked results.
- `GET /candidate/{id}` — returns the latest full candidate breakdown after analysis.
- `POST /upload` — accepts CSV or JSON candidate datasets and validates required fields.

## Project Structure

```text
PRISM/
├── main.py
├── agents/
├── core/
├── data/
│   ├── sample_dataset.json
│   └── sample_jd.json
├── frontend/
│   └── index.html
├── requirements.txt
└── README.md
```
