"""
06 - AGENTIC EVALUATION (New Foundry Agent Service)
====================================================
Uses the new conversations/responses API against the prompt agent created in 05.
Handles tool-call loops explicitly (classic's create_and_process is gone).

Metrics:
  * IntentResolutionEvaluator
  * TaskAdherenceEvaluator
  * ToolCallAccuracyEvaluator

Run 05_create_foundry_agent.py first.
"""
from __future__ import annotations
import json
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.evaluation import (
    evaluate,
    IntentResolutionEvaluator,
    TaskAdherenceEvaluator,
    ToolCallAccuracyEvaluator,
)

from _config import FOUNDRY_PROJECT_ENDPOINT, DATA_DIR, OUTPUT_DIR, judge_model_config, banner
from _generate import load_jsonl


# ---------------------------------------------------------------- local tool impls
def triage_lookup(symptom: str) -> str:
    table = {
        "chest pain":         {"severity": "emergency", "action": "call 911 immediately"},
        "stroke":             {"severity": "emergency", "action": "call 911 immediately"},
        "fever":              {"severity": "routine",   "action": "schedule same-day visit if >102F for 24h"},
        "headache":           {"severity": "routine",   "action": "OTC analgesic; escalate if sudden severe"},
        "suicidal thoughts":  {"severity": "emergency", "action": "call/text 988; stay with the person"},
        "swollen calf":       {"severity": "urgent",    "action": "evaluate for DVT - urgent care or ER"},
        "peanut allergy":     {"severity": "emergency", "action": "epinephrine auto-injector + 911"},
        "pregnancy no movement": {"severity": "urgent", "action": "L&D evaluation"},
    }
    key = symptom.lower().strip()
    match = next((v for k, v in table.items() if k in key), None)
    if match is None:
        match = {"severity": "unknown", "action": "escalate to human"}
    return json.dumps({"symptom": symptom, **match})


def escalate_to_human(reason: str) -> str:
    return json.dumps({"status": "escalated", "ticket_id": "TR-2026-0001", "reason": reason})


DISPATCH = {
    "triage_lookup": lambda args: triage_lookup(args["symptom"]),
    "escalate_to_human": lambda args: escalate_to_human(args["reason"]),
}


# ------------------------------------------------------------------- agent runner
def load_agent_info() -> dict:
    p = OUTPUT_DIR / "agent.json"
    if not p.exists():
        raise RuntimeError("Run 05_create_foundry_agent.py first.")
    return json.loads(p.read_text())


def run_agent_turn(openai, agent_name: str, user_input: str) -> tuple[str, list[dict]]:
    """Run one user turn, executing any tool calls, return (final_text, tool_calls_captured)."""
    conv = openai.conversations.create(
        items=[{"type": "message", "role": "user", "content": user_input}],
        metadata={"agent": agent_name},
    )
    response = openai.responses.create(
        conversation=conv.id,
        input="",
        extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
    )

    tool_calls_captured: list[dict] = []
    max_loops = 4
    while max_loops > 0:
        pending_outputs = []
        final_text_parts: list[str] = []

        for item in response.output:
            itype = getattr(item, "type", "")
            if itype == "function_call":
                call_id = getattr(item, "call_id", None) or getattr(item, "id", "")
                name = getattr(item, "name", "")
                raw_args = getattr(item, "arguments", "") or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
                tool_calls_captured.append({
                    "type": "tool_call",
                    "tool_call_id": call_id,
                    "name": name,
                    "arguments": args,
                })
                fn = DISPATCH.get(name)
                result = fn(args) if fn else json.dumps({"error": f"no such tool {name}"})
                pending_outputs.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result,
                })
            elif itype == "message":
                for b in getattr(item, "content", []):
                    t = getattr(b, "text", None)
                    if t:
                        final_text_parts.append(t)

        if not pending_outputs:
            return ("\n".join(final_text_parts), tool_calls_captured)

        response = openai.responses.create(
            previous_response_id=response.id,
            input=pending_outputs,
            extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
        )
        max_loops -= 1

    return ("\n".join(final_text_parts), tool_calls_captured)


def run_agent_over_dataset() -> Path:
    info = load_agent_info()
    agent_name = info["agent_name"]

    cred = DefaultAzureCredential()
    project = AIProjectClient(endpoint=FOUNDRY_PROJECT_ENDPOINT, credential=cred)
    openai = project.get_openai_client()

    dataset = load_jsonl(DATA_DIR / "clinical.jsonl")[:5]  # keep demo small

    rows: list[dict] = []
    banner(f"Running agent '{agent_name}' over {len(dataset)} clinical prompts")
    for i, item in enumerate(dataset, 1):
        q = item["question"]
        try:
            text, tool_calls = run_agent_turn(openai, agent_name, q)
            print(f"  [{i:>2}/{len(dataset)}] ok  tool_calls={len(tool_calls)}  resp_chars={len(text)}")
        except Exception as e:
            text = f"[ERROR] {e}"
            tool_calls = []
            print(f"  [{i:>2}/{len(dataset)}] ERR {e}")

        rows.append({
            "id": item["id"],
            "query": q,
            "response": text,
            "tool_calls": tool_calls,
            "tool_definitions": [
                {
                    "name": "triage_lookup",
                    "description": "Look up severity and recommended first step for a symptom.",
                    "parameters": {"type": "object",
                                   "properties": {"symptom": {"type": "string"}},
                                   "required": ["symptom"]},
                },
                {
                    "name": "escalate_to_human",
                    "description": "Route the conversation to a clinician.",
                    "parameters": {"type": "object",
                                   "properties": {"reason": {"type": "string"}},
                                   "required": ["reason"]},
                },
            ],
            "ground_truth": item.get("ground_truth", ""),
        })

    out = OUTPUT_DIR / "agent-runs.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"  -> saved {out.name}")
    return out


def main() -> None:
    runs_file = run_agent_over_dataset()

    cfg = judge_model_config()
    evaluators = {
        "intent_resolution":  IntentResolutionEvaluator(model_config=cfg),
        "task_adherence":     TaskAdherenceEvaluator(model_config=cfg),
        "tool_call_accuracy": ToolCallAccuracyEvaluator(model_config=cfg),
    }
    q = "${data.query}"; r = "${data.response}"
    evaluator_config = {
        "intent_resolution":  {"column_mapping": {"query": q, "response": r}},
        "task_adherence":     {"column_mapping": {"query": q, "response": r, "tool_calls": "${data.tool_calls}"}},
        "tool_call_accuracy": {"column_mapping": {"query": q, "tool_calls": "${data.tool_calls}", "tool_definitions": "${data.tool_definitions}"}},
    }

    banner("Agent evaluation (Intent / TaskAdherence / ToolCallAccuracy)")
    result = evaluate(
        data=str(runs_file),
        evaluators=evaluators,
        evaluator_config=evaluator_config,
        output_path=str(OUTPUT_DIR / "agent-eval.result.json"),
        evaluation_name="AgentEval-ProvidenceClinicalTriage",
        azure_ai_project=FOUNDRY_PROJECT_ENDPOINT,  # -> visible in Foundry portal 'Evaluation' tab
    )
    metrics = dict(result.get("metrics", {})) if isinstance(result, dict) else {}
    for k, v in metrics.items():
        print(f"  {k:<40}: {v}")


if __name__ == "__main__":
    main()
