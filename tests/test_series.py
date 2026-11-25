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
