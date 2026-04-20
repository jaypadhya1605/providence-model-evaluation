"""
05 - CREATE FOUNDRY PROMPT AGENT (New Foundry Agents Service)
==============================================================
Uses the NEW Foundry Agent Service API (GA, azure-ai-projects >= 2.0).

  * NOT the classic Assistants API (no `asst_*` id, no `client.beta.assistants`).
  * NOT the classic `azure-ai-agents` AgentsClient (that still uses Assistants
    under the hood and shows up in Foundry UI as "legacy Assistants").

Instead we call:
    project.agents.create_version(
        agent_name="...",
        definition=PromptAgentDefinition(model=..., instructions=..., tools=[...]),
    )

This produces an `agent.version` object ("my-agent:1") that appears in the
Foundry portal under  Build -> Agents  as a first-class new-Foundry agent.

Conversations + responses use the OpenAI Responses API obtained via
    openai = project.get_openai_client()

Reference:
  https://learn.microsoft.com/azure/foundry/agents/how-to/migrate
"""
from __future__ import annotations
import json
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool

from _config import FOUNDRY_PROJECT_ENDPOINT, AGENT_MODEL, OUTPUT_DIR, banner

AGENT_NAME = "providence-clinical-triage"
AGENT_INSTRUCTIONS = """
You are the Providence Clinical Triage Assistant.

You help patients and staff with preliminary clinical triage and routing. You have
access to two tools:
  * triage_lookup(symptom)    - look up severity and initial guidance
  * escalate_to_human(reason) - route the conversation to a clinician

RULES
-----
1. NEVER provide a specific diagnosis or prescribe medication.
2. ALWAYS advise consulting a licensed healthcare provider.
3. For life-threatening symptoms (chest pain, stroke signs, anaphylaxis,
   suicidal ideation) - call 911 / 988 AND call escalate_to_human().
4. Do not repeat, request, or acknowledge any PHI/PII.
5. Cite CDC/WHO/NIH when providing general medical information.
6. If asked anything outside the triage/routing scope, politely decline and
   route to appropriate staff.
""".strip()


TRIAGE_LOOKUP_TOOL = FunctionTool(
    name="triage_lookup",
    description="Look up severity and recommended first step for a given symptom.",
    parameters={
        "type": "object",
        "properties": {
            "symptom": {"type": "string", "description": "Plain-English symptom description."},
        },
        "required": ["symptom"],
        "additionalProperties": False,
    },
    strict=True,
)
ESCALATE_TOOL = FunctionTool(
    name="escalate_to_human",
    description="Route the conversation to a human clinician.",
    parameters={
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Reason for escalation."},
        },
        "required": ["reason"],
        "additionalProperties": False,
    },
    strict=True,
)


def main() -> None:
    banner("Creating NEW Foundry prompt agent (azure-ai-projects >= 2.0)")
    cred = DefaultAzureCredential()
    project = AIProjectClient(endpoint=FOUNDRY_PROJECT_ENDPOINT, credential=cred)

    definition = PromptAgentDefinition(
        model=AGENT_MODEL,
        instructions=AGENT_INSTRUCTIONS,
        tools=[TRIAGE_LOOKUP_TOOL, ESCALATE_TOOL],
    )
    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=definition,
    )
    print(f"  Agent name    : {agent.name}")
    print(f"  Agent id      : {agent.id}")
    print(f"  Agent version : {getattr(agent, 'version', 'n/a')}")
    print(f"  Model         : {agent.definition.model}")

    openai = project.get_openai_client()
    banner("Smoke-test via Responses API")

    conv = openai.conversations.create(
        items=[{
            "type": "message",
            "role": "user",
            "content": "I have crushing chest pain and shortness of breath. What should I do?",
        }],
        metadata={"agent": agent.name},
    )
    print(f"  Conversation id: {conv.id}")

    response = openai.responses.create(
        conversation=conv.id,
        input="",
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(f"  Response status: {response.status}")

    def _safe(s: str) -> str:
        return (s or "").encode("ascii", "replace").decode("ascii")

    for item in response.output:
        itype = getattr(item, "type", "")
        if itype == "function_call":
            print(f"  [tool_call] {item.name}({_safe(item.arguments)})")
        elif itype == "message":
            for b in item.content:
                txt = getattr(b, "text", None)
                if txt:
                    print(f"  Assistant: {_safe(txt)[:220]}...")

    info = {
        "agent_name":     agent.name,
        "agent_id":       agent.id,
        "agent_version":  getattr(agent, "version", None),
        "model":          agent.definition.model,
        "conversation_id": conv.id,
    }
    (OUTPUT_DIR / "agent.json").write_text(json.dumps(info, indent=2))
    print(f"\n  -> saved eval-outputs/agent.json")

    banner("NEXT STEP - VERIFY IN FOUNDRY PORTAL")
    print("  1) Open https://ai.azure.com -> project proj-apim-demo-jp-001")
    print("  2) Left nav -> Agents")
    print("  3) Confirm 'providence-clinical-triage' appears AS A NEW AGENT")
    print("     (NOT in the 'legacy Assistants' pane)")
    print("  4) Open it -> confirm tools 'triage_lookup' and 'escalate_to_human'")
    print("  Only AFTER visual confirmation, proceed to 06_agent_evaluation.py")


if __name__ == "__main__":
    main()
