"""Prueba de humo del servidor MCP por stdio, como lo usaría cualquier cliente MCP (sin modelo de IA)."""
import asyncio, json, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVIDOR = Path(__file__).resolve().parent.parent / "servidor_mcp" / "eco_mcp.py"

async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVIDOR)])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            for t in tools:
                print("TOOL", t.name, "read_only=", t.annotations.read_only_hint if t.annotations else None)
            res = await s.call_tool("field_summary", {})
            print("field_summary ->", (res.content[0].text if res.content else json.dumps(res.structured_content))[:400])
            res = await s.call_tool("layer_detail", {"layer": "medio"})
            print("layer_detail ->", (res.content[0].text if res.content else "")[:300])
            res = await s.call_tool("layer_detail", {"layer": "../admin"})
            print("entrada inválida -> isError =", res.is_error, (res.content[0].text if res.content else "")[:160])

asyncio.run(main())
