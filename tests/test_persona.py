"""First persona: an analyst needs one citable municipal population figure offline."""

import json
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import ine_gt as ine


def verificar_cita(fuente, codigo):
    assert fuente.unidad == "Personas"
    url = urlsplit(fuente.consulta)
    assert (url.scheme, url.netloc, url.path) == (
        "https", "datos.ine.gob.gt", "/api/3/action/datastore_search"
    )
    params = parse_qs(url.query)
    assert params["resource_id"] == [fuente.recurso]
    assert json.loads(params["filters"][0]) == fuente.filtros == {
        "DEPTO": codigo // 100, "MUPIO": codigo, "SEXO": 0
    }
    assert datetime.fromisoformat(fuente.fecha_consulta_utc).utcoffset() == timedelta(0)


def test_analyst_disambiguates_municipality_and_cites_number(monkeypatch):
    # The same name occurs in two departments. The analyst chooses San Marcos.
    options = ine.buscar_municipio("San Pedro Sacatepequez")
    assert set(options.departamento) == {"Guatemala", "San Marcos"}
    code = int(options.loc[options.departamento == "San Marcos", "codigo"].item())

    def ckan_reply(self, action, params):
        assert action == "datastore_search"
        assert json.loads(params["filters"]) == {"DEPTO": 12, "MUPIO": 1202, "SEXO": 0}
        records = [
            {"DEPTO": 12, "MUPIO": 1202, "SEXO": 0, "EDAD": age, "2026.0": 10}
            for age in range(71)
        ]
        return {"total": 71, "records": records}

    monkeypatch.setattr(ine.INEClient, "action", ckan_reply)
    series_id = ine.buscar_serie("población municipal").id_serie.item()
    table = ine.cargar_serie(series_id, año=2026, municipio=code)
    source = ine.mostrar_fuente(table)

    assert table[["periodo", "valor"]].iloc[0].tolist() == [2026, 710]
    verificar_cita(source.iloc[0], code)
