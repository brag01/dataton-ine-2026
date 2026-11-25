# Trabajar en ine_gt

El README contiene la instalación, el ejemplo mínimo y los resultados esperados. Para cargar una serie desde otro programa, importa `ine_gt` y usa `cargar_serie`. Para buscar candidatos por nombre, usa `buscar_serie` o `buscar_municipio`. Si el nombre corresponde a varios municipios, selecciona por departamento antes de consultar. Para citar una cifra, conserva `mostrar_fuente(tabla)` junto con el resultado.

## Cinco reglas para cambios en la biblioteca

1. **Mantén una consulta útil en tres líneas.** Comprueba que el ejemplo inicial del README funciona con los argumentos públicos. Debe mostrar una cifra con su período y permitir identificar la fuente.
2. **Expresa el contrato en Python.** Anota las entradas y el retorno de las funciones públicas. Documenta los argumentos que dependen de la serie, las columnas de salida y sus unidades. Esto permite construir una llamada correcta desde la firma y la docstring.
3. **Explica cómo actuar ante cada problema.** Usa avisos de Python cuando el resultado pueda entregarse con una salvedad. Conserva la procedencia y los valores recibidos. Si los datos impiden calcular un total válido, sigue el contrato de excepciones del README. Indica qué argumento o recurso revisar.
4. **Conserva una interfaz pequeña.** Reutiliza las funciones públicas y las dependencias actuales. Justifica cualquier nueva abstracción compartida con dos usos reales. Al cambiar una definición estadística, documenta el criterio de Mary y la fuente del INE que lo respalda.
5. **Prueba la promesa estadística sin red.** Simula las respuestas de CKAN y comprueba tanto el resultado como el comportamiento ante datos incompletos. Para un aviso, prueba cuándo se emite y que el valor o la tabla devueltos siguen siendo correctos.

En PowerShell, ejecuta `.\.venv\Scripts\python.exe -m pytest -q` desde la raíz. Si falta el entorno, créalo con los comandos de la sección «Pruebas» del README. Distingue en el informe de cambios las pruebas simuladas de cualquier consulta real al portal.
