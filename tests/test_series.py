import warnings

import pytest
import ine_gt as ine


def test_busqueda():
    assert ine.buscar_municipio("coban").codigo.tolist() == [1601]
    assert set(ine.buscar_municipio("San Pedro Sacatepequez").codigo) == {109, 1202}
    assert ine.buscar_serie("IPC").id_serie.item() == "ipc_nacional_mensual"


@pytest.mark.parametrize("edades", [list(range(71)), list(range(70)), [0] + list(range(70))])
def test_poblacion(monkeypatch, edades):
    import json
    def respuesta(self, accion, params):
        filtros = json.loads(params["filters"])
        assert filtros == {"DEPTO": 12, "MUPIO": 1202, "SEXO": 0}
        filas = [dict(filtros, EDAD=i, **{"2026.0": 10}) for i in edades]
        return {"total": len(filas), "records": filas}
    monkeypatch.setattr(ine.INEClient, "action", respuesta)
    if len(set(edades)) != 71:
        with pytest.raises(ValueError, match="edad"):
            ine.cargar_serie("poblacion_municipal_anual", 2026, municipio=1202)
    else:
        tabla = ine.cargar_serie("poblacion_municipal_anual", 2026, municipio=1202)
        assert tabla.valor.item() == 710
        assert ine.mostrar_fuente(tabla).iloc[0]["filtros"]["MUPIO"] == 1202


def test_ipc(monkeypatch):
    import json
    def respuesta(self, accion, params):
        filtros = json.loads(params["filters"])
        assert filtros == {"Año": 2026, "Descripción": "ÍNDICE GENERAL"}
        return {"total": 1, "records": [dict(filtros, Mes="Octubre", República=106.24)]}
    monkeypatch.setattr(ine.INEClient, "action", respuesta)
    assert ine.cargar_serie("ipc_nacional_mensual", 2026).valor.item() == 106.24


@pytest.mark.parametrize("año,mes,valor,aviso", [
    (2026, "Octubre", 106, True),
    (2026, "Octubre", 106.24, False),
    (2026, "Noviembre", 106, False),
    (2025, "Octubre", 106, False),
])
def test_precision_ipc(monkeypatch, año, mes, valor, aviso):
    fila = {"Año": año, "Mes": mes, "Descripción": "ÍNDICE GENERAL", "República": valor}
    monkeypatch.setattr(ine.INEClient, "action", lambda *args: {"records": [fila], "total": 1})
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        tabla = ine.cargar_serie("ipc_nacional_mensual", año)
    assert len(avisos) == int(aviso)
    if aviso:
        assert avisos[0].category is UserWarning
        assert "Se conserva" in str(avisos[0].message)
    assert tabla.valor.item() == valor
    assert "106.24" in ine.mostrar_fuente(tabla).nota.item()


def test_series_sin_observaciones(monkeypatch):
    monkeypatch.setattr(ine.INEClient, "action", lambda *args: {"records": [], "total": 0})
    with pytest.warns(UserWarning, match="Sin observaciones de IPC para 2026"):
        tabla = ine.cargar_serie("ipc_nacional_mensual", 2026)
    assert tabla.empty and list(tabla.columns) == ["periodo", "valor"]
    assert ine.mostrar_fuente(tabla).periodo_solicitado.item() == 2026
    with pytest.raises(ValueError, match="buscar_municipio"):
        ine.cargar_serie("poblacion_municipal_anual", 2026, municipio=1202)


@pytest.mark.parametrize("valor", [None, float("nan"), "inf", "-inf", -1, "sin dato"])
def test_ipc_invalido(monkeypatch, valor):
    fila = {"Año": 2026, "Mes": "Octubre", "Descripción": "ÍNDICE GENERAL", "República": valor}
    monkeypatch.setattr(ine.INEClient, "action", lambda *args: {"records": [fila], "total": 1})
    with pytest.raises(ValueError, match="IPC inválido para 2026-10"):
        ine.cargar_serie("ipc_nacional_mensual", año=2026)


@pytest.mark.parametrize("serie,opciones,columna", [
    ("ipc_nacional_mensual", {}, "República"),
    ("poblacion_municipal_anual", {"municipio": 1202}, "EDAD"),
])
def test_esquema_inesperado(monkeypatch, serie, opciones, columna):
    monkeypatch.setattr(ine.INEClient, "action", lambda *args: {"records": [{"_id": 1}], "total": 1})
    with pytest.raises(ine.INEAPIError) as error:
        ine.cargar_serie(serie, 2026, **opciones)
    assert columna in str(error.value)
    assert ine.buscar_serie(serie).recurso.item() in str(error.value)
