"""
02 — USE-CASE EVALUATION: CLINICAL
===================================
Question this answers:
  "Given the model is catalog-approved, is it appropriate for THIS clinical use case?"

This is Providence's Lens #2 (use-case) for CLINICAL workflows.
Clinical overlay adds:
  * Groundedness (hallucination) - built-in
  * Relevance / Similarity / F1    - built-in
  * ClinicalSafetyEvaluator        - custom (see 07_custom_evaluators.py)
  * MedicalCitationEvaluator       - custom
  * HIPAALeakEvaluator             - custom

Inputs : datasets/clinical.jsonl
Outputs: eval-outputs/usecase-clinical-<model>.*
"""
from __future__ import annotations
import json
from pathlib import Path

from azure.ai.evaluation import (
    evaluate,
    RelevanceEvaluator,
    SimilarityEvaluator,
    F1ScoreEvaluator,
    GroundednessEvaluator,
    CoherenceEvaluator,
)

from _config import CANDIDATE_MODEL_A, CANDIDATE_MODEL_B, DATA_DIR, OUTPUT_DIR, FOUNDRY_PROJECT_ENDPOINT, judge_model_config, banner
from _generate import generate_responses, load_jsonl, SYSTEM_PROMPTS
from _custom_evaluators import ClinicalSafetyEvaluator, HIPAALeakEvaluator, MedicalCitationEvaluator


def run_clinical_eval(model: str) -> dict:
    banner(f"Clinical use-case evaluation: {model}")

    ds = load_jsonl(DATA_DIR / "clinical.jsonl")
    out_jsonl = OUTPUT_DIR / f"usecase-clinical-{model.replace('.', '')}.jsonl"
    generate_responses(ds, model, SYSTEM_PROMPTS["clinical"], out_jsonl)

    cfg = judge_model_config()

    evaluators = {
        "relevance":     RelevanceEvaluator(model_config=cfg),
        "similarity":    SimilarityEvaluator(model_config=cfg),
        "f1":            F1ScoreEvaluator(),
        "groundedness":  GroundednessEvaluator(model_config=cfg),
        "coherence":     CoherenceEvaluator(model_config=cfg),
        # --- Providence overlays (custom) ---
        "clinical_safety":   ClinicalSafetyEvaluator(model_config=cfg),
        "hipaa_leak":        HIPAALeakEvaluator(),
        "medical_citation":  MedicalCitationEvaluator(model_config=cfg),
    }

    q = "${data.query}"
    r = "${data.response}"
    gt = "${data.ground_truth}"
    ctx = "${data.context}"
    evaluator_config = {
        "relevance":    {"column_mapping": {"query": q, "response": r, "context": ctx}},
        "similarity":   {"column_mapping": {"query": q, "response": r, "ground_truth": gt}},
        "f1":           {"column_mapping": {"response": r, "ground_truth": gt}},
        "groundedness": {"column_mapping": {"query": q, "response": r, "context": ctx}},
        "coherence":    {"column_mapping": {"query": q, "response": r}},
        "clinical_safety":  {"column_mapping": {"query": q, "response": r}},
        "hipaa_leak":       {"column_mapping": {"response": r}},
        "medical_citation": {"column_mapping": {"query": q, "response": r}},
    }

    result = evaluate(
        data=str(out_jsonl),
        evaluators=evaluators,
        evaluator_config=evaluator_config,
        output_path=str(OUTPUT_DIR / f"usecase-clinical-{model.replace('.', '')}.result.json"),
        evaluation_name=f"UseCase-Clinical-{model}",
        azure_ai_project=FOUNDRY_PROJECT_ENDPOINT,  # -> visible in Foundry portal 'Evaluation' tab
    )
    metrics = dict(result.get("metrics", {})) if isinstance(result, dict) else {}
    print(f"\n  Metrics for {model}:")
    for k, v in metrics.items():
        print(f"    {k:>40}: {v}")
    return {"model": model, "metrics": metrics}


def main() -> None:
    summary = [run_clinical_eval(m) for m in [CANDIDATE_MODEL_A, CANDIDATE_MODEL_B]]
    out = OUTPUT_DIR / "usecase-clinical-summary.json"
    out.write_text(json.dumps(summary, indent=2))
    banner("USE-CASE CLINICAL SUMMARY — per-model metric means (higher is better)")
    if summary:
        keys = list(summary[0]["metrics"].keys())
        header = f"{'metric':<40}" + "".join(f"{row['model']:>14}" for row in summary)
        print(header)
        for k in keys:
            row = f"{k:<40}" + "".join(f"{r['metrics'].get(k, '-'):>14}" for r in summary)
            print(row)


if __name__ == "__main__":
    main()
