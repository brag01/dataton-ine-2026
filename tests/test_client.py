import pytest
from ine_gt import INEClient, INEAPIError


def test_descubrir_series():
    with INEClient() as client:
        catalogo = client.catalogo()
        assert set(catalogo.id_serie) == {"ipc_nacional_mensual", "poblacion_municipal_anual"}
        assert 'año=2026' in client.catalogo("ÍPC").ejemplo.item()
        assert client.catalogo("censo").empty


def test_campos_sin_descargar_filas(monkeypatch):
    def esquema(name, params):
        assert name == "datastore_search" and params["limit"] == 0
        return {"fields": [{"id": "Año", "type": "int4"}], "records": []}
    with INEClient() as client:
        monkeypatch.setattr(client, "action", esquema)
        assert client.campos("recurso").to_dict("records") == [{"campo": "Año", "tipo": "int4"}]
        monkeypatch.setattr(client, "action", lambda *args: {"records": []})
        with pytest.raises(INEAPIError, match="Esquema incompleto"):
            client.campos("recurso")


def test_limit_invalido():
    with INEClient() as client:
        with pytest.raises(ValueError):
            client.datos("abc", limit=0)


def test_vista_previa_refresca_esquema_y_conserva_campos_sin_datos(monkeypatch):
    respuestas = iter([
        {"fields": [{"id": "Edad", "type": "int4"}], "records": [{"Edad": 9}, {"Edad": None}]},
        {"fields": [{"id": "Grupo", "type": "text"}], "records": []},
    ])
    def consultar(name, params):
        assert name == "datastore_search"
        assert params == {"resource_id": "censo", "limit": 2, "include_total": "false"}
        return next(respuestas)
    with INEClient() as cliente:
        monkeypatch.setattr(cliente, "action", consultar)
        primera = cliente.vista_previa("censo", filas=2)
        assert primera.to_dict("records") == [{"campo": "Edad", "tipo": "int4", "ejemplos": [9, None]}]
        segunda = cliente.vista_previa("censo", filas=2)
        assert segunda.to_dict("records") == [{"campo": "Grupo", "tipo": "text", "ejemplos": []}]
        with pytest.raises(ValueError, match="entre 1 y 10"):
            cliente.vista_previa("censo", filas=1000)


def test_respuesta_api_invalida(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {"success": False, "error": {"message": "No existe"}}

    with INEClient() as client:
        monkeypatch.setattr(client.session, "get", lambda *args, **kwargs: FakeResponse())
        with pytest.raises(INEAPIError):
            client.action("package_show", {"id": "no-existe"})


def test_paginacion(monkeypatch):
    pages = {
        0: {"records": [{"valor": 1}, {"valor": 2}], "total": 3},
        2: {"records": [{"valor": 3}], "total": 3},
    }
    with INEClient() as client:
        monkeypatch.setattr(client, "action", lambda name, params: pages[params["offset"]])
        frame = client.datos("recurso", limit=2)
        assert frame["valor"].tolist() == [1, 2, 3]
        assert frame.attrs["source"]["resource_id"] == "recurso"
