# ine_gt 2.0.0.1

Consulta el IPC nacional mensual y la población municipal anual de Guatemala desde Python. El catálogo de 340 municipios viene incluido. Las cifras se obtienen de la API del INE al ejecutar la consulta.

## Instalación

Descomprime el ZIP. Desde la carpeta que contiene pyproject.toml ejecuta `python -m pip install .` (Python 3.10 o posterior). En Colab, sube el ZIP y ejecuta:

```python
!unzip -qo ine_gt_ver2.0.zip
%pip install ./ine_gt_ver2.0
```

## Consultar una serie documentada

```python
import ine_gt as ine
serie = ine.buscar_serie("población municipal").id_serie.item()
opciones = ine.buscar_municipio("San Pedro Sacatepéquez")
codigo = int(opciones.loc[opciones.departamento == "San Marcos", "codigo"].item())
tabla = ine.cargar_serie(serie, año=2026, municipio=codigo)
print(tabla)
print(ine.mostrar_fuente(tabla).T.to_string())
ipc = ine.cargar_serie("ipc_nacional_mensual", año=2026)
print(ipc)
```

Población al 30 de junio. Omite el año para recuperar 2015–2030. Sexo 0 corresponde a ambos sexos, 1 a hombres y 2 a mujeres. Se suman las 71 categorías de edad de un único sexo. La consulta histórica de San Marcos (municipio 1202) dio 92,282 personas en 2026. En el prototipo se contrastaron 144 valores municipales con la publicación oficial (Guatemala, Quetzaltenango y Cobán). El Excel sirvió como referencia de validación.

El IPC se expresa en puntos, base 2024 = 100. Para enero–octubre de 2026 se observaron enteros en la API. En octubre devolvió 106 frente al 106.24 publicado. Se conserva la precisión recibida. Los meses disponibles dependen del recurso.

## Explorar otros recursos del portal

```python
from ine_gt import INEClient
with INEClient() as cliente:
    conjuntos = cliente.buscar_conjuntos("IPC")
    if not conjuntos.empty:
        recursos = cliente.recursos(conjuntos.iloc[0]["id"])
        print(recursos)
        if not recursos.empty:
            activos = recursos.loc[recursos["datastore_active"] == True]
            if not activos.empty:
                muestra = cliente.datos(activos.iloc[0]["id"], max_rows=5)
                print(muestra)
                print(muestra.attrs["source"])
```

La búsqueda del portal devuelve conjuntos y recursos. La búsqueda local devuelve series con reglas estadísticas documentadas. En datos(), limit controla el tamaño de página, max_rows limita el total y filters admite nombres y valores de campos del recurso. La procedencia incluye filtros, URLs por página y fecha UTC.

## Pruebas

Ejecuta `python -m pip install -e '.[dev]'` y `python -m pytest -q`. Las pruebas locales usan respuestas simuladas para funcionar sin conexión. Los ejemplos del README requieren acceso a datos.ine.gob.gt.
