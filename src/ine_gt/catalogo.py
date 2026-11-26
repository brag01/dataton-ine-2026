"""Metadatos locales de las series documentadas del INE."""
import unicodedata

import pandas as pd


_IPC = {
    "id_serie": "ipc_nacional_mensual",
    "nombre": "Índice de Precios al Consumidor (IPC)",
    "frecuencia": "Mensual",
    "cobertura": "Nacional",
    "base": "Año 2024 = 100",
    "unidad": "Puntos de índice",
    "recurso": "4b1c485c-78cb-4a0e-b11e-39306a8647f1",
    "argumentos": "año (obligatorio)",
    "ejemplo": 'ine.cargar_serie("ipc_nacional_mensual", año=2026)',
    "campo_filtro": "Descripción",
    "valor_filtro": "ÍNDICE GENERAL",
    "campo_valor": "República",
    "fuente": "https://datos.ine.gob.gt/api/3/action/datastore_search",
    "nota": "Enero a octubre de 2026: la API devolvió la parte entera "
            "del índice nacional. Octubre: 106 en la API y 106.24 publicado.",
}
_POBLACION = {
    "id_serie": "poblacion_municipal_anual",
    "nombre": "Población municipal estimada y proyectada",
    "frecuencia": "Anual",
    "cobertura": "Municipal",
    "argumentos": "municipio (obligatorio), año y sexo (opcionales)",
    "ejemplo": 'ine.cargar_serie("poblacion_municipal_anual", municipio=1202, año=2026)',
    "periodo": "2015–2030",
    "fecha_referencia": "30 de junio de cada año",
    "unidad": "Personas",
    "recurso": "56b97bc0-5624-408d-a136-3931dd05610a",
    "fuente": _IPC["fuente"],
    "nota": "Población por municipio, sexo y edad. SEXO=0 corresponde a ambos sexos.",
}
_CATALOGO = (_IPC, _POBLACION)


def _normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.casefold())
                   if not unicodedata.combining(c))


def buscar_serie(texto: str) -> pd.DataFrame:
    """Busca términos en el catálogo local. Usa id_serie del resultado para cargar_serie."""
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("Escriba el nombre, sigla o identificador de una serie.")
    return _catalogo_series(texto)


def _catalogo_series(tema: str | None = None) -> pd.DataFrame:
    terminos = _normalizar(tema).split() if tema is not None else []
    coincidencias = []
    for ficha in _CATALOGO:
        descripcion = " ".join(ficha.get(campo, "") for campo in
                               ("id_serie", "nombre", "frecuencia", "cobertura", "base"))
        indice = _normalizar(descripcion)
        if all(termino in indice for termino in terminos):
            coincidencias.append(ficha)
    return pd.DataFrame(coincidencias, columns=[*_IPC, "periodo", "fecha_referencia"])
