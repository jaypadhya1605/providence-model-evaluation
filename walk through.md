# Providence — Session 3 (Model Evaluation) · 60-minute walk-through

Deck: `Providence - Model Evaluation.pptx` · 39 slides
Demo UI: `streamlit run streamlit_app.py` → http://localhost:8501
Portal: <https://ai.azure.com> → project `proj-apim-demo-jp-001` → Agents + Model catalog (Leaderboards) + Evaluation UI
Repo: <https://github.com/jaypadhya1605/foundry-agent-observatory> (folder-3, CI workflow at `.github/workflows/model-evaluation.yml`)

## Pre-call setup (do this 5 minutes before)

```powershell
cd "C:\Users\jaypadhya\OneDrive - Microsoft\Desktop\Providence\Azure Foundry Deep Dive Session\3.Model Evaluation"
.\.venv\Scripts\Activate.ps1
az account show   # confirm sub 06c76c82-... and signed in
streamlit run streamlit_app.py --server.port=8501
```

Open **5 tabs** / windows:

1. **PowerPoint** — `Providence - Model Evaluation.pptx` in presenter view (so you see speaker notes).
2. **Browser — Streamlit** — http://localhost:8501.
3. **Browser — Foundry portal** — https://ai.azure.com → `proj-apim-demo-jp-001` → **Agents** blade. Should already show `providence-clinical-triage:2`. Keep a second tab on **Model catalog → Leaderboards** and a third on **Evaluation** ready.
4. **Browser — GitHub** — https://github.com/jaypadhya1605/foundry-agent-observatory → **Actions** tab, with the `.github/workflows/model-evaluation.yml` workflow visible.
5. **Terminal** — venv activated, in the session folder. For live script runs.

> **Do not re-run the long evaluation scripts during the call.** Everything under `eval-outputs/` is pre-computed. The Streamlit tabs read that JSON directly. Only run lightweight scripts live (04, 09).

## Timing (60 min total)

| Slide(s) | Section | Mode | Time | Cumulative |
|---|---|---|---|---|
| 1 | Title + open | Slides | 1 min | 1 |
| 2 | Agenda | Slides | 1 min | 2 |
| 3–4 | The Providence ask + two-lens model | Slides | 3 min | 5 |
| 5–7 | Foundry context (factory / catalog / unified) | Slides | 2 min | 7 |
| 8–11 | Model deployment + what we've deployed | Slides | 3 min | 10 |
| 12–13 | **Use cases covered today** (clinical vs non-clinical) | Slides | 2 min | 12 |
| 14–15 | Built-in evaluators explained | Slides | 2 min | 14 |
| 16 | **DEMO 0** — Foundry Model Catalog + Leaderboard (portal) | Demo | 2 min | 16 |
| 17 | **DEMO 1** — built-ins + platform approval | Demo | 5 min | 21 |
| 18 | **DEMO 2** — clinical use-case | Demo | 4 min | 25 |
| 19 | **DEMO 3** — non-clinical use-case | Demo | 2 min | 27 |
| 20–21 | Custom evaluators overlay | Slides | 2 min | 29 |
| 22 | **DEMO 4** — custom evaluators | Demo | 3 min | 32 |
| 23 | Content Safety | Slides | 1 min | 33 |
| 24 | **DEMO 5** — red-team | Demo | 3 min | 36 |
| 25–26 | Agent evaluation intro | Slides | 2 min | 38 |
| 27 | **DEMO 6** — agent create + eval + portal | Demo | 4 min | 42 |
| 28–29 | Three evaluation modes explainer | Slides | 2 min | 44 |
| 30 | **DEMO 7** — automated / manual / human on same 5 rows | Demo | 4 min | 48 |
| 31 | Exception process intro | Slides | 1 min | 49 |
| 32 | **DEMO 8** — exception decision | Demo | 3 min | 52 |
| 33 | Architecture | Slides | 1 min | 53 |
| 34–35 | CI/CD evaluation — GitHub Actions | Slides | 1 min | 54 |
| 36 | **DEMO 9** — PR fails the governance gate (GitHub) | Demo | 2 min | 56 |
| 37–38 | Providence asks delivered + takeaways | Slides | 2 min | 58 |
| 39 | Q & A | Open | 2 min | 60 |

## Demo cue sheet

### DEMO 0 (slide 16) — Foundry Model Catalog + Leaderboard

1. Switch to the **Foundry portal tab** → click **Model catalog** in the left rail → open the **Leaderboards** view.
2. Show the **Quality** leaderboard (ranked by MMLU / GPQA / BBH). Point out `gpt-5` and `gpt-5-mini` positions.
3. Click the **Safety** leaderboard tab — note which models drop rank.
4. Click **Cost & performance** — show $/1K tok and P95 latency.
5. Punchline: *"Leaderboards give you the short-list in 2 minutes with zero code. They do NOT know whether a model is safe for YOUR clinical data — that's what Lens 2 proves next."*

