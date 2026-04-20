"""
10 - EVALUATION MODES (Automated / Manual / Human)
===================================================
Providence asked to show the three evaluation modes side-by-side on the
SAME use case so the audience sees when each applies.

  AUTOMATED  - code-driven, programmatic judge. Scales to 1000s of rows,
               runs in CI/CD. (scripts 01..09 are all automated.)
               This script demonstrates an automated pass over 5 clinical
               prompts using the custom ClinicalSafety + HIPAALeak evaluators.

  MANUAL     - same rubric, but triggered from Foundry portal -> Evaluation
               UI. The data scientist picks a dataset + evaluators + model
               and clicks "Run". Outputs land back in the same project.
               This script generates a ready-to-upload JSONL for that flow
               and prints the portal URL + steps.

  HUMAN      - subject-matter experts (MDs, coders, compliance) score rows
               in a spreadsheet. Their scores are ingested and aggregated
               alongside the automated scores. The winning model must pass
               BOTH automated AND human bars.
               This script writes a review CSV for SMEs, then (if scored)
               aggregates the human scores.

Output files:
  eval-outputs/10-automated.result.json
  eval-outputs/10-manual-upload.jsonl          <- upload this in Foundry UI
  datasets/human-eval-template.csv             <- hand to SMEs
  eval-outputs/10-human-aggregate.json         <- only if SMEs have scored
"""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path
from statistics import mean

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from azure.ai.evaluation import evaluate

from _config import (
    CANDIDATE_MODEL_A,
    DATA_DIR,
    OUTPUT_DIR,
    FOUNDRY_PROJECT_NAME,
    banner,
    judge_model_config,
)
from _custom_evaluators import ClinicalSafetyEvaluator, HIPAALeakEvaluator
from _generate import generate_responses, SYSTEM_PROMPTS


# --------------------------------------------------------------------------
def mode_automated() -> Path:
    banner("MODE 1 - AUTOMATED (programmatic, scales, runs in CI/CD)")
    src = DATA_DIR / "clinical.jsonl"
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines()][:5]
    print(f"  Using 5 clinical prompts from {src.name}")

    runs_path = OUTPUT_DIR / "10-automated-runs.jsonl"
    generate_responses(rows, CANDIDATE_MODEL_A, SYSTEM_PROMPTS["clinical"], runs_path)

    judge = judge_model_config()
    evaluators = {
        "clinical_safety": ClinicalSafetyEvaluator(judge),
        "hipaa_leak":      HIPAALeakEvaluator(),
    }
    result = evaluate(
        data=str(runs_path),
        evaluators=evaluators,
        output_path=str(OUTPUT_DIR / "10-automated.result.json"),
    )
    print(f"  -> {OUTPUT_DIR / '10-automated.result.json'}")
    for m, v in (result.get("metrics") or {}).items():
        if isinstance(v, (int, float)):
            print(f"     {m:50s} {v}")
    return runs_path


# --------------------------------------------------------------------------
def mode_manual(runs_path: Path) -> Path:
    banner("MODE 2 - MANUAL (one-click eval from Foundry portal UI)")
    upload = OUTPUT_DIR / "10-manual-upload.jsonl"
    rows = [json.loads(l) for l in runs_path.read_text(encoding="utf-8").splitlines()]
    # Foundry UI Evaluation expects {query, response, ground_truth?}
    with upload.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({
                "query":        r.get("query", r.get("input", "")),
                "response":     r.get("response", ""),
                "ground_truth": r.get("ground_truth", r.get("expected", "")),
            }) + "\n")
    print(f"  Wrote upload-ready dataset -> {upload}")
    print()
    print("  Provider demo steps (do this LIVE in the portal during the call):")
    print("  1. Browser -> https://ai.azure.com")
    print(f"  2. Select project: {FOUNDRY_PROJECT_NAME}")
    print("  3. Left nav -> 'Evaluation' -> 'Create new evaluation'")
    print("  4. Choose: Evaluate existing dataset")
    print(f"     Upload: {upload.name}")
    print("  5. Pick evaluators: Coherence, Relevance, Groundedness, Content Safety")
    print("  6. Click 'Run' - results stream back into the same project ~2-5 min")
    print()
    print("  Why demo this: non-coders on the governance team can run repeatable")
    print("  evaluations without touching Python. Same metrics, different door.")
    return upload


# --------------------------------------------------------------------------
def mode_human(runs_path: Path) -> Path:
    banner("MODE 3 - HUMAN (SME review in CSV, aggregated back)")
    template = DATA_DIR / "human-eval-template.csv"
    rows = [json.loads(l) for l in runs_path.read_text(encoding="utf-8").splitlines()]

    # Only write a fresh blank template if it doesn't already exist.
    # Otherwise preserve any SME scores already captured.
    if not template.exists():
        with template.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "row_id", "query", "response",
                "sme_clinical_safety_1to5",
                "sme_factual_accuracy_1to5",
                "sme_would_block_y_or_n",
                "sme_notes",
            ])
            for i, r in enumerate(rows, 1):
                w.writerow([
                    i,
                    r.get("query", ""),
                    (r.get("response", "") or "").replace("\r", " ").replace("\n", " "),
                    "", "", "", "",
                ])
        print(f"  Wrote fresh SME review template -> {template}")
    else:
        print(f"  Using existing SME template -> {template}  (preserving scores)")
    print("  Provider demo steps:")
    print("  1. Send this CSV to the clinical-safety reviewers at Providence.")
    print("  2. SMEs score each row (1-5 scale + free-form notes).")
    print("  3. Re-run this script after scoring - aggregates means + disagreement.")
    print()

    # If already scored, aggregate.
    scored_rows = []
    with template.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if (row.get("sme_clinical_safety_1to5") or "").strip():
                try:
                    scored_rows.append({
                        "clinical_safety": int(row["sme_clinical_safety_1to5"]),
                        "factual":         int(row["sme_factual_accuracy_1to5"]),
                        "would_block":     (row["sme_would_block_y_or_n"] or "").lower().startswith("y"),
                    })
                except ValueError:
                    continue
    if scored_rows:
        agg = {
            "n_reviewed":            len(scored_rows),
            "clinical_safety_mean":  round(mean([r["clinical_safety"] for r in scored_rows]), 2),
            "factual_accuracy_mean": round(mean([r["factual"] for r in scored_rows]), 2),
            "would_block_rate":      round(sum(1 for r in scored_rows if r["would_block"]) / len(scored_rows), 2),
        }
        out = OUTPUT_DIR / "10-human-aggregate.json"
        out.write_text(json.dumps(agg, indent=2), encoding="utf-8")
        print(f"  Aggregated {agg['n_reviewed']} SME reviews -> {out}")
        print(json.dumps(agg, indent=2))
    else:
        print("  (no SME rows scored yet; aggregation skipped)")

    return template


# --------------------------------------------------------------------------
def main() -> None:
    banner("Providence - three evaluation modes")
    runs_path = mode_automated()
    mode_manual(runs_path)
    mode_human(runs_path)

    banner("WHY THREE MODES MATTER")
    print("  Automated  = scale + regression (run in CI/CD on every change)")
    print("  Manual     = governance team can run without code")
    print("  Human      = MD/coder/compliance sign-off on the hard cases")
    print()
    print("  A model enters the Providence catalog only after passing all three.")


if __name__ == "__main__":
    main()
