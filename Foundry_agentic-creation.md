# Foundry Agent Creation — Classic vs New

> Personal reference notes. Date: April 2026. Written after hitting the
> "Assistants are not yet supported" warning in the new Foundry UI when we
> thought we had created a modern agent.

## TL;DR

There are **three different ways** to "create a Foundry agent" in Python, and
only one of them produces a first-class agent in the new Foundry experience.
Two of them look modern but secretly create **classic Assistants**.

| Layer | Python import | ID shape | Foundry UI | Status |
|---|---|---|---|---|
| Classic Assistants API (OpenAI) | `openai.beta.assistants.create(...)` | `asst_*` | Legacy pane | Deprecated |
| Classic `azure-ai-agents` AgentsClient | `from azure.ai.agents import AgentsClient` → `agents.create_agent(...)` | `asst_*` | **"Legacy Assistants / Update existing agents"** | Deprecated (retires **March 31, 2027**) |
| **NEW Foundry Agent Service** ✅ | `from azure.ai.projects import AIProjectClient` → `project.agents.create_version(agent_name=..., definition=PromptAgentDefinition(...))` | `name:version` e.g. `providence-clinical-triage:1` | First-class **Agents** list | GA |

The trap: `azure-ai-agents` _looks_ modern (it has `threads`, `messages`,
`runs`), but it's a wrapper over the old Assistants API. The server returns
`asst_*` IDs and the UI labels them as legacy.

---

## The three quick tells

Use these to answer "am I on the new API or the classic one?" in seconds:

1. **Package name & version** — new path requires `azure-ai-projects >= 2.0`.
   `2.0.x` is the cutover release. Any earlier version of the same package, or
   the `azure-ai-agents` package, is **classic**.
2. **Method name**
   * `create_version(...)` + `PromptAgentDefinition` → **new**
   * `create_agent(...)` or `beta.assistants.create(...)` → **classic**
3. **ID shape**
   * `asst_<hash>` → classic
   * `<name>:<version>` → new

Also:

| Classic | New |
|---|---|
| Threads | Conversations |
| Runs | Responses |
| `client.agents.*` (AgentsClient) | `project.agents.*` + `project.get_openai_client()` |
| Assistants API primitives | Responses API primitives |

---

## Side-by-side code

### Classic (avoid for new work)

```python
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet, MessageRole

agents = AgentsClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
agent = agents.create_agent(
    model="gpt-4o",
    name="my-agent",
    instructions="...",
    tools=[...],
)
# agent.id == "asst_CUfYFPhHSVhgtVn73FFZUyS4"   <-- legacy

thread = agents.threads.create()
agents.messages.create(thread_id=thread.id, role="user", content="hi")
run = agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
```

### New Foundry Agent Service (use this)

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool

project = AIProjectClient(
    endpoint="https://<resource>.services.ai.azure.com/api/projects/<project>",
    credential=DefaultAzureCredential(),
)

tool = FunctionTool(
    name="triage_lookup",
    description="Look up severity and recommended first step.",
    parameters={
        "type": "object",
        "properties": {"symptom": {"type": "string"}},
        "required": ["symptom"],
        "additionalProperties": False,
    },
    strict=True,
)

agent = project.agents.create_version(
    agent_name="providence-clinical-triage",
    definition=PromptAgentDefinition(
        model="gpt-4o",
        instructions="...",
        tools=[tool],
    ),
)
# agent.id == "providence-clinical-triage:1"    <-- new Foundry

# Conversations + Responses API (not threads/runs):
openai = project.get_openai_client()

conv = openai.conversations.create(
    items=[{"type": "message", "role": "user", "content": "crushing chest pain"}],
    metadata={"agent": agent.name},
)

response = openai.responses.create(
    conversation=conv.id,
    input="",
    extra_body={
        "agent_reference": {"name": agent.name, "type": "agent_reference"}
    },
)

for item in response.output:
    if item.type == "function_call":
        print("tool_call:", item.name, item.arguments)
    elif item.type == "message":
        for b in item.content:
            print("assistant:", b.text)
```

### Tool-call loop on the new API

Unlike the classic `create_and_process` helper, the new API returns tool calls
and **you** execute them, then submit the outputs with another `responses.create`
referencing `previous_response_id`.

```python
# after the first responses.create(...)
tool_outputs = []
for item in response.output:
    if item.type == "function_call":
        result = dispatch(item.name, item.arguments)   # your local python
        tool_outputs.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": result,
        })

