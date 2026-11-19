"""Pruebas del servidor MCP sin red: se reemplaza la API de EcoCentinela por respuestas fijas."""
import asyncio
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "servidor_mcp"))
import eco_mcp  # noqa: E402

RESUMEN = {"estratos": [{
    "estrato": "medio", "plaga": "piezodorus", "nombre": "Chinche de la alfalfa", "cientifico": "Piezodorus guildinii",
    "unidad": "chinches/m", "altura_cm": 45, "umbral": 0.8, "fuente_umbral": "INTA", "densidad": 2.14,
    "estado": "RECOMENDAR", "proteccion": None, "producto_sugerido": "tiametoxam + lambdacialotrina", "estadio": "R3"}]}
DETALLE = {"estrato": "medio", "nodos": [{"id": "RC-MED-P1", "bateria_v": 3.75, "rssi": -88,
                                           "bitacora": [f"linea {i}" for i in range(20)]}]}
CONFIG = {"oauth_client_id": "no-debe-salir", "productos": [
    {"codigo": "tiametoxam_lambdacialotrina", "plaga": "piezodorus", "principio_activo": "tiametoxam + lambdacialotrina"}]}


@pytest.fixture
def api(monkeypatch):
    llamadas = []

    def falso_get(url, **kw):
        llamadas.append(url)
        ruta = url.split(eco_mcp.API, 1)[1]
        datos = {"/api/resumen": RESUMEN, "/api/estrato/medio": DETALLE, "/api/config": CONFIG}[ruta]
        return httpx.Response(200, json=datos, request=httpx.Request("GET", url))

    monkeypatch.setattr(eco_mcp.httpx, "get", falso_get)
    return llamadas


def test_resumen_traduce_y_conserva_la_evidencia(api):
    r = eco_mcp.field_summary()
    capa = r["layers"][0]
    assert capa["status"] == "RECOMENDAR" and capa["density"] == 2.14 and capa["action_threshold"] == 0.8
    assert capa["reference_active_ingredient"] == "tiametoxam + lambdacialotrina"
    assert "agronomist" in r["note"]


def test_detalle_recorta_la_bitacora(api):
    r = eco_mcp.layer_detail("medio")
    assert len(r["nodes"][0]["recent_log"]) == eco_mcp.MAX_LOG_LINES
    assert r["nodes"][0]["recent_log"][-1] == "linea 19"


def test_productos_no_filtra_datos_de_configuracion(api):
    r = eco_mcp.reference_products()
    assert r == [{"code": "tiametoxam_lambdacialotrina", "pest": "piezodorus",
                  "active_ingredient": "tiametoxam + lambdacialotrina"}]
    assert "no-debe-salir" not in str(r)


def test_sin_api_da_un_error_legible(monkeypatch):
    def caida(url, **kw):
        raise httpx.ConnectTimeout("timeout")
    monkeypatch.setattr(eco_mcp.httpx, "get", caida)
    with pytest.raises(RuntimeError, match="unavailable"):
        eco_mcp.field_summary()


def test_herramientas_publicadas_son_solo_lectura():
    tools = asyncio.run(eco_mcp.mcp.list_tools())
    assert {t.name for t in tools} == {"field_summary", "layer_detail", "reference_products"}
    assert all(t.annotations.read_only_hint and not t.annotations.destructive_hint for t in tools)


def test_estrato_invalido_rechazado_antes_de_la_red(api):
    with pytest.raises(Exception):
        asyncio.run(eco_mcp.mcp.call_tool("layer_detail", {"layer": "../admin"}))
    assert not any("admin" in u for u in api)
