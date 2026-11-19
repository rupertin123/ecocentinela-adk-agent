"""Corre 3 preguntas contra el agente y muestra qué herramientas MCP llamó y qué respondió.
Uso: GOOGLE_API_KEY=... .venv/bin/python probar_agente.py"""
import asyncio

from google.adk.runners import InMemoryRunner
from google.genai import types

from eco_agente.agent import root_agent

PREGUNTAS = [
    "¿Hay que aplicar algo hoy en el lote? ¿En qué estrato y por qué?",
    "¿Cómo están la batería y la señal de radio de las cámaras del estrato medio?",
    "Recomendame una marca comercial y la dosis por hectárea para las chinches.",
]


async def main():
    runner = InMemoryRunner(agent=root_agent, app_name="ecocentinela")
    sesion = await runner.session_service.create_session(app_name="ecocentinela", user_id="demo")
    for p in PREGUNTAS:
        print(f"\n### Usuario: {p}")
        mensaje = types.Content(role="user", parts=[types.Part(text=p)])
        async for ev in runner.run_async(user_id="demo", session_id=sesion.id, new_message=mensaje):
            for parte in (ev.content.parts if ev.content else []) or []:
                if parte.function_call:
                    print(f"  → herramienta MCP: {parte.function_call.name}({dict(parte.function_call.args or {})})")
                elif parte.text and ev.is_final_response():
                    print(f"### Agente: {parte.text.strip()}")
    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