### DEMO 1 (slide 17) — built-ins + platform approval

1. Slide 15 on screen, say: "Let me show you what a built-in evaluator actually returns."
2. Terminal: `.\.venv\Scripts\python.exe 04_builtin_evaluators_explained.py` — runs ~60 seconds. Scroll to the `groundedness` output and point at the `groundedness_reason` string and `groundedness_threshold`.
3. Back to Streamlit → **tab "01 — Platform approval"**. Show the APPROVED_FOR_CATALOG verdict for both `gpt-5` and `gpt-5-mini`. Click into one row to show the per-metric scores.
4. Return to slide 15. Punchline: *"This is Lens 1. One-time gate. Every future use-case starts from this approved pool."*

### DEMO 2 (slide 16) — clinical use-case

1. **Do not re-run.** Go straight to Streamlit → **tab "02 — Clinical"**.
2. Show the table: `clinical_safety_score 4.9` for both models. `hipaa_leak_leaked 0.1 / 0.0`.
3. Filter to the single failing HIPAA row. Show the response text — the regex catch.
4. Punchline: *"gpt-5-mini beat gpt-5 on the HIPAA gate for this sample. Generic leaderboards would never tell you that."*

### DEMO 3 (slide 17) — non-clinical use-case

1. Streamlit → **tab "03 — Non-clinical"**. 30 seconds total.
2. Point at: same harness, different evaluators, different dataset. Relevance 4.9, fluency 4.0.
3. Punchline: *"One framework, two lenses, many workflows."*

### DEMO 4 (slide 20) — custom evaluators

1. Streamlit → **tab "07 — Custom evaluators"**.
2. Show the three custom metrics as separate columns. Click the failing HIPAA row; show which regex matched (`phone`, `email`, etc.).
3. Mention: HIPAA evaluator is **deterministic regex** — not an LLM. Zero cost, zero flakiness.

### DEMO 5 (slide 22) — red-team

1. Streamlit → **tab "08 — Red-team"**.
2. Show `refusal_detected = 0.1` and `dangerous_leak = 0.2` on gpt-5.
3. Click 2–3 adversarial rows to show the jailbreak style (role-play prompts, PHI fishing).
4. Punchline: *"This is the rehearsal. Better to see 20% here than 0.1% in production."*

### DEMO 6 (slide 25) — agent create + eval

1. Switch to the **Foundry portal tab**. Show `providence-clinical-triage:2` in the **Agents** blade. Click it — show the tools `triage_lookup` and `escalate_to_human`.
2. Emphasise: *"This is a NEW Foundry agent, not a classic Assistant. Note the id format `name:version`, not `asst_*`."*
3. (Optional, 30s) Terminal: `.\.venv\Scripts\python.exe 05_create_foundry_agent.py` — re-creates the agent, fires the smoke-test, prints the tool call.
4. Streamlit → **tab "06 — Agent evaluation"**. Show the three agent metrics: IntentResolution 4.0, TaskAdherence 0.8, ToolCallAccuracy 5.0.
5. Punchline: *"The agent picked `escalate_to_human` on 'crushing chest pain' — clinical-safety operationalized as a tool-call metric."*

### DEMO 7 (slide 30) — automated / manual / human (three modes)

1. Terminal: `.\.venv\Scripts\python.exe 10_evaluation_modes.py` — runs ~30 seconds end-to-end.
2. Point at the three output files as they print:
   - `eval-outputs\10-automated.result.json` — `clinical_safety_score 5.0`, `hipaa_leak_rate 0.0` (automated).
   - `eval-outputs\10-manual-upload.jsonl` — 5 rows ready for the Foundry **Evaluation UI**.
   - `eval-outputs\10-human-aggregate.json` — `clinical_safety_mean 4.8`, `would_block_rate 0.0` (human SME average).
3. Open the **manual JSONL** in VS Code — show `{query, response, ground_truth}` format.
4. (Optional 60s) Switch to the **Foundry Evaluation tab** → **+ New evaluation** → **Bulk run**. Upload `10-manual-upload.jsonl`. Pick Groundedness + Relevance + Fluency. Click Run. You don't have to wait for it — just prove the one-click path exists.
5. Open `datasets\human-eval-template.csv` — show the pre-scored SME rows (5/5, 4/5, 5/5…).
6. Punchline: *"Automated (5.0) vs human (4.8) — 0.2 gap. The LLM judge is well-calibrated on this rubric. That's your calibration signal."*

### DEMO 8 (slide 32) — exception decision

