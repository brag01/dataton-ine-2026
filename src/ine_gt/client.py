"""Cliente genérico para la API CKAN del INE Guatemala."""
from __future__ import annotations

from typing import Any
import json
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
import pandas as pd

from .catalogo import _catalogo_series, buscar_serie
from .exceptions import INEAPIError


class INEClient:
    """Consulta el catálogo CKAN y sus recursos DataStore. Usa with para cerrar la sesión."""

    def __init__(self, base_url: str = "https://datos.ine.gob.gt/api/3/action", timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ine-gt/2.0.0"})

    def close(self) -> None:
        self.session.close()

    def catalogo(self, tema: str | None = None) -> pd.DataFrame:
        """Lista series locales con su ID, unidad, argumentos y ejemplo para cargar_serie.

        Omite tema para ver todas. Para buscar otros temas en el portal usa buscar_conjuntos.
        """
        fichas = _catalogo_series() if tema is None else buscar_serie(tema)
        return fichas[["id_serie", "nombre", "frecuencia", "unidad", "argumentos", "ejemplo"]]

    def __enter__(self) -> "INEClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def action(self, name: str, params: dict[str, Any] | None = None) -> Any:
        """Devuelve el resultado JSON de la acción CKAN o lanza INEAPIError."""
        try:
            response = self.session.get(
                f"{self.base_url}/{name}", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise INEAPIError(f"No se pudo consultar '{name}': {exc}") from exc
        if not isinstance(payload, dict) or not payload.get("success"):
            error = payload.get("error") if isinstance(payload, dict) else payload
            raise INEAPIError(f"La API rechazó '{name}': {error}")
        if "result" not in payload:
            raise INEAPIError(f"La respuesta de '{name}' carece de 'result'. Revise la respuesta del portal.")
        return payload["result"]

    def buscar_conjuntos(self, texto: str, rows: int = 100) -> pd.DataFrame:
        """Busca conjuntos en el portal. rows fija el tamaño de página. Usa id con recursos()."""
        if rows <= 0:
            raise ValueError("rows debe ser positivo")
        items = []
        offset = 0
        while True:
            result = self.action("package_search", {"q": texto, "rows": rows, "start": offset})
            batch = result.get("results", [])
            items.extend(batch)
            offset += len(batch)
            if not batch or offset >= result.get("count", offset):
                break
        return pd.DataFrame([
            {"id": x.get("id"), "nombre": x.get("name"), "titulo": x.get("title"),
             "notas": x.get("notes"), "num_recursos": len(x.get("resources", []))}
            for x in items
        ])

    def recursos(self, conjunto_id: str) -> pd.DataFrame:
        """Lista los recursos del conjunto. Selecciona datastore_active para consultar con datos()."""
        package = self.action("package_show", {"id": conjunto_id})
        return pd.DataFrame([
            {"id": r.get("id"), "nombre": r.get("name"), "formato": r.get("format"),
             "url": r.get("url"), "datastore_active": r.get("datastore_active", False),
             "ultima_modificacion": r.get("last_modified")}
            for r in package.get("resources", [])
        ])

    def _consultar_campos(self, resource_id: str, filas: int) -> tuple[pd.DataFrame, dict]:
        result = self.action("datastore_search", {"resource_id": resource_id, "limit": filas,
                                                  "include_total": "false"})
        fields = result.get("fields") if isinstance(result, dict) else None
        if not isinstance(fields, list) or any(
            not isinstance(f, dict) or not f.get("id") or not f.get("type") for f in fields
        ):
            raise INEAPIError(f"Esquema incompleto para {resource_id}. Revise que DataStore esté activo.")
        campos = pd.DataFrame([(f["id"], f["type"]) for f in fields], columns=["campo", "tipo"])
        return campos, result

    def campos(self, resource_id: str) -> pd.DataFrame:
        """Devuelve campo y tipo de cada columna de un recurso DataStore activo, sin pedir filas."""
        campos, _ = self._consultar_campos(resource_id, 0)
        return campos

    def vista_previa(self, resource_id: str, filas: int = 3) -> pd.DataFrame:
        """Consulta las variables actuales de un recurso DataStore y hasta 10 filas de ejemplo.

        Devuelve una fila por variable con campo, tipo y ejemplos. Los ejemplos siguen
        el orden de las filas recibidas y conservan los nulos. Un recurso vacío
        conserva sus campos con listas vacías. Cada llamada vuelve a consultar al INE.
        """
        if type(filas) is not int or not 1 <= filas <= 10:
            raise ValueError("Use filas entre 1 y 10. Para ver solo los nombres y tipos, use campos().")
        campos, result = self._consultar_campos(resource_id, filas)
        registros = result.get("records")
        if not isinstance(registros, list) or not all(isinstance(r, dict) for r in registros):
            raise INEAPIError(f"Muestra inválida para {resource_id}. Revise el recurso en DataStore.")
        campos["ejemplos"] = [[r.get(nombre) for r in registros[:filas]] for nombre in campos["campo"]]
        campos.attrs.update(resource_id=resource_id, fecha_consulta_utc=datetime.now(timezone.utc).isoformat())
        return campos

    def datos(self, resource_id: str, limit: int = 1000, max_rows: int | None = None,
              *, filters: dict[str, Any] | None = None) -> pd.DataFrame:
        """Lee filas de DataStore. limit fija la página y max_rows el total de filas.

        filters usa los nombres de columna del recurso. La procedencia queda en attrs["source"].
        """
        if limit <= 0 or (max_rows is not None and max_rows < 0):
            raise ValueError("limit debe ser positivo y max_rows no negativo")
        consultas = []
        records: list[dict[str, Any]] = []
        offset = 0
        while max_rows is None or len(records) < max_rows:
            page_limit = limit if max_rows is None else min(limit, max_rows - len(records))
            params = {
                "resource_id": resource_id, "limit": page_limit, "offset": offset
            }
            if filters:
                params["filters"] = json.dumps(filters)
            consultas.append(f"{self.base_url}/datastore_search?{urlencode(params)}")
            result = self.action("datastore_search", params)
            if not isinstance(result, dict) or not isinstance(result.get("records"), list):
                raise INEAPIError(f"DataStore omitió la lista 'records'. Revise el recurso {resource_id}.")
            batch = result["records"]
            records.extend(batch)
            offset += len(batch)
            if not batch or ("total" in result and offset >= result["total"]):
                break
        frame = pd.DataFrame.from_records(records)
        frame.attrs["source"] = {"portal": self.base_url, "resource_id": resource_id,
                                 "consultas": consultas, "filtros": dict(filters or {}),
                                 "fecha_consulta_utc": datetime.now(timezone.utc).isoformat() if consultas else None}
        return frame