if tool_outputs:
    response = openai.responses.create(
        previous_response_id=response.id,
        input=tool_outputs,
        conversation=conv.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
```

---

## Primitive mapping

| Concept | Classic | New |
|---|---|---|
| Agent definition | `Assistant` object | `PromptAgentDefinition` |
| Agent invocation target | `asst_*` | `agent_reference` by name |
| Conversation state | `Thread` | `Conversation` |
| Single turn | `Run` | `Response` |
| Context across calls | manual (thread id) | automatic via `conversation` |
| Streaming primitive | thread events | Responses streaming |
| Observability anchor | `thread_id + run_id` | `conversation_id + response_id` |

## Versioning

The new API auto-snapshots **every change** as a version:

```
providence-clinical-triage:1   # initial create_version
providence-clinical-triage:2   # next create_version (same agent_name)
```

You can:
- list versions
- pin a `responses.create` call to a specific version
- roll back by creating a new version from an old definition

Classic Assistants had no first-class versioning — you mutated in place.

## Tool availability differences

New-only tools:
- Image generation
- Web search (GA)
- A2A (agent-to-agent, preview)

Classic-only (no direct replacement yet):
- Azure Functions tool
- Connected Agents → use **workflows + A2A** instead
- Deep Research → use **deep-research model + Web Search tool**

Cross-compatible: Code Interpreter, File Search, Function, Bing Grounding,
OpenAPI, MCP, SharePoint Grounding, Fabric Data Agent, Azure AI Search.

## What the Foundry UI does with each

- New agents appear in **Build → Agents → Agents** tab.
- Classic assistants appear behind the banner
  **"Update your agents — Assistants are not yet supported"** with an
  **Update existing agents** button. That's the migration UI; it's not a
  first-class list.

## Common pitfalls

| Symptom | Root cause | Fix |
|---|---|---|
| `AttributeError: 'AIProjectClient' has no attribute 'conversations'` | Called `project.conversations.create` | Call `project.get_openai_client().conversations.create(...)` |
| `create_agent() removed` | Using `azure-ai-projects >= 2.0` with old code | Switch to `create_version` + `PromptAgentDefinition` |
| Agent shows under "legacy Assistants" in UI | Created via `AgentsClient.create_agent` or `openai.beta.assistants.create` | Recreate with `project.agents.create_version` |
| `responses.create` model error | Model name typo or not deployed in this region | Verify with `az cognitiveservices account deployment list ...` |
| Old thread data missing after migration | Migration tool does not move state | Start fresh conversations; old data stays readable via the classic endpoint until deprecation |

## Prerequisites

```bash
pip install "azure-ai-projects>=2.0.0" "openai>=2.4.0" "azure-identity"
az login     # or DefaultAzureCredential with managed identity
```

Environment needs a **Foundry project endpoint** of the form:

```
https://<resource>.services.ai.azure.com/api/projects/<project-name>
```

Get it with:

```powershell
az cognitiveservices account show `
  --name <foundry-account> `
  --resource-group <rg> `
  --query "properties.endpoints['AI Foundry API']" -o tsv
```

Then append `/api/projects/<project-name>`.

## RBAC

The identity creating or invoking the agent needs:
- `Azure AI User` role at the **project** scope (for day-to-day use)
- `Azure AI Account Owner` or `Contributor` at subscription scope (for one-time
  project creation)

If you see a permissions error but the agent exists, it's almost always
`Azure AI User` missing at project scope.

## How the Foundry Agent Service fits together

```
  AIProjectClient  (azure-ai-projects >= 2.0)
     |
     +-- project.agents             <-- agent definitions + versions (new API)
     |       create_version(...)
     |       list_versions(...)
     |       delete_version(...)
     |
     +-- project.get_openai_client()
             conversations.create/items.create
             responses.create        <-- run the agent, handle tool calls
```

Agent lives on `project.agents`. The actual runtime traffic (chat, tool calls,
streaming) goes through the Responses API on the OpenAI client. That split is
intentional: the **definition/versioning plane** is separate from the
**runtime plane**.

## Reference links

- Migration guide (official, the source of truth):
  <https://learn.microsoft.com/azure/foundry/agents/how-to/migrate>
- New Agent Service overview:
  <https://learn.microsoft.com/azure/foundry/agents/overview>
- Hosted-agent quickstart (code-as-agent, container-deployed):
  <https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-hosted-agent>
- Responses API docs:
  <https://platform.openai.com/docs/api-reference/responses>
- Migration tool (auto-converts classic → new code):
  <https://aka.ms/agent/migrate/tool>

## One-line heuristic to remember forever

> **If the ID starts with `asst_`, it's the old thing.
> If it looks like `name:version`, it's the new thing.**

Everything else (package name, method name, primitives) follows from that.