1. Terminal: `.\.venv\Scripts\python.exe 09_exception_process.py` — runs in ~2 seconds, reads all prior JSON.
2. Show the output: both models → `AUTO_DENIED` because of the 10% HIPAA leak rate.
3. Open `eval-outputs\exception-decision-gpt-5.json` in VS Code. Point at `hard_failures`, `quality_failures`, `metrics_observed`. *"This JSON is the audit log. Route it to ServiceNow or the governance inbox — it's a file, not a meeting."*
4. Streamlit → **tab "09 — Exception process"** for a final visual summary.

### DEMO 9 (slide 36) — GitHub Actions PR gate

1. Switch to the **GitHub tab** → repo `jaypadhya1605/foundry-agent-observatory`.
2. Open `.github/workflows/model-evaluation.yml`. Scroll through the triggers (pull_request, cron, workflow_dispatch), the OIDC login step, and the evaluation run (01→02→03→07→08→09).
3. Click the **Actions** tab → open the most recent `Model Evaluation (Providence)` run. Expand the **09 Exception process** step.
4. Show: job status ❌ red X when any model = `AUTO_DENIED`. Scroll to **Summary → Artifacts** → `providence-eval-outputs` contains every `*.result.json`.
5. If a PR is open, open its **Conversation** tab → show the bot-posted table (Model | Decision | Failures).
6. Punchline: *"The governance policy now blocks a merge. Not a meeting, not an email. Every main-branch commit has an audited evaluation run attached to its SHA."*

## Anticipated Q & A

| Question | Answer |
|---|---|
| Does the exception decision actually block deployment? | Today it writes an audit JSON. Wiring into CD / ServiceNow is ~1 day of plumbing. |
| Can we run this on our own Foundry tenant? | Yes. Fork the repo, edit `.env`, `az login`, run scripts 01-09. |
| What about fine-tuned models? | Same harness. Every new fine-tune version re-runs script 01 (platform approval). |
| How much does continuous evaluation cost? | Nightly eval, 100 rows × 2 models ≈ a few dollars/week in inference. No infra fixed cost. |
| How do you handle prompt drift in judges? | Judge deployment + API version are pinned in `_config.py::judge_model_config`. Re-run 04 any time you suspect drift. |
| Why gpt-4o as the judge? | Stable, well-calibrated for rubric-following, cheaper than gpt-5 for judge-scale workloads. You can swap via `JUDGE_MODEL` env var. |
| What if Foundry adds a new built-in evaluator next month? | Script 04 is designed to iterate over `azure.ai.evaluation`; adding a new evaluator is a one-line change. |
| Does this work for multi-agent workflows? | Script 06 evaluates a single agent. For multi-agent, add an aggregator evaluator that scores the orchestration trace — same `evaluate()` API. |

## Rollback / recovery

If any demo script fails live:

- **Network/API flake during a run** → switch immediately to Streamlit; all results are on disk.
- **Agent not visible in portal** → refresh the Agents blade; worst case, re-run `05_create_foundry_agent.py` (creates a new version `:3`).
- **Streamlit crashes** → `streamlit run streamlit_app.py --server.port=8502` in a fresh terminal.
- **Long lag during script run** → you have <60s before attention drops. Abort with `Ctrl+C` and pivot to the Streamlit pre-computed view.

## Close-out

- Leave the repo, the deck, and the Streamlit app with Providence.
- Follow-up actions (from slide 30):
  1. Swap in 100–200 rows of real Providence clinical Q&A into `datasets/clinical.jsonl`.
  2. Wire `exception-decision-*.json` into ServiceNow / approval flow.
  3. Decide `hard_fail` vs `needs_review` thresholds with their governance board.
  4. Run script 04 against the two models they're evaluating this quarter.

## File quick-reference

| File | Purpose |
|---|---|
| [Providence - Model Evaluation.pptx](Providence%20-%20Model%20Evaluation.pptx) | Unified 39-slide deck (has speaker notes) |
| [10_evaluation_modes.py](10_evaluation_modes.py) | Automated / manual / human modes on 5 clinical rows |
| [.github/workflows/model-evaluation.yml](.github/workflows/model-evaluation.yml) | CI/CD evaluation workflow (PR gate + nightly cron) |
| [README.md](README.md) | Deep technical README |
| [Foundry_agentic-creation.md](Foundry_agentic-creation.md) | NEW-vs-classic agent creation guide |
| [streamlit_app.py](streamlit_app.py) | Demo UI (9 tabs, reads from `eval-outputs/`) |
| `01_*..09_*.py` | Individual evaluation scripts |
| `_custom_evaluators.py` | Providence overlay (ClinicalSafety, HIPAALeak, MedicalCitation) |
| `eval-outputs/` | Pre-computed JSON results (safe to re-demo) |
| `datasets/` | Clinical, non-clinical, adversarial prompt sets |
