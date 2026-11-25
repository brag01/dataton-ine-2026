import pytest
from ine_gt import INEClient, INEAPIError


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
