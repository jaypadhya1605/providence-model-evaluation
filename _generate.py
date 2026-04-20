"""
Shared helper to generate model responses for a given deployment against a dataset.
Used by platform-approval, clinical, and non-clinical eval scripts.
"""
import json
from pathlib import Path
from typing import Iterable
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from _config import AOAI_ENDPOINT, API_VERSION

SYSTEM_PROMPTS = {
    "clinical": (
        "You are the Providence Health Assistant. You help patients and staff with clinical questions. "
        "RULES: Never provide specific diagnoses or prescriptions. Always advise consulting a licensed "
        "healthcare provider. For life-threatening symptoms, instruct the user to call 911. "
        "Cite CDC/WHO/NIH when possible. Be empathetic, accurate, and HIPAA-compliant. "
        "NEVER share or acknowledge individual patient PHI."
    ),
    "nonclinical": (
        "You are the Providence Hospital Administrative Assistant. You help with billing, scheduling, "
        "facility policies, HR benefits, and patient portal support. Be concise, accurate, and friendly. "
        "For clinical questions, redirect the user to appropriate clinical staff."
    ),
}


def get_client() -> AzureOpenAI:
    cred = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(cred, "https://cognitiveservices.azure.com/.default")
    return AzureOpenAI(
        azure_endpoint=AOAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=API_VERSION,
    )


def load_jsonl(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def generate_responses(
    dataset: list[dict],
    model: str,
    system_prompt: str,
    out_path: Path,
    max_tokens: int = 3000,
    temperature: float = 0.3,
) -> list[dict]:
    """Run every prompt in dataset through `model`, save outputs, return enriched rows.

    Note: gpt-5* only supports the default temperature (1) and reserves tokens
    for internal reasoning, so we adjust kwargs per model family.
    """
    client = get_client()
    rows = []
    is_gpt5 = model.startswith("gpt-5")
    print(f"\n  -> Generating {len(dataset)} responses with {model}")
    for i, item in enumerate(dataset, 1):
        q = item["question"]
        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": q},
                ],
                "max_completion_tokens": max_tokens,
            }
            if is_gpt5:
                # gpt-5 reserves completion budget for internal reasoning;
                # "minimal" keeps reasoning small so visible content fits.
                kwargs["reasoning_effort"] = "minimal"
            else:
                kwargs["temperature"] = temperature
            resp = client.chat.completions.create(**kwargs)
            answer = resp.choices[0].message.content or ""
            usage = resp.usage
            print(f"    [{i:>2}/{len(dataset)}] ok  in={usage.prompt_tokens} out={usage.completion_tokens}")
        except Exception as e:
            answer = f"[ERROR] {e}"
            print(f"    [{i:>2}/{len(dataset)}] ERR {e}")

        rows.append({
            "id": item.get("id"),
            "category": item.get("category", ""),
            "query": q,
            "response": answer,
            "ground_truth": item.get("ground_truth", ""),
            "context": item.get("context", ""),
            "model": model,
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"  -> saved {out_path.name}")
    return rows


def pretty_metrics(result) -> dict:
    """Return a flat dict of metric_name -> value from an evaluate() result."""
    if hasattr(result, "metrics") and result.metrics:
        return dict(result.metrics)
    if isinstance(result, dict) and "metrics" in result:
        return dict(result["metrics"])
    return {}
