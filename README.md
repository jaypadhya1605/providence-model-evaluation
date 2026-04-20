# Providence — Session 3: Model Evaluation

> Repo: <https://github.com/jaypadhya1605/providence-model-evaluation>
>
> Third of a three-session Foundry deep-dive for Providence Health (after
> Session 1 Observability and Session 2 APIM AI Gateway). This repo answers
> the five evaluation questions Providence raised during kickoff.

## The use case

Providence Health wants to put generative AI models to work across both
**clinical** (triage bots, drug-interaction lookup, patient-facing Q&A) and
**non-clinical** (billing, HR, scheduling) workflows. Before a model enters
Providence's internal catalog, Governance and Medical Affairs require
evidence that:

1. The model is safe in general (platform approval).
2. The model is appropriate for the specific workflow (use-case approval).
3. Providence-specific policies (HIPAA leakage, citation discipline, refusal
   behavior) are enforced beyond what the Foundry built-ins cover.
4. Failures route through a documented exception process — not ad-hoc email.
5. Agents go through the same governance, not just chat models.

The scripts in this folder implement all of the above end-to-end against
`gpt-4o` and `gpt-4.1-mini`, using only the pre-existing Foundry resources
from Sessions 1 and 2 (zero new infra).

## Repository structure

```
providence-model-evaluation/
├── streamlit_app.py                   # Unified demo UI (9 tabs)
├── datasets/                          # Clinical, non-clinical, adversarial prompts
├── eval-outputs/                      # Pre-computed evaluation results
├── 01‐10_*.py                         # Evaluation scripts (see table below)
├── _config.py / _generate.py          # Shared config + model calling
├── _custom_evaluators.py              # Providence overlay (ClinicalSafety, HIPAA, Citation)
├── .github/workflows/                 # CI/CD - model-evaluation.yml
├── Providence - Model Evaluation.pptx # 40-slide pitch deck
├── walk through.md                    # 60-minute demo script
└── README.md
```

## Streamlit demo app

A Streamlit app (`streamlit_app.py`) visualizes every output in
`eval-outputs/` across 9 tabs — one per Providence ask. Safe to run in front
of an audience because it reads only from on-disk JSON; no live API calls.

```powershell
streamlit run streamlit_app.py
```

## Providence asks → this repo

| # | Providence ask | Files |
|---|---|---|
| A | Clinical vs non-clinical evaluation | `02_usecase_clinical_eval.py`, `03_usecase_nonclinical_eval.py` |
| B | Separate platform approval from use-case evaluation | `01_platform_approval_eval.py` vs `02/03` |
| C | What built-in evaluators are, how they determine efficacy | `04_builtin_evaluators_explained.py` |
| D | Exception process | `09_exception_process.py` |
| E | Guardrails / controls | `08_redteam_adversarial.py` + `_custom_evaluators.py` |

## The two-lens model (the one slide for Monday)

```
          ┌──────────────────────────────────────────────────────┐
          │                PLATFORM APPROVAL (Lens 1)            │
          │   "Can this model be in the Providence catalog?"     │
          │   - Safety floor    - Content safety                 │
          │   - Hallucination   - HIPAA leak scan                │
          │   - Baseline quality (coherence / fluency)           │
          │   -> 01_platform_approval_eval.py                    │
          └──────────────────────────────────────────────────────┘
                                │  approved
                                ▼
          ┌──────────────────────────────────────────────────────┐
          │                USE-CASE EVALUATION (Lens 2)          │
          │   "Is this model appropriate for THIS workload?"     │
          │   Clinical overlay (02)                              │
          │     + ClinicalSafety, MedicalCitation, Groundedness  │
          │   Non-clinical overlay (03)                          │
          │     + Relevance, Similarity, F1                      │
          └──────────────────────────────────────────────────────┘
                                │
                                ▼
          ┌──────────────────────────────────────────────────────┐
          │                 EXCEPTION PROCESS                    │
          │   Aggregates all metrics -> APPROVED / NEEDS_REVIEW  │
          │                            / AUTO_DENIED             │
          │   -> 09_exception_process.py                         │
          └──────────────────────────────────────────────────────┘
```

## Existing Azure resources reused (zero-new-infra, minimum cost)

- Foundry account: `ai-apim-demo-jp-001` (eastus2, S0)
- Foundry project: `proj-apim-demo-jp-001`
- Model deployments:
  - `gpt-4o` @ Standard/30 TPM — **Candidate A & Judge**
  - `gpt-4.1-mini` @ GlobalStandard/10 TPM — **Candidate B** (added for this session)
