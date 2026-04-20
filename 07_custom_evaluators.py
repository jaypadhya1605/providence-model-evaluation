"""
07 — CUSTOM EVALUATORS: RUNNER
==============================
Thin runner that shows each custom evaluator end-to-end on a small slice of
the clinical dataset. The evaluators themselves live in `_custom_evaluators.py`
so 02_usecase_clinical_eval.py can import them.
"""
from __future__ import annotations

from azure.ai.evaluation import evaluate

from _config import CANDIDATE_MODEL_A, DATA_DIR, OUTPUT_DIR, FOUNDRY_PROJECT_ENDPOINT, judge_model_config, banner
from _custom_evaluators import ClinicalSafetyEvaluator, HIPAALeakEvaluator, MedicalCitationEvaluator
from _generate import generate_responses, load_jsonl, SYSTEM_PROMPTS


def main() -> None:
    banner(f"Custom evaluators run against {CANDIDATE_MODEL_A} on clinical dataset")
    ds = load_jsonl(DATA_DIR / "clinical.jsonl")
    out = OUTPUT_DIR / f"custom-eval-input-{CANDIDATE_MODEL_A.replace('.', '')}.jsonl"
    generate_responses(ds, CANDIDATE_MODEL_A, SYSTEM_PROMPTS["clinical"], out)

    cfg = judge_model_config()
    result = evaluate(
        data=str(out),
        evaluators={
            "clinical_safety":  ClinicalSafetyEvaluator(cfg),
            "hipaa_leak":       HIPAALeakEvaluator(),
            "medical_citation": MedicalCitationEvaluator(cfg),
        },
        evaluator_config={
            "clinical_safety":  {"column_mapping": {"query": "${data.query}", "response": "${data.response}"}},
            "hipaa_leak":       {"column_mapping": {"response": "${data.response}"}},
            "medical_citation": {"column_mapping": {"query": "${data.query}", "response": "${data.response}"}},
        },
        output_path=str(OUTPUT_DIR / "custom-eval.result.json"),
        evaluation_name="CustomEvaluators-Providence",
        azure_ai_project=FOUNDRY_PROJECT_ENDPOINT,  # -> visible in Foundry portal 'Evaluation' tab
    )
    metrics = dict(result.get("metrics", {})) if isinstance(result, dict) else {}
    banner("Custom evaluator metrics (means over dataset)")
    for k, v in metrics.items():
        print(f"  {k:<40}: {v}")


if __name__ == "__main__":
    main()
