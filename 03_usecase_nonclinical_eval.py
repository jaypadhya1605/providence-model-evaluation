"""
03 — USE-CASE EVALUATION: NON-CLINICAL
=======================================
Question this answers:
  "Is the model appropriate for THIS non-clinical use case (billing, scheduling, HR, facility)?"

Non-clinical overlay is lighter than clinical — no medical-safety evaluators,
but still checks relevance, groundedness, and task-adherence style quality.

Inputs : datasets/nonclinical.jsonl
"""
from __future__ import annotations
import json

from azure.ai.evaluation import (
    evaluate,
    RelevanceEvaluator,
    SimilarityEvaluator,
    F1ScoreEvaluator,
    CoherenceEvaluator,
    FluencyEvaluator,
)

from _config import CANDIDATE_MODEL_A, CANDIDATE_MODEL_B, DATA_DIR, OUTPUT_DIR, judge_model_config, banner
from _generate import generate_responses, load_jsonl, SYSTEM_PROMPTS


def run_nonclinical_eval(model: str) -> dict:
    banner(f"Non-clinical use-case evaluation: {model}")
    ds = load_jsonl(DATA_DIR / "nonclinical.jsonl")
    out_jsonl = OUTPUT_DIR / f"usecase-nonclinical-{model.replace('.', '')}.jsonl"
    generate_responses(ds, model, SYSTEM_PROMPTS["nonclinical"], out_jsonl)

    cfg = judge_model_config()
    evaluators = {
        "relevance":   RelevanceEvaluator(model_config=cfg),
        "similarity":  SimilarityEvaluator(model_config=cfg),
        "f1":          F1ScoreEvaluator(),
        "coherence":   CoherenceEvaluator(model_config=cfg),
        "fluency":     FluencyEvaluator(model_config=cfg),
    }
    q = "${data.query}"; r = "${data.response}"; gt = "${data.ground_truth}"; ctx = "${data.context}"
    evaluator_config = {
        "relevance":  {"column_mapping": {"query": q, "response": r, "context": ctx}},
        "similarity": {"column_mapping": {"query": q, "response": r, "ground_truth": gt}},
        "f1":         {"column_mapping": {"response": r, "ground_truth": gt}},
        "coherence":  {"column_mapping": {"query": q, "response": r}},
        "fluency":    {"column_mapping": {"query": q, "response": r}},
    }
    result = evaluate(
        data=str(out_jsonl),
        evaluators=evaluators,
        evaluator_config=evaluator_config,
        output_path=str(OUTPUT_DIR / f"usecase-nonclinical-{model.replace('.', '')}.result.json"),
        evaluation_name=f"UseCase-NonClinical-{model}",
    )
    metrics = dict(result.get("metrics", {})) if isinstance(result, dict) else {}
    print(f"\n  Metrics for {model}:")
    for k, v in metrics.items():
        print(f"    {k:>30}: {v}")
    return {"model": model, "metrics": metrics}


def main() -> None:
    summary = [run_nonclinical_eval(m) for m in [CANDIDATE_MODEL_A, CANDIDATE_MODEL_B]]
    out = OUTPUT_DIR / "usecase-nonclinical-summary.json"
    out.write_text(json.dumps(summary, indent=2))
    banner("USE-CASE NON-CLINICAL SUMMARY")
    if summary:
        keys = list(summary[0]["metrics"].keys())
        print(f"{'metric':<30}" + "".join(f"{row['model']:>14}" for row in summary))
        for k in keys:
            print(f"{k:<30}" + "".join(f"{r['metrics'].get(k, '-'):>14}" for r in summary))


if __name__ == "__main__":
    main()
