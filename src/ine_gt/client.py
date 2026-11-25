"""Cliente genérico para la API CKAN del INE Guatemala."""
from __future__ import annotations

from typing import Any
import json
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
import pandas as pd

from .exceptions import INEAPIError


class INEClient:
    def __init__(self, base_url: str = "https://datos.ine.gob.gt/api/3/action", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ine-gt/2.0.0"})

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "INEClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def action(self, name: str, params: dict[str, Any] | None = None) -> Any:
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
        return payload["result"]

    def buscar_conjuntos(self, texto: str, rows: int = 100) -> pd.DataFrame:
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
        package = self.action("package_show", {"id": conjunto_id})
        return pd.DataFrame([
            {"id": r.get("id"), "nombre": r.get("name"), "formato": r.get("format"),
             "url": r.get("url"), "datastore_active": r.get("datastore_active", False),
             "ultima_modificacion": r.get("last_modified")}
            for r in package.get("resources", [])
        ])

    def datos(self, resource_id: str, limit: int = 1000, max_rows: int | None = None,
              *, filters: dict[str, Any] | None = None) -> pd.DataFrame:
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
            batch = result.get("records", [])
            records.extend(batch)
            offset += len(batch)
            if not batch or ("total" in result and offset >= result["total"]):
                break
        frame = pd.DataFrame.from_records(records)
        frame.attrs["source"] = {"portal": self.base_url, "resource_id": resource_id,
                                 "consultas": consultas, "filtros": dict(filters or {}),
                                 "fecha_consulta_utc": datetime.now(timezone.utc).isoformat() if consultas else None}
        return frame
