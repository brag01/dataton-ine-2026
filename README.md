# Consultar datos del INE de Guatemala con Python

Con `ine_gt` puedes consultar el índice de precios al consumidor (IPC) de Guatemala por mes o la población estimada y proyectada de un municipio por año. Cada consulta entrega una tabla y la fuente que puedes citar.

## Primera consulta: IPC de un año

Instala la biblioteca con Python 3.10 o posterior. En una terminal, abre la carpeta del proyecto y ejecuta `python -m pip install .`. Luego, en Python:

```python
import ine_gt as ine
ipc = ine.cargar_serie("ipc_nacional_mensual", año=2026)
print(ipc, ine.mostrar_fuente(ipc).T, sep="\n\n")
```

Obtendrás una fila por mes disponible. La columna `periodo` identifica el mes y `valor` contiene el índice en puntos (base 2024 = 100). Debajo de la tabla verás la fuente y la fecha de consulta.

## ¿Qué acepta `ine.cargar_serie`?

El primer argumento es `id_serie`. El catálogo de esta versión contiene exactamente estos dos identificadores. Cópialos tal como aparecen, en minúsculas y con guiones bajos.

| Quiero consultar | `id_serie` exacto | Argumentos |
| --- | --- | --- |
| IPC mensual de Guatemala | `ipc_nacional_mensual` | `año` obligatorio, entero de cuatro dígitos. Solo admite el año. |
| Población anual de un municipio al 30 de junio | `poblacion_municipal_anual` | `municipio` obligatorio, código entero. `año` opcional entre 2015 y 2030; al omitirlo devuelve todo el período. `sexo` opcional: `0` ambos (predeterminado), `1` hombres, `2` mujeres. |

Si solo conoces el tema, búscalo primero. La búsqueda local admite palabras parciales e ignora tildes y mayúsculas:

```python
opciones = ine.buscar_serie("ipc")
print(opciones[["id_serie", "nombre"]])
# id_serie: ipc_nacional_mensual
```

Elige el `id_serie` de la fila que necesitas. Por ejemplo, `ine.cargar_serie("ipc", año=2026)` lanza `ValueError`; la llamada válida es `ine.cargar_serie("ipc_nacional_mensual", año=2026)`. Para cargar población, pasa `municipio` y `sexo` por nombre, por ejemplo `ine.cargar_serie("poblacion_municipal_anual", municipio=1202, año=2026)`.

<details>
<summary>Instalación en Google Colab desde un ZIP</summary>

En Colab, sube el ZIP y ejecuta:

```python
!unzip -qo ine_gt_ver2.0.zip
%pip install ./ine_gt_ver2.0
```

</details>

## ¿Cómo elijo el municipio correcto?

El catálogo local incluye 340 municipios. San Pedro Sacatepéquez aparece en dos departamentos. Este ejemplo selecciona el de San Marcos antes de consultar su población:

```python
import ine_gt as ine
serie = ine.buscar_serie("población municipal").id_serie.item()
opciones = ine.buscar_municipio("San Pedro Sacatepéquez")
codigo = int(opciones.loc[opciones.departamento == "San Marcos", "codigo"].item())
tabla = ine.cargar_serie(serie, año=2026, municipio=codigo)
print(tabla)
print(ine.mostrar_fuente(tabla).T.to_string())
```

Población al 30 de junio. Omite el año para recuperar 2015–2030. Sexo 0 corresponde a ambos sexos, 1 a hombres y 2 a mujeres. Se suman las 71 categorías de edad de un único sexo. La consulta histórica de San Pedro Sacatepéquez, departamento de San Marcos (municipio 1202), dio 92,282 personas en 2026. En el prototipo se contrastaron 144 valores municipales con la publicación oficial (Guatemala, Quetzaltenango y Cobán). El Excel sirvió como referencia de validación.

El IPC se expresa en puntos, base 2024 = 100. Para enero–octubre de 2026 se observaron enteros en la API. En octubre devolvió 106 frente al 106.24 publicado. Se conserva la precisión recibida. Los meses disponibles dependen del recurso.

### Interpretar la respuesta en un programa

Ambas series devuelven un `pandas.DataFrame` con `periodo` y `valor`. Para IPC, el período es mensual y el valor se expresa en puntos de índice. Para población, el período es un año entero y el valor se expresa en personas.

| Situación | Qué hacer |
| --- | --- |
| IPC sin observaciones | La función emite `UserWarning` y devuelve una tabla vacía con fuente. Comprueba `tabla.empty` y registra «sin observaciones» en el informe. |
| IPC con algunos meses disponibles | Usa los meses presentes. Si el cálculo exige un año completo, comprueba que haya 12 meses. |
| IPC con un valor ausente, no numérico, infinito o negativo | La función lanza `ValueError` e indica el mes y el recurso que debes revisar. |
| Aviso de precisión del IPC | Conserva el valor recibido y cita la nota de `mostrar_fuente(tabla)`. El aviso señala valores enteros en el período documentado de enero a octubre de 2026. |
| Población sin filas o con edades incompletas | La función lanza `ValueError`. Revisa el municipio y el sexo o, si faltan edades, consulta el recurso antes de publicar un total. |
| Falta una columna esperada | La función lanza `INEAPIError`. El mensaje identifica el recurso y la columna para comprobar el esquema en el portal. |

## Explorar otros recursos del portal

| Para qué sirve | Función | Origen |
| --- | --- | --- |
| Encontrar indicadores admitidos y sus unidades | `buscar_serie(texto)` | Catálogo local |
| Resolver el código de un municipio por nombre y departamento | `buscar_municipio(nombre)` | Catálogo local |
| Obtener el IPC mensual o la población anual por municipio | `cargar_serie(id_serie, ...)` | Portal |
| Citar la consulta, fecha UTC, filtros y unidad de una cifra | `mostrar_fuente(tabla)` | Metadatos de la tabla |
| Buscar conjuntos por tema | `cliente.buscar_conjuntos(texto)` | Catálogo del portal |
| Ver los archivos de un conjunto y cuáles admiten DataStore | `cliente.recursos(conjunto_id)` | Catálogo del portal |
| Leer filas aplicando filtros y un límite total | `cliente.datos(resource_id, filters=..., max_rows=...)` | DataStore |
| Ejecutar una acción CKAN por nombre y obtener el resultado JSON | `cliente.action(name, params)` | API del portal |

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

<details>
<summary>Para quienes mantienen la biblioteca: entorno y verificación</summary>

Desde la raíz del repositorio en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest -q
```

La suite predeterminada usa respuestas simuladas. Para verificar el catálogo, el IPC y la población contra el portal real, ejecuta `.\.venv\Scripts\python.exe harness.py live`. Esta consulta imprime las cifras y sus fuentes y requiere acceso a datos.ine.gob.gt. Las instrucciones para trabajar en el repositorio están en [AGENTS.md](AGENTS.md).

</details>
