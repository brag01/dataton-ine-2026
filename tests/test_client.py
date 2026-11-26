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
