"""
Shared configuration for Providence Session 3 (Model Evaluation).
Reads from .env (or .env.template as fallback) and exposes typed constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR

# Load .env if present, fall back to .env.template for out-of-the-box usability
env_path = ROOT / ".env"
if not env_path.exists():
    env_path = ROOT / ".env.template"
load_dotenv(env_path, override=False)


def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}. Copy .env.template -> .env and fill it.")
    return v


# Azure
SUBSCRIPTION_ID = _req("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP = _req("AZURE_RESOURCE_GROUP")
LOCATION = _req("AZURE_LOCATION")

# Foundry
FOUNDRY_ACCOUNT_NAME = _req("FOUNDRY_ACCOUNT_NAME")
FOUNDRY_PROJECT_NAME = _req("FOUNDRY_PROJECT_NAME")
AOAI_ENDPOINT = _req("AOAI_ENDPOINT")
FOUNDRY_PROJECT_ENDPOINT = _req("FOUNDRY_PROJECT_ENDPOINT")
API_VERSION = os.getenv("API_VERSION", "2025-01-01-preview")

# Models
CANDIDATE_MODEL_A = _req("CANDIDATE_MODEL_A")
CANDIDATE_MODEL_B = _req("CANDIDATE_MODEL_B")
JUDGE_MODEL = _req("JUDGE_MODEL")
AGENT_MODEL = _req("AGENT_MODEL")

# Paths
DATA_DIR = ROOT / "datasets"
OUTPUT_DIR = ROOT / "eval-outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def judge_model_config() -> dict:
    """Returns the model_config dict expected by azure-ai-evaluation evaluators."""
    return {
        "azure_endpoint": AOAI_ENDPOINT,
        "azure_deployment": JUDGE_MODEL,
        "api_version": API_VERSION,
    }


def banner(title: str, width: int = 72) -> None:
    line = "=" * width
    print(f"\n{line}\n  {title}\n{line}")
