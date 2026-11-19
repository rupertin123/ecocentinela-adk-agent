"""EcoCentinela field assistant: a small Google ADK agent whose only tools come from an MCP server.

The agent never talks to the EcoCentinela API directly. ADK starts the MCP server as a subprocess
(stdio), asks it which tools exist, shows them to Gemini, and executes whatever tool call Gemini
decides to make. Swapping the data source means swapping the MCP server, not the agent.

Run:  adk run eco_agente      (terminal chat)
      adk web                 (browser UI with the event trace)
"""
import os
import sys
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

SERVIDOR = Path(__file__).resolve().parent.parent / "servidor_mcp" / "eco_mcp.py"
MODELO = os.environ.get("ECO_MODELO", "gemini-flash-lite-latest")

herramientas_eco = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(command=sys.executable, args=[str(SERVIDOR)],
                                            env={**os.environ}),
        timeout=30.0,
    ),
    # Allow-list: even if the server grows, this agent only sees these read-only tools.
    tool_filter=["field_summary", "layer_detail", "reference_products"],
)

INSTRUCCION = """You are the field assistant of EcoCentinela, a simulated soybean field near Río Cuarto, Argentina,
monitored by 12 camera nodes at three canopy heights.

Rules:
1. Never state a number, status or date from memory: call the tools first and answer only from what they return.
2. Answer in the user's language, briefly: first the answer, then the evidence (density vs. threshold, source).
3. Recommendations name an ACTIVE INGREDIENT only. Never give brands or doses; the grower and an agronomist decide.
4. Say clearly that the field is simulated when the user asks about real fields or real products.
5. If a tool fails, say the data is unavailable and do not guess.
"""

root_agent = Agent(
    name="ecocentinela_asistente",
    model=MODELO,
    description="Answers questions about pest pressure, spray recommendations and node health in the EcoCentinela field.",
    instruction=INSTRUCCION,
    tools=[herramientas_eco],
)
