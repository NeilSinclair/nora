---
name: agent-creator
description: Design and scaffold LLM pipeline agents — multi-stage chains where each stage uses a language model to route, classify, extract, or act. Use this skill when the user wants to build an AI pipeline, agent workflow, or any system with stages like router → intent parser → handler, classifier → extractor → responder, or similar LLM-chained architectures. Produces Python code with system prompts embedded inline. Trigger whenever the user describes a pipeline, chain-of-thought workflow, multi-step AI system, or wants to wire together multiple LLM calls with structured outputs.
---

# Agent Creator

A design and scaffolding skill for LLM pipeline agents. The user describes what they want their pipeline to do; you design the stages and generate scaffolded Python code with system prompts embedded inline.

## What this skill produces

- A clear pipeline design (stages, models, structured output schemas, flow of data)
- Python scaffolding for each stage with system prompts written directly in the code
- Wiring code that connects stages end-to-end
- A brief explanation of why each design decision was made

## Phase 1: Capture Intent

Start by understanding what the pipeline needs to accomplish. Extract answers from the conversation if already provided; otherwise ask. Keep this conversational — don't fire all questions at once.

Key things to understand:

1. **What is the pipeline's job?** What comes in (user message, document, event, etc.) and what should come out (action taken, structured data, response sent)?
2. **What are the natural decision points?** Where does the flow branch based on meaning or intent — not just data type? Each branch point is likely a pipeline stage.
3. **What actions does it ultimately take?** (Write to DB, call an API, generate a reply, trigger a webhook, etc.)
4. **What context carries across stages?** (Conversation history, user state, session data)
5. **Any constraints?** (Specific LLM provider, latency requirements, structured output format, existing code to integrate with)

You don't need all of this upfront — start coding once you have enough to make the core stages clear. The user can fill in gaps as you go.

## Phase 2: Design the Pipeline

Map out the stages before writing code. Present the design to the user as a simple diagram and confirm before scaffolding:

```
Input → [Stage 1: Router] → [Stage 2: Intent Parser] → [Stage 3: Handler] → Output
              ↓ route                ↓ intent + params           ↓ result
```

For each stage decide:
- **Role**: What question does this stage answer? (Which domain? What does the user want? What data is needed?)
- **Model**: Which LLM, and at what capability level? Fast/cheap models (e.g. gpt-4o-mini, gpt-5-nano) work well for classification and extraction. More capable models (e.g. gpt-4o, claude-sonnet) for generation and synthesis.
- **Output type**: Structured output (use when the next stage needs to parse the result programmatically) vs. free-form text (use for final user-facing responses).
- **Structured schema**: If structured, what fields? What are the types and constraints?

### Common pipeline patterns

Use these as starting points, not prescriptions:

**Router → Intent Parser → Handler**
Good for: conversational assistants, command processors, chatbots with multiple capabilities.
- Router classifies broad domain (calendar / notes / chat)
- Intent parser extracts fine-grained action + parameters (add / edit / delete + entity details)
- Handler executes and returns result

**Classifier → Extractor → Synthesiser**
Good for: document processing, data pipelines, structured data extraction.
- Classifier determines document type or category
- Extractor pulls structured fields from content
- Synthesiser formats or interprets the extracted data for the end consumer

**Planner → Executor → Reviewer**
Good for: agentic tasks, code generation, multi-step reasoning.
- Planner breaks the goal into steps
- Executor carries out each step (may loop)
- Reviewer checks quality and decides whether to retry or accept

**Single-stage with rich structured output**
Good for: focused tasks that don't need branching — e.g. a single extraction call that returns everything downstream needs.

## Phase 3: Scaffold the Code

Generate Python. Structure it as one file per stage plus a pipeline runner that wires them together, unless the pipeline is very small (then one file is fine).

### File layout

```
<pipeline_name>/
├── pipeline.py          # Top-level runner: accepts input, calls stages in order, returns output
├── stages/
│   ├── router.py        # One file per stage
│   ├── intent_parser.py
│   └── handler.py
└── models.py            # Pydantic models for all structured outputs
```

For a small pipeline (2–3 stages), collapse everything into `pipeline.py`.

### Code style

- Use the OpenAI Responses API by default (not Chat Completions). If the user specifies a different provider, adapt accordingly.
- Define structured outputs as Pydantic models in `models.py`. Pass them to the API via `text={"format": {"type": "json_schema", "json_schema": ...}}` or the SDK's structured output helper.
- Put config (model names, temperature, etc.) at the top of each file as module-level constants — not hardcoded inline.
- System prompts go directly in the code as multi-line strings assigned to a named constant (e.g. `ROUTER_SYSTEM_PROMPT = """..."""`). Do not load them from external files.
- Keep functions focused: one function per stage, with clear input/output types.

### System prompt writing guide

System prompts are the most important part of each stage. Write them to be:

**Specific about the stage's job.** Tell the model exactly what decision it's making, not just what it is. Instead of "You are a router", write "Your job is to read the user's message and decide which domain it belongs to. You must choose exactly one of: calendar, notes, reminders, shopping_lists, chat, help."

**Explicit about the output contract.** If the stage returns structured output, describe each field and what values are valid. The model should never have to guess.

**Contextually aware.** If conversation history or prior stage outputs are passed in, tell the model what they are and how to use them. E.g. "The conversation history is provided so you can resolve references like 'the one I mentioned earlier' or 'yes, that one'."

**Concise.** Every sentence should earn its place. Remove anything that doesn't change behaviour.

Example system prompt pattern:
```python
ROUTER_SYSTEM_PROMPT = """
You classify user messages into one of the following routes: {routes}.

Rules:
- Choose the single best-fitting route based on the user's primary intent.
- If the message could fit multiple routes, prefer the more specific one.
- Use 'chat' only when no other route applies.

Output a JSON object with:
  route (string): one of {routes}
  date_from (string | null): ISO date if the user mentions a start date, otherwise null
  date_to (string | null): ISO date if the user mentions an end date, otherwise null
  extra_context (string | null): any additional context useful for downstream stages
"""
```

### Wiring the stages

The pipeline runner in `pipeline.py` should:
1. Accept the raw input (user message, document, etc.) and any shared context
2. Call each stage in order, passing the output of one as input to the next
3. Return the final output

Keep the runner thin — it orchestrates, it doesn't contain logic.

```python
def run_pipeline(user_message: str, history: list[dict]) -> str:
    route_result = route(user_message, history)
    intent_result = parse_intent(route_result, user_message, history)
    return handle(intent_result, user_message, history)
```

## Phase 4: Present and Explain

After generating the code:

1. Walk the user through the pipeline at a high level — what each stage does, why the model choice was made, what the system prompts are doing.
2. Call out any design decisions that had meaningful tradeoffs (e.g. "I used a separate router stage rather than combining it with intent parsing because the routing decision is cheap and it keeps each stage's system prompt focused").
3. Ask if anything needs adjusting before they start integrating.

## Design principles to apply throughout

**Each stage should do one thing.** If a stage's system prompt has two distinct jobs (classify AND extract), consider splitting it. Focused prompts produce more reliable outputs.

**Prefer structured outputs between stages.** Free-form text is for human consumption. Machine-to-machine handoffs should use typed, validated schemas.

**Name things for what they decide, not what they are.** `route()` not `llm_call_1()`. `ROUTER_SYSTEM_PROMPT` not `SYSTEM_PROMPT`.

**Make the data flow obvious.** A reader should be able to trace what fields flow from stage to stage without running the code.

**Don't over-engineer.** A two-stage pipeline doesn't need a plugin architecture. Scaffold the minimum that makes the pipeline work and is easy to extend later.