- App Insights: `appinsights-apim-demo-jp-001` (optional wire-up in `_config.py`)

Nothing else provisioned for this session. Only per-token inference cost on existing deployments.

## How to run

```powershell
# Inside the session folder
py -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.template .env     # fill anything blank
az login                          # DefaultAzureCredential path

python 04_builtin_evaluators_explained.py   # starts here (no cost)
python 01_platform_approval_eval.py         # Lens 1
python 02_usecase_clinical_eval.py          # Lens 2 (clinical)
python 03_usecase_nonclinical_eval.py       # Lens 2 (non-clinical)
python 07_custom_evaluators.py              # Providence overlays
python 08_redteam_adversarial.py            # adversarial + refusal

# PERSISTENT AGENT — STOP after 05 to confirm in Foundry UI
python 05_create_foundry_agent.py
# ...confirm in portal...
python 06_agent_evaluation.py               # agentic metrics

python 09_exception_process.py              # governance decision aggregator

# Optional — launch the demo UI (reads eval-outputs/, no API calls)
streamlit run streamlit_app.py
```

## Datasets

- `datasets/clinical.jsonl`    — 10 clinical triage / drug-safety / peds / MH prompts
- `datasets/nonclinical.jsonl` — 10 admin / billing / scheduling / HR prompts
- `datasets/adversarial.jsonl` — 10 adversarial (jailbreak / PII / injection / misinfo)

## Why persistent Foundry agents (not classic Assistants API)

`05_create_foundry_agent.py` uses `azure-ai-projects` + `azure-ai-agents` (GA v2). These
render in the Foundry UI → **Agents** tab and support server-side tool calls, threads, and
evaluation via `IntentResolution`, `TaskAdherence`, `ToolCallAccuracy`. The legacy path —
`openai.beta.assistants.create(...)` — is explicitly avoided.

## Files

```
datasets/
  clinical.jsonl
  nonclinical.jsonl
  adversarial.jsonl

_config.py                         # env + constants
_generate.py                       # shared model-response generator
_custom_evaluators.py              # ClinicalSafety, HIPAALeak, MedicalCitation

01_platform_approval_eval.py
02_usecase_clinical_eval.py
03_usecase_nonclinical_eval.py
04_builtin_evaluators_explained.py
05_create_foundry_agent.py         # PAUSE for UI verification after running
06_agent_evaluation.py
07_custom_evaluators.py
08_redteam_adversarial.py
09_exception_process.py

streamlit_app.py                   # unified demo UI
Foundry_agentic-creation.md        # classic vs new Agent Service — knowledge doc

.env.template
requirements.txt
README.md
```

## GitHub Actions — CI/CD evaluation

`.github/workflows/model-evaluation.yml` re-runs the harness on every PR,
nightly at 07:00 UTC, and on-demand via `workflow_dispatch`. The
exception-process step is the PR gate: any model scored `AUTO_DENIED` fails
the job and blocks merge.

### One-time setup (for this repo to run CI against Azure)

1. Create an app registration for GitHub OIDC federation:
   ```powershell
   az ad app create --display-name providence-model-eval-gh
   # Note the appId (AZURE_CLIENT_ID) and objectId
   az ad sp create --id <appId>
   az role assignment create --assignee <appId> --role Contributor \
     --scope /subscriptions/<sub-id>/resourceGroups/<rg>
   ```
2. Add a federated credential for `repo:jaypadhya1605/providence-model-evaluation:ref:refs/heads/main`
   (and another for `pull_request` if you want PR runs).
3. Add these as **repo secrets** under Settings → Secrets → Actions:

   | Secret | Source |
   |---|---|
   | `AZURE_CLIENT_ID`            | app registration |
   | `AZURE_TENANT_ID`            | `az account show --query tenantId` |
   | `AZURE_SUBSCRIPTION_ID`      | `az account show --query id` |
   | `AOAI_ENDPOINT`              | Foundry account endpoint |
   | `FOUNDRY_PROJECT_ENDPOINT`   | Foundry project endpoint |
   | `FOUNDRY_ACCOUNT_NAME`       | `ai-apim-demo-jp-001` (or yours) |
   | `FOUNDRY_PROJECT_NAME`       | `proj-apim-demo-jp-001` (or yours) |
   | `AZURE_RESOURCE_GROUP`       | resource group |

4. Trigger a run: **Actions → Model Evaluation (Providence) → Run workflow**.
