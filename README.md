# Consultar datos del INE de Guatemala con Python

Con `ine_gt` puedes responder dos preguntas: **¿cómo cambió el índice de precios de Guatemala durante un año?** y **¿cuántas personas se estiman en un municipio?** Cada resultado incluye el período, el valor y la información necesaria para citarlo. Buscar nombres funciona sin conexión. Obtener cifras requiere acceso a `datos.ine.gob.gt`.

## Mi primera consulta

**En Google Colab**, abre un cuaderno, pega esta línea en una celda y ejecútala. Así instalas la biblioteca desde la rama principal de este proyecto:

```text
%pip install git+https://github.com/brag01/dataton-ine-2026.git@master
```

**En tu computadora**, necesitas Python 3.10 o posterior. Si descargaste el proyecto como ZIP, descomprímelo. Abre una terminal en la carpeta que contiene `pyproject.toml` y ejecuta `python -m pip install .`.

En otra celda de Colab o en Python, copia estas tres líneas:

```python
import ine_gt as ine
ipc = ine.cargar_serie("ipc_nacional_mensual", año=2026)
print(ipc, ine.mostrar_fuente(ipc).T, sep="\n\n")
```

La primera tabla tiene una fila por mes disponible. Por ejemplo, `2026-10` significa octubre de 2026. El `valor` se mide en **puntos de índice** y el promedio de 2024 equivale a 100. Un valor de 106 indica un nivel de precios 6 % superior al promedio de 2024. Para obtener la variación mensual necesitas comparar dos meses consecutivos. La segunda tabla identifica el recurso consultado y cuándo se obtuvo.

## Qué escribir en `cargar_serie`

| Quiero obtener | Primer argumento exacto (`id_serie`) | Otros argumentos |
| --- | --- | --- |
| IPC nacional por mes | `"ipc_nacional_mensual"` | `año` obligatorio como entero de cuatro dígitos, por ejemplo `año=2026`. |
| Población por municipio al 30 de junio | `"poblacion_municipal_anual"` | `municipio` obligatorio como código entero. `año` opcional de 2015 a 2030; si lo omites, recibes los 16 años. `sexo` opcional: `0` ambos (predeterminado), `1` hombres, `2` mujeres. |

Si solo conoces el tema, usa `ine.buscar_serie("ipc")` o `ine.buscar_serie("población municipal")`. Elige el identificador de la columna `id_serie` y cópialo exactamente. La búsqueda reconoce `"IPC"` y `"ipc"`; el cargador requiere `"ipc_nacional_mensual"`.

## Encontrar un municipio y citar su población

Busca por nombre en el catálogo de 340 municipios. Puedes omitir las tildes. **Comprueba el departamento** antes de elegir el código: hay un San Pedro Sacatepéquez en Guatemala y otro en San Marcos.

```python
import ine_gt as ine
print(ine.buscar_municipio("San Pedro Sacatepequez"))
```

Para el de **San Marcos**, el código es `1202`. Este ejemplo devuelve la proyección de población para ambos sexos en 2026, en personas:

```python
poblacion = ine.cargar_serie("poblacion_municipal_anual", municipio=1202, año=2026)
fuente = ine.mostrar_fuente(poblacion)
print(poblacion)
print(fuente[["unidad", "consulta", "fecha_consulta_utc", "operacion"]].T)
```

Al citar la cifra, incluye municipio y departamento, período, unidad, URL y fecha de consulta. La biblioteca suma las 71 categorías de edad de la selección. Con `sexo=0` el total ya incluye a hombres y mujeres.

## Usar el resultado en un análisis o agente

Ambas series devuelven un `pandas.DataFrame` con las columnas `periodo` y `valor`. En el IPC el período es mensual; en población es un año entero. Guarda también `ine.mostrar_fuente(tabla)` si vas a exportar las cifras a CSV: la procedencia está en los metadatos de la tabla original.

| Si ocurre esto | Qué hacer |
| --- | --- |
| La búsqueda tiene cero o varias coincidencias | Revisa los nombres y la cobertura. Selecciona una fila antes de extraer el ID o código. |
| El IPC devuelve una tabla vacía y un aviso | Comprueba `tabla.empty` y comunica «sin observaciones». Si hay algunos meses, verifica que estén todos los que requiere tu cálculo. |
| Aparece un aviso de precisión del IPC | Conserva el valor y cita la nota. En octubre de 2026 se observó 106 en la API y 106.24 en la publicación. |
| `ValueError` por argumentos o cifras inválidas | Revisa el mensaje. Corrige el ID, año, municipio o sexo si corresponde. Si el índice es inválido o faltan edades para el total, revisa el recurso antes de usar la cifra. |
| `ine.INEAPIError` | Revisa la acción o recurso del mensaje. Comprueba la conexión si falló la solicitud y el esquema si faltó una columna. |

## Buscar otros datos en el portal

Para descubrir las series que puedes cargar, consulta el catálogo local. Funciona sin conexión:

```python
with ine.INEClient() as cliente:
    print(cliente.catalogo()[["id_serie", "argumentos", "ejemplo"]])
```

Usa `cliente.catalogo("ipc")` para filtrar por tema. Para explorar censos, usa `cliente.buscar_conjuntos("censo")`, elige un conjunto y llama a `cliente.recursos(conjunto_id)`. Con el ID de un recurso que tenga `datastore_active=True`, `cliente.campos(resource_id)` muestra sus columnas y tipos antes de descargar filas.

Para explorar conjuntos adicionales, usa `INEClient`. Busca un tema y selecciona el conjunto por su título:

```python
with ine.INEClient() as cliente:
    conjuntos = cliente.buscar_conjuntos("IPC")
    print(conjuntos)
```

| Siguiente paso | Método |
| --- | --- |
| Ver los archivos de un conjunto y sus formatos | `cliente.recursos(conjunto_id)` con el `id` del conjunto elegido |
| Consultar filas de un recurso con `datastore_active=True` | `cliente.datos(resource_id, max_rows=5)` con el `id` del recurso |
| Filtrar por columnas del recurso | `cliente.datos(resource_id, filters={"Año": 2026}, max_rows=10)` si el recurso tiene una columna llamada `Año` |
| Obtener la procedencia de esas filas | `muestra.attrs["source"]`, donde `muestra` es la tabla devuelta por `datos` |
| Ejecutar otra acción de lectura de CKAN | `cliente.action(nombre, params)` devuelve el resultado JSON de la acción |

Ejecuta los métodos del cliente dentro de `with ine.INEClient() as cliente:`. En `datos`, `max_rows` limita el total y `limit` controla cuántas filas solicita cada página.

[Cambios por versión](CHANGELOG.md) · [Desarrollo y preparación de versiones](HARNESS.md)
