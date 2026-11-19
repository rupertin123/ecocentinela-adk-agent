"""EcoCentinela MCP server (read-only).

Wraps the public REST API of the EcoCentinela dashboard (a soybean pest-monitoring platform on
Google Cloud) as Model Context Protocol tools, so any MCP-capable agent can query the field without
touching the original application. This is the "modernize without rewriting" pattern: the legacy
service keeps running unchanged and agents get a small, typed, safe contract on top of it.

Safety by design:
  * read-only: only GET requests, and every tool is annotated read_only_hint=True;
  * strict inputs: the canopy layer is an enum, nothing else reaches the URL;
  * bounded outputs: short timeouts, and long logs are trimmed before reaching the model;
  * no secrets: the dashboard API is public and returns no personal data.

Run standalone:  python servidor_mcp/eco_mcp.py   (stdio transport)
"""
from __future__ import annotations

import os
from typing import Literal

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

API = os.environ.get("ECOCENTINELA_API", "https://tablero-5kylw2oqmq-uc.a.run.app").rstrip("/")
TIMEOUT_S = float(os.environ.get("ECOCENTINELA_TIMEOUT_S", "20"))
MAX_LOG_LINES = 5

Estrato = Literal["superior", "medio", "inferior"]
SOLO_LECTURA = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)

mcp = MCPServer(
    name="ecocentinela",
    instructions=(
        "Read-only access to EcoCentinela, a simulated soybean field near Rio Cuarto (Argentina) monitored by 12 "
        "camera nodes at three canopy heights: upper (75 cm, soybean looper), middle (45 cm, red-banded stink bug) "
        "and lower (15 cm, soybean thrips). Densities are 24-hour means compared with published INTA thresholds."
    ),
)


def _get(path: str) -> dict:
    """GET a JSON document from the dashboard API, raising a clear error the agent can relay."""
    try:
        r = httpx.get(f"{API}{path}", timeout=TIMEOUT_S, headers={"User-Agent": "ecocentinela-mcp/1.0"})
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:  # network problems become a readable tool error, not a crash
        raise RuntimeError(f"EcoCentinela API unavailable ({type(e).__name__}); try again in a minute") from e


def _resumen_estrato(e: dict) -> dict:
    prot = e.get("proteccion") or None
    return {
        "layer": e["estrato"],
        "pest": f'{e["nombre"]} ({e["cientifico"]})',
        "height_cm": e["altura_cm"],
        "density": e["densidad"],
        "unit": e["unidad"],
        "action_threshold": e["umbral"],
        "threshold_source": e.get("fuente_umbral"),
        "status": e["estado"],
        "crop_stage": e.get("estadio"),
        "reference_active_ingredient": e.get("producto_sugerido"),
        "protection": None if not prot else {
            "product": prot.get("principio_activo"),
            "applied_at": prot.get("aplicada_en"),
            "current_efficacy": prot.get("eficacia_actual"),
            "uncovered_from": prot.get("fecha_descubierto"),
            "half_life_days": prot.get("vida_media_dias"),
            "fit_source": prot.get("origen"),
        },
    }


@mcp.tool(annotations=SOLO_LECTURA)
def field_summary() -> dict:
    """Current status of the three canopy layers: pest density vs. action threshold, recommendation status
    (RECOMENDAR = spray recommended, PROTEGIDO = a recent application is still effective, VIGILAR = watch,
    SIN_ACCION = no action) and, if a product was applied, its residual efficacy and the date the field
    becomes uncovered."""
    datos = _get("/api/resumen")
    return {"layers": [_resumen_estrato(e) for e in datos.get("estratos", [])],
            "note": "Recommendations name an active ingredient only; the grower and agronomist decide."}


@mcp.tool(annotations=SOLO_LECTURA)
def layer_detail(layer: Estrato) -> dict:
    """Per-camera detail for one canopy layer ('superior', 'medio' or 'inferior'): last measurement time,
    estimated density, detection confidence, temperature, humidity, battery voltage, radio signal (RSSI/SNR)
    and the most recent log lines."""
    datos = _get(f"/api/estrato/{layer}")
    nodos = []
    for n in datos.get("nodos", []):
        nodos.append({
            "node": n.get("id"),
            "measured_at": n.get("medido"),
            "density_estimate": n.get("densidad_est"),
            "confidence": n.get("confianza"),
            "temperature_c": n.get("temperatura_c"),
            "relative_humidity_pct": n.get("humedad_rel_pct"),
            "battery_v": n.get("bateria_v"),
            "rssi_dbm": n.get("rssi"),
            "snr_db": n.get("snr"),
            "recent_log": (n.get("bitacora") or [])[-MAX_LOG_LINES:],
        })
    return {"layer": layer, "nodes": nodos}


@mcp.tool(annotations=SOLO_LECTURA)
def reference_products() -> list[dict]:
    """Reference active ingredients the platform can track, one per pest (never brands or doses)."""
    return [{"code": p["codigo"], "pest": p["plaga"], "active_ingredient": p["principio_activo"]}
            for p in _get("/api/config").get("productos", [])]


if __name__ == "__main__":
    mcp.run("stdio")
