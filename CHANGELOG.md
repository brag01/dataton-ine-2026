# Cambios por versión

## Pendiente de publicación

- `INEClient.vista_previa(resource_id)` consulta los campos vigentes y unos pocos valores de ejemplo de cada variable antes de descargar un recurso.

- `INEClient.catalogo()` permite descubrir las series disponibles y cómo cargarlas. `INEClient.campos(resource_id)` consulta los nombres y tipos de las columnas de un recurso DataStore.

- El IPC emite un aviso si la consulta está vacía o si devuelve valores enteros en el período documentado de enero a octubre de 2026. El resultado conserva el valor recibido y la fuente.
- Un valor de IPC ausente, no numérico, infinito o negativo genera un error que identifica el período. Si falta una columna de una serie, el mensaje identifica el recurso que se debe revisar.
- El manual incluye los dos identificadores admitidos, la búsqueda de municipios por departamento y los datos necesarios para citar una cifra.

## 2.0.0

- Consulta del IPC mensual nacional y de las estimaciones y proyecciones anuales de población municipal para 2015–2030.
- Búsqueda local de series y municipios, exploración del catálogo del INE y consulta de filas con filtros y procedencia.
