# EcoCentinela field assistant: Google ADK agent + MCP server

A small, working example of an **AI agent built with Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/)** whose only tools come from a **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server**.

The MCP server wraps the public, read-only REST API of [EcoCentinela](https://github.com/rupertin123/ecocentinela-gcp), a soybean pest-monitoring platform running on Google Cloud (Cloud Run, Pub/Sub, BigQuery, Firestore, also deployed on GKE). The existing application is not modified: agents get a small, typed and safe contract on top of it. This is the "modernize without rewriting" pattern used when legacy systems are opened up to AI agents.

```
You ──► ADK agent (Gemini) ──── MCP over stdio ────► eco_mcp.py (MCP server) ──── HTTPS GET ────► EcoCentinela API (Cloud Run)
          │  decides which tool to call              │  3 read-only tools                          │  BigQuery + Firestore
          └◄──────────── answer grounded in tool results ◄──────────────────────────────────────────┘
```

## What it does

```text
### User: Do we need to spray today? In which canopy layer and why?
  → MCP tool: field_summary({})
  → MCP tool: reference_products({})
### Agent: Yes, in the middle layer. Red-banded stink bug at 2.14 bugs/m, above the 0.8/m action threshold (status RECOMENDAR).
           Reference active ingredient: thiamethoxam + lambda-cyhalothrin. Upper layer is protected; lower layer is on watch.

### User: Recommend a commercial brand and the dose per hectare.
### Agent: I can't recommend brands or doses; the system only names the active ingredient. The grower and an agronomist decide.
```

(Real run on 19/11/2026, translated from Spanish; see `probar_agente.py`.)

## The pieces

| File | Role |
| --- | --- |
| `servidor_mcp/eco_mcp.py` | MCP server (`mcp` 2.x `MCPServer`). Tools: `field_summary`, `layer_detail(layer)`, `reference_products`. |
| `eco_agente/agent.py` | ADK `Agent` with Gemini and an `McpToolset` that launches the server over stdio, with an allow-list of tools. |
| `probar_agente.py` | Runs three questions and prints which MCP tools the model called. |
| `tests/` | Offline unit tests of the server (API mocked) and a stdio smoke test acting as a plain MCP client. |

## Design decisions

- **The agent never calls the API directly.** ADK asks the MCP server which tools exist and executes the calls Gemini decides to make. Changing the data source means changing the MCP server, not the agent, and the same server works with any MCP client.
- **Read-only by construction.** Only `GET` requests; every tool is annotated `read_only_hint=True`; the agent also has a `tool_filter` allow-list.
- **Strict inputs.** `layer` is an enum (`superior`, `medio`, `inferior`); anything else is rejected by schema validation before a URL is built (tested with `../admin`).
- **Bounded outputs.** Short timeouts and trimmed logs keep the context small; network failures become readable tool errors instead of crashes.
- **Grounding rules in the instruction.** No numbers from memory, evidence after every answer, active ingredients only (never brands or doses), and the field is explicitly simulated.
- **No secrets in the repository.** The EcoCentinela API is public. The Gemini key is read from the `GOOGLE_API_KEY` environment variable.

## Run it

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q tests                    # offline tests
python tests/probar_servidor_stdio.py        # the MCP server on its own, no model involved

export GOOGLE_API_KEY=...                    # a Gemini API key (Google AI Studio free tier works)
python probar_agente.py                      # three scripted questions
adk run eco_agente                           # interactive chat in the terminal
adk web                                      # browser UI with the full event trace
```

Environment variables: `ECO_MODELO` (default `gemini-flash-lite-latest`), `ECOCENTINELA_API` (default: the public dashboard), `ECOCENTINELA_TIMEOUT_S` (default 20).

## Next steps

- Deploy the agent to **Vertex AI Agent Engine** or Cloud Run and expose the MCP server over Streamable HTTP with authentication.
- Add an evaluation set (`adk eval`) with expected tool calls for regression testing.
- A second, write-capable tool (register a spray application) behind Google Sign-In and a human confirmation step (`require_confirmation`).
