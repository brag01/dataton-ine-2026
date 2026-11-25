"""Catálogo inicial de series del INE de Guatemala. Requiere pandas."""

import unicodedata
import warnings
from typing import Literal

import pandas as pd

from .client import INEClient
from .exceptions import INEAPIError


_IPC = {
    "id_serie": "ipc_nacional_mensual",
    "nombre": "Índice de Precios al Consumidor (IPC)",
    "frecuencia": "Mensual",
    "cobertura": "Nacional",
    "base": "Año 2024 = 100",
    "unidad": "Puntos de índice",
    "recurso": "4b1c485c-78cb-4a0e-b11e-39306a8647f1",
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
    terminos = _normalizar(texto).split()
    coincidencias = []
    for ficha in _CATALOGO:
        descripcion = " ".join(ficha.get(campo, "") for campo in
                               ("id_serie", "nombre", "frecuencia", "cobertura", "base"))
        indice = _normalizar(descripcion)
        if all(termino in indice for termino in terminos):
            coincidencias.append(ficha)
    return pd.DataFrame(coincidencias, columns=[*_IPC, "periodo", "fecha_referencia"])


_MESES = {nombre: numero for numero, nombre in enumerate(
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(), 1
)}


def _consultar(ficha, filtros, limite):
    with INEClient() as cliente:
        datos = cliente.datos(ficha["recurso"], limit=limite, filters=filtros)
    return datos, datos.attrs["source"]


def _validar_columnas(datos, ficha, requeridas):
    faltantes = sorted(set(requeridas).difference(datos.columns))
    if faltantes:
        raise INEAPIError(
            f"Faltan columnas para {ficha['id_serie']}: {', '.join(faltantes)}. "
            f"Revise el esquema del recurso {ficha['recurso']} en el portal del INE."
        )


def _cargar_poblacion(municipio, sexo, año):
    if type(municipio) is not int or municipio < 101:
        raise ValueError("Indique el código municipal completo, por ejemplo municipio=101.")
    if type(sexo) is not int or sexo not in (0, 1, 2):
        raise ValueError("Use sexo=0 para ambos sexos, 1 para hombres o 2 para mujeres.")
    if año is not None and (type(año) is not int or not 2015 <= año <= 2030):
        raise ValueError("El año debe estar entre 2015 y 2030.")
    filtros = {"DEPTO": municipio // 100, "MUPIO": municipio, "SEXO": sexo}
    datos, fuente = _consultar(_POBLACION, filtros, 72)
    if datos.empty:
        raise ValueError(f"Sin registros para el municipio {municipio} y sexo {sexo}. "
                         "Verifique el código con buscar_municipio() y revise el sexo solicitado.")
    años = [año] if año is not None else range(2015, 2031)
    _validar_columnas(datos, _POBLACION, [*filtros, "EDAD", *(f"{p}.0" for p in años)])
    for campo, valor in filtros.items():
        if not pd.to_numeric(datos[campo]).eq(valor).all():
            raise ValueError("La API devolvió datos fuera del filtro municipal.")
    edades = pd.to_numeric(datos["EDAD"])
    if len(edades) != 71 or set(edades) != set(range(71)):
        raise ValueError("La API devolvió categorías de edad incompletas o duplicadas.")
    valores = []
    for periodo in años:
        columna = pd.to_numeric(datos[f"{periodo}.0"], errors="raise")
        if columna.isna().any() or (columna < 0).any() or (columna % 1 != 0).any():
            raise ValueError(f"Población inválida para {periodo}.")
        valores.append(int(columna.sum()))
    tabla = pd.DataFrame({"periodo": años, "valor": valores})
    tabla.attrs.update(id_serie=_POBLACION["id_serie"], recurso=_POBLACION["recurso"],
                       consulta=fuente["consultas"][0], **fuente,
                       periodo_solicitado=año or "2015–2030", operacion="Suma de 71 categorías de edad por año",
                       base=None, unidad="Personas", nota=_POBLACION["nota"],
                       municipio=municipio, sexo=sexo)
    return tabla


def cargar_serie(
    id_serie: Literal["ipc_nacional_mensual", "poblacion_municipal_anual"],
    año: int | None = None,
    *,
    municipio: int | None = None,
    sexo: Literal[0, 1, 2] | None = None,
) -> pd.DataFrame:
    """Devuelve periodo y valor, con procedencia accesible mediante mostrar_fuente().

    cargar_serie("ipc_nacional_mensual", año=2026) devuelve los meses disponibles
    como períodos de pandas y el índice en puntos (base 2024 = 100). Emite
    UserWarning si faltan todas las observaciones o se observa el caso documentado
    de precisión. La tabla vacía conserva su fuente.

    cargar_serie("poblacion_municipal_anual", municipio=1202) devuelve años y
    personas al 30 de junio. El año opcional selecciona uno de 2015 a 2030.
    Sexo: 0 (ambos, por defecto), 1 (hombres), 2 (mujeres). Si faltan filas
    o edades para calcular el total municipal, lanza ValueError.
    """
    ficha = next((f for f in _CATALOGO if f["id_serie"] == id_serie), None)
    if ficha is None:
        opciones = ", ".join(f["id_serie"] for f in _CATALOGO)
        raise ValueError(f"Serie desconocida: {id_serie!r}. Use uno de estos identificadores: {opciones}.")
    if ficha is _POBLACION:
        return _cargar_poblacion(municipio, 0 if sexo is None else sexo, año)
    if municipio is not None or sexo is not None:
        raise ValueError("Los filtros municipio y sexo corresponden a población municipal.")
    if type(año) is not int or not 1000 <= año <= 9999:
        raise ValueError("El año debe ser un entero de cuatro dígitos.")
    filtros = {"Año": año, ficha["campo_filtro"]: ficha["valor_filtro"]}
    datos, fuente = _consultar(ficha, filtros, 13)
    if len(datos.index):
        _validar_columnas(datos, ficha, [*filtros, "Mes", ficha["campo_valor"]])
    registros = datos.to_dict("records")
    if len(registros) > 12:
        raise ValueError("La API devolvió más de doce registros para una serie mensual.")
    periodos, valores = [], []
    for registro in registros:
        if registro[ficha["campo_filtro"]] != ficha["valor_filtro"]:
            raise ValueError("La API devolvió otro indicador.")
        mes = _MESES.get(str(registro["Mes"]).strip().lower())
        if mes is None or str(registro["Año"]) != str(año):
            raise ValueError("La API devolvió un período inesperado.")
        periodos.append(pd.Period(year=año, month=mes, freq="M"))
        valores.append(registro[ficha["campo_valor"]])
    tabla = pd.DataFrame({"periodo": pd.PeriodIndex(periodos, freq="M"),
                          "valor": pd.to_numeric(valores, errors="coerce")})
    valor = tabla["valor"]
    invalidos = valor.isna() | (valor < 0) | (valor == float("inf"))
    if invalidos.any():
        periodo = tabla.loc[invalidos, "periodo"].iloc[0]
        raise ValueError(f"IPC inválido para {periodo}: se esperaba un valor finito y no negativo. "
                         f"Revise el campo República del recurso {ficha['recurso']}.")
    if tabla["periodo"].duplicated().any():
        raise ValueError("La API devolvió meses duplicados.")
    tabla = tabla.sort_values("periodo", ignore_index=True)
    tabla.attrs.update(id_serie=id_serie, recurso=ficha["recurso"], consulta=fuente["consultas"][0], **fuente,
                       periodo_solicitado=año, operacion="Lectura mensual del campo República",
                       base=ficha["base"], unidad=ficha["unidad"], nota=ficha["nota"])
    if tabla.empty:
        warnings.warn(f"Sin observaciones de IPC para {año}. Revise el año y la fuente "
                      "antes de calcular un indicador.", UserWarning, stacklevel=2)
    elif año == 2026 and ((tabla["periodo"].dt.month <= 10) & (tabla["valor"] % 1 == 0)).any():
        warnings.warn(f"{ficha['nota']} Se conserva el valor recibido. "
                      "Consulte la publicación del INE si necesita decimales.", UserWarning, stacklevel=2)
    return tabla


def mostrar_fuente(tabla: pd.DataFrame) -> pd.DataFrame:
    """Devuelve la procedencia registrada al cargar la serie como tabla de una fila."""
    if not isinstance(tabla, pd.DataFrame):
        raise TypeError("Se esperaba una tabla de pandas obtenida con cargar_serie().")
    campos = ("id_serie", "recurso", "consulta", "fecha_consulta_utc",
              "base", "unidad", "nota")
    if any(campo not in tabla.attrs for campo in campos):
        raise ValueError("La tabla carece de metadatos de procedencia completos.")
    return pd.DataFrame([{campo: tabla.attrs[campo] for campo in tabla.attrs}])

# Catálogo municipal del INE, proyecciones 2015–2030
_MUNICIPIOS = [(101, 'Guatemala', 'Guatemala'),
 (102, 'Santa Catarina Pinula', 'Guatemala'),
 (103, 'San José Pinula', 'Guatemala'),
 (104, 'San José del Golfo', 'Guatemala'),
 (105, 'Palencia', 'Guatemala'),
 (106, 'Chinautla', 'Guatemala'),
 (107, 'San Pedro Ayampuc', 'Guatemala'),
 (108, 'Mixco', 'Guatemala'),
 (109, 'San Pedro Sacatepéquez', 'Guatemala'),
 (110, 'San Juan Sacatepéquez', 'Guatemala'),
 (111, 'San Raymundo', 'Guatemala'),
 (112, 'Chuarrancho', 'Guatemala'),
 (113, 'Fraijanes', 'Guatemala'),
 (114, 'Amatitlán', 'Guatemala'),
 (115, 'Villa Nueva', 'Guatemala'),
 (116, 'Villa Canales', 'Guatemala'),
 (117, 'San Miguel Petapa', 'Guatemala'),
 (201, 'Guastatoya', 'El Progreso'),
 (202, 'Morazán', 'El Progreso'),
 (203, 'San Agustín Acasaguastlán', 'El Progreso'),
 (204, 'San Cristóbal Acasaguastlán', 'El Progreso'),
 (205, 'El Jícaro', 'El Progreso'),
 (206, 'Sansare', 'El Progreso'),
 (207, 'Sanarate', 'El Progreso'),
 (208, 'San Antonio La Paz', 'El Progreso'),
 (301, 'Antigua Guatemala', 'Sacatepéquez'),
 (302, 'Jocotenango', 'Sacatepéquez'),
 (303, 'Pastores', 'Sacatepéquez'),
 (304, 'Sumpango', 'Sacatepéquez'),
 (305, 'Santo Domingo Xenacoj', 'Sacatepéquez'),
 (306, 'Santiago Sacatepéquez', 'Sacatepéquez'),
 (307, 'San Bartolomé Milpas Altas', 'Sacatepéquez'),
 (308, 'San Lucas Sacatepéquez', 'Sacatepéquez'),
 (309, 'Santa Lucía Milpas Altas', 'Sacatepéquez'),
 (310, 'Magdalena Milpas Altas', 'Sacatepéquez'),
 (311, 'Santa María de Jesús', 'Sacatepéquez'),
 (312, 'Ciudad Vieja', 'Sacatepéquez'),
 (313, 'San Miguel Dueñas', 'Sacatepéquez'),
 (314, 'San Juan Alotenango', 'Sacatepéquez'),
 (315, 'San Antonio Aguas Calientes', 'Sacatepéquez'),
 (316, 'Santa Catarina Barahona', 'Sacatepéquez'),
 (401, 'Chimaltenango', 'Chimaltenango'),
 (402, 'San José Poaquil', 'Chimaltenango'),
 (403, 'San Martín Jilotepeque', 'Chimaltenango'),
 (404, 'San Juan Comalapa', 'Chimaltenango'),
 (405, 'Santa Apolonia', 'Chimaltenango'),
 (406, 'Tecpán Guatemala', 'Chimaltenango'),
 (407, 'Patzún', 'Chimaltenango'),
 (408, 'San Miguel Pochuta', 'Chimaltenango'),
 (409, 'Patzicía', 'Chimaltenango'),
 (410, 'Santa Cruz Balanyá', 'Chimaltenango'),
 (411, 'Acatenango', 'Chimaltenango'),
 (412, 'San Pedro Yepocapa', 'Chimaltenango'),
 (413, 'San Andrés Itzapa', 'Chimaltenango'),
 (414, 'Parramos', 'Chimaltenango'),
 (415, 'Zaragoza', 'Chimaltenango'),
 (416, 'El Tejar', 'Chimaltenango'),
 (501, 'Escuintla', 'Escuintla'),
 (502, 'Santa Lucía Cotzumalguapa', 'Escuintla'),
 (503, 'La Democracia', 'Escuintla'),
 (504, 'Siquinalá', 'Escuintla'),
 (505, 'Masagua', 'Escuintla'),
 (506, 'Tiquisate', 'Escuintla'),
 (507, 'La Gomera', 'Escuintla'),
 (508, 'Guanagazapa', 'Escuintla'),
 (509, 'San José', 'Escuintla'),
 (510, 'Iztapa', 'Escuintla'),
 (511, 'Palín', 'Escuintla'),
 (512, 'San Vicente Pacaya', 'Escuintla'),
 (513, 'Nueva Concepción', 'Escuintla'),
 (514, 'Sipacate', 'Escuintla'),
 (601, 'Cuilapa', 'Santa Rosa'),
 (602, 'Barberena', 'Santa Rosa'),
 (603, 'Santa Rosa de Lima', 'Santa Rosa'),
 (604, 'Casillas', 'Santa Rosa'),
 (605, 'San Rafael Las Flores', 'Santa Rosa'),
 (606, 'Oratorio', 'Santa Rosa'),
 (607, 'San Juan Tecuaco', 'Santa Rosa'),
 (608, 'Chiquimulilla', 'Santa Rosa'),
 (609, 'Taxisco', 'Santa Rosa'),
 (610, 'Santa María Ixhuatán', 'Santa Rosa'),
 (611, 'Guazacapán', 'Santa Rosa'),
 (612, 'Santa Cruz Naranjo', 'Santa Rosa'),
 (613, 'Pueblo Nuevo Viñas', 'Santa Rosa'),
 (614, 'Nueva Santa Rosa', 'Santa Rosa'),
 (701, 'Sololá', 'Sololá'),
 (702, 'San José Chacayá', 'Sololá'),
 (703, 'Santa María Visitación', 'Sololá'),
 (704, 'Santa Lucía Utatlán', 'Sololá'),
 (705, 'Nahualá', 'Sololá'),
 (706, 'Santa Catarina Ixtahuacán', 'Sololá'),
 (707, 'Santa Clara La Laguna', 'Sololá'),
 (708, 'Concepción', 'Sololá'),
 (709, 'San Andrés Semetabaj', 'Sololá'),
 (710, 'Panajachel', 'Sololá'),
 (711, 'Santa Catarina Palopó', 'Sololá'),
 (712, 'San Antonio Palopó', 'Sololá'),
 (713, 'San Lucas Tolimán', 'Sololá'),
 (714, 'Santa Cruz La Laguna', 'Sololá'),
 (715, 'San Pablo La Laguna', 'Sololá'),
 (716, 'San Marcos La Laguna', 'Sololá'),
 (717, 'San Juan La Laguna', 'Sololá'),
 (718, 'San Pedro La Laguna', 'Sololá'),
 (719, 'Santiago Atitlán', 'Sololá'),
 (801, 'Totonicapán', 'Totonicapán'),
 (802, 'San Cristóbal Totonicapán', 'Totonicapán'),
 (803, 'San Francisco El Alto', 'Totonicapán'),
 (804, 'San Andrés Xecul', 'Totonicapán'),
 (805, 'Momostenango', 'Totonicapán'),
 (806, 'Santa María Chiquimula', 'Totonicapán'),
 (807, 'Santa Lucía la Reforma', 'Totonicapán'),
 (808, 'San Bartolo Aguas Calientes', 'Totonicapán'),
 (901, 'Quetzaltenango', 'Quetzaltenango'),
 (902, 'Salcajá', 'Quetzaltenango'),
 (903, 'San Juan Olintepeque', 'Quetzaltenango'),
 (904, 'San Carlos Sija', 'Quetzaltenango'),
 (905, 'Sibilia', 'Quetzaltenango'),
 (906, 'Cabricán', 'Quetzaltenango'),
 (907, 'Cajolá', 'Quetzaltenango'),
 (908, 'San Miguel Siguilá', 'Quetzaltenango'),
 (909, 'San Juan Ostuncalco', 'Quetzaltenango'),
 (910, 'San Mateo', 'Quetzaltenango'),
 (911, 'Concepción Chiquirichapa', 'Quetzaltenango'),
 (912, 'San Martín Sacatepéquez', 'Quetzaltenango'),
 (913, 'Almolonga', 'Quetzaltenango'),
 (914, 'Cantel', 'Quetzaltenango'),
 (915, 'Huitán', 'Quetzaltenango'),
 (916, 'Zunil', 'Quetzaltenango'),
 (917, 'Colomba Costa Cuca', 'Quetzaltenango'),
 (918, 'San Francisco La Unión', 'Quetzaltenango'),
 (919, 'El Palmar', 'Quetzaltenango'),
 (920, 'Coatepeque', 'Quetzaltenango'),
 (921, 'Génova', 'Quetzaltenango'),
 (922, 'Flores Costa Cuca', 'Quetzaltenango'),
 (923, 'La Esperanza', 'Quetzaltenango'),
 (924, 'Palestina de Los Altos', 'Quetzaltenango'),
 (1001, 'Mazatenango', 'Suchitepéquez'),
 (1002, 'Cuyotenango', 'Suchitepéquez'),
 (1003, 'San Francisco Zapotitlán', 'Suchitepéquez'),
 (1004, 'San Bernardino', 'Suchitepéquez'),
 (1005, 'San José el Ídolo', 'Suchitepéquez'),
 (1006, 'Santo Domingo Suchitepéquez', 'Suchitepéquez'),
 (1007, 'San Lorenzo', 'Suchitepéquez'),
 (1008, 'Samayac', 'Suchitepéquez'),
 (1009, 'San Pablo Jocopilas', 'Suchitepéquez'),
 (1010, 'San Antonio Suchitepéquez', 'Suchitepéquez'),
 (1011, 'San Miguel Panán', 'Suchitepéquez'),
 (1012, 'San Gabriel', 'Suchitepéquez'),
 (1013, 'Chicacao', 'Suchitepéquez'),
 (1014, 'Patulul', 'Suchitepéquez'),
 (1015, 'Santa Bárbara', 'Suchitepéquez'),
 (1016, 'San Juan Bautista', 'Suchitepéquez'),
 (1017, 'Santo Tomas La Unión', 'Suchitepéquez'),
 (1018, 'Zunilito', 'Suchitepéquez'),
 (1019, 'Pueblo Nuevo', 'Suchitepéquez'),
 (1020, 'Río Bravo', 'Suchitepéquez'),
 (1021, 'San José La Máquina', 'Suchitepéquez'),
 (1101, 'Retalhuleu', 'Retalhuleu'),
 (1102, 'San Sebastián', 'Retalhuleu'),
 (1103, 'Santa Cruz Muluá', 'Retalhuleu'),
 (1104, 'San Martín Zapotitlán', 'Retalhuleu'),
 (1105, 'San Felipe', 'Retalhuleu'),
 (1106, 'San Andrés Villa Seca', 'Retalhuleu'),
 (1107, 'Champerico', 'Retalhuleu'),
 (1108, 'Nuevo San Carlos', 'Retalhuleu'),
 (1109, 'El Asintal', 'Retalhuleu'),
 (1201, 'San Marcos', 'San Marcos'),
 (1202, 'San Pedro Sacatepéquez', 'San Marcos'),
 (1203, 'San Antonio Sacatepéquez', 'San Marcos'),
 (1204, 'Comitancillo', 'San Marcos'),
 (1205, 'San Miguel Ixtahuacán', 'San Marcos'),
 (1206, 'Concepción Tutuapa', 'San Marcos'),
 (1207, 'Tacaná', 'San Marcos'),
 (1208, 'Sibinal', 'San Marcos'),
 (1209, 'Tajumulco', 'San Marcos'),
 (1210, 'Tejutla', 'San Marcos'),
 (1211, 'San Rafael Pie de la Cuesta', 'San Marcos'),
 (1212, 'Nuevo Progreso', 'San Marcos'),
 (1213, 'El Tumbador', 'San Marcos'),
 (1214, 'San José el Rodeo', 'San Marcos'),
 (1215, 'Malacatán', 'San Marcos'),
 (1216, 'Catarina', 'San Marcos'),
 (1217, 'Ayutla', 'San Marcos'),
 (1218, 'Ocós', 'San Marcos'),
 (1219, 'San Pablo', 'San Marcos'),
 (1220, 'El Quetzal', 'San Marcos'),
 (1221, 'La Reforma', 'San Marcos'),
 (1222, 'Pajapita', 'San Marcos'),
 (1223, 'Ixchiguán', 'San Marcos'),
 (1224, 'San José Ojetenam', 'San Marcos'),
 (1225, 'San Cristóbal Cucho', 'San Marcos'),
 (1226, 'Sipacapa', 'San Marcos'),
 (1227, 'Esquipulas Palo Gordo', 'San Marcos'),
 (1228, 'Río Blanco', 'San Marcos'),
 (1229, 'San Lorenzo', 'San Marcos'),
 (1230, 'La Blanca', 'San Marcos'),
 (1301, 'Huehuetenango', 'Huehuetenango'),
 (1302, 'Chiantla', 'Huehuetenango'),
 (1303, 'Malacatancito', 'Huehuetenango'),
 (1304, 'Cuilco', 'Huehuetenango'),
 (1305, 'Nentón', 'Huehuetenango'),
 (1306, 'San Pedro Necta', 'Huehuetenango'),
 (1307, 'Jacaltenango', 'Huehuetenango'),
 (1308, 'San Pedro Soloma', 'Huehuetenango'),
 (1309, 'San Ildefonso Ixtahuacán', 'Huehuetenango'),
 (1310, 'Santa Bárbara', 'Huehuetenango'),
 (1311, 'La Libertad', 'Huehuetenango'),
 (1312, 'La Democracia', 'Huehuetenango'),
 (1313, 'San Miguel Acatán', 'Huehuetenango'),
 (1314, 'San Rafael La Independencia', 'Huehuetenango'),
 (1315, 'Todos Santos Cuchumatán', 'Huehuetenango'),
 (1316, 'San Juan Atitán', 'Huehuetenango'),
 (1317, 'Santa Eulalia', 'Huehuetenango'),
 (1318, 'San Mateo Ixtatán', 'Huehuetenango'),
 (1319, 'Colotenango', 'Huehuetenango'),
 (1320, 'San Sebastián Huehuetenango', 'Huehuetenango'),
 (1321, 'Tectitán', 'Huehuetenango'),
 (1322, 'Concepción Huista', 'Huehuetenango'),
 (1323, 'San Juan Ixcoy', 'Huehuetenango'),
 (1324, 'San Antonio Huista', 'Huehuetenango'),
 (1325, 'San Sebastián Coatán', 'Huehuetenango'),
 (1326, 'Santa Cruz Barillas', 'Huehuetenango'),
 (1327, 'Aguacatán', 'Huehuetenango'),
 (1328, 'San Rafael Petzal', 'Huehuetenango'),
 (1329, 'San Gaspar Ixchil', 'Huehuetenango'),
 (1330, 'Santiago Chimaltenango', 'Huehuetenango'),
 (1331, 'Santa Ana Huista', 'Huehuetenango'),
 (1332, 'Unión Cantinil', 'Huehuetenango'),
 (1333, 'Petatán', 'Huehuetenango'),
 (1401, 'Santa Cruz del Quiché', 'Quiché'),
 (1402, 'Chiché', 'Quiché'),
 (1403, 'Chinique', 'Quiché'),
 (1404, 'Zacualpa', 'Quiché'),
 (1405, 'Chajul', 'Quiché'),
 (1406, 'Santo Tomás Chichicastenango', 'Quiché'),
 (1407, 'Patzité', 'Quiché'),
 (1408, 'San Antonio Ilotenango', 'Quiché'),
 (1409, 'San Pedro Jocopilas', 'Quiché'),
 (1410, 'Cunén', 'Quiché'),
 (1411, 'San Juan Cotzal', 'Quiché'),
 (1412, 'Joyabaj', 'Quiché'),
 (1413, 'Santa María Nebaj', 'Quiché'),
 (1414, 'San Andrés Sajcabajá', 'Quiché'),
 (1415, 'San Miguel Uspantán', 'Quiché'),
 (1416, 'Sacapulas', 'Quiché'),
 (1417, 'San Bartolomé Jocotenango', 'Quiché'),
 (1418, 'Canillá', 'Quiché'),
 (1419, 'Chicamán', 'Quiché'),
 (1420, 'Playa Grande Ixcán', 'Quiché'),
 (1421, 'Pachalum', 'Quiché'),
 (1501, 'Salamá', 'Baja Verapaz'),
 (1502, 'San Miguel Chicaj', 'Baja Verapaz'),
 (1503, 'Rabinal', 'Baja Verapaz'),
 (1504, 'Cubulco', 'Baja Verapaz'),
 (1505, 'Granados', 'Baja Verapaz'),
 (1506, 'Santa Cruz El Chol', 'Baja Verapaz'),
 (1507, 'San Jerónimo', 'Baja Verapaz'),
 (1508, 'Purulhá', 'Baja Verapaz'),
 (1601, 'Cobán', 'Alta Verapaz'),
 (1602, 'Santa Cruz Verapaz', 'Alta Verapaz'),
 (1603, 'San Cristóbal Verapaz', 'Alta Verapaz'),
 (1604, 'Tactic', 'Alta Verapaz'),
 (1605, 'Tamahú', 'Alta Verapaz'),
 (1606, 'San Miguel Tucurú', 'Alta Verapaz'),
 (1607, 'Panzós', 'Alta Verapaz'),
 (1608, 'Senahú', 'Alta Verapaz'),
 (1609, 'San Pedro Carchá', 'Alta Verapaz'),
 (1610, 'San Juan Chamelco', 'Alta Verapaz'),
 (1611, 'San Agustín Lanquín', 'Alta Verapaz'),
 (1612, 'Santa María Cahabón', 'Alta Verapaz'),
 (1613, 'Chisec', 'Alta Verapaz'),
 (1614, 'Chahal', 'Alta Verapaz'),
 (1615, 'Fray Bartolomé de Las Casas', 'Alta Verapaz'),
 (1616, 'Santa Catalina La Tinta', 'Alta Verapaz'),
 (1617, 'Raxruhá', 'Alta Verapaz'),
 (1701, 'Flores', 'Petén'),
 (1702, 'San José', 'Petén'),
 (1703, 'San Benito', 'Petén'),
 (1704, 'San Andrés', 'Petén'),
 (1705, 'La Libertad', 'Petén'),
 (1706, 'San Francisco', 'Petén'),
 (1707, 'Santa Ana', 'Petén'),
 (1708, 'Dolores', 'Petén'),
 (1709, 'San Luis', 'Petén'),
 (1710, 'Sayaxché', 'Petén'),
 (1711, 'Melchor de Mencos', 'Petén'),
 (1712, 'Poptún', 'Petén'),
 (1713, 'Las Cruces', 'Petén'),
 (1714, 'El Chal', 'Petén'),
 (1801, 'Puerto Barrios', 'Izabal'),
 (1802, 'Livingston', 'Izabal'),
 (1803, 'El Estor', 'Izabal'),
 (1804, 'Morales', 'Izabal'),
 (1805, 'Los Amates', 'Izabal'),
 (1901, 'Zacapa', 'Zacapa'),
 (1902, 'Estanzuela', 'Zacapa'),
 (1903, 'Río Hondo', 'Zacapa'),
 (1904, 'Gualán', 'Zacapa'),
 (1905, 'Teculután', 'Zacapa'),
 (1906, 'Usumatlán', 'Zacapa'),
 (1907, 'Cabañas', 'Zacapa'),
 (1908, 'San Diego', 'Zacapa'),
 (1909, 'La Unión', 'Zacapa'),
 (1910, 'Huité', 'Zacapa'),
 (1911, 'San Jorge', 'Zacapa'),
 (2001, 'Chiquimula', 'Chiquimula'),
 (2002, 'San José La Arada', 'Chiquimula'),
 (2003, 'San Juan Ermita', 'Chiquimula'),
 (2004, 'Jocotán', 'Chiquimula'),
 (2005, 'Camotán', 'Chiquimula'),
 (2006, 'Olopa', 'Chiquimula'),
 (2007, 'Esquipulas', 'Chiquimula'),
 (2008, 'Concepción Las Minas', 'Chiquimula'),
 (2009, 'Quezaltepeque', 'Chiquimula'),
 (2010, 'San Jacinto', 'Chiquimula'),
 (2011, 'Ipala', 'Chiquimula'),
 (2101, 'Jalapa', 'Jalapa'),
 (2102, 'San Pedro Pinula', 'Jalapa'),
 (2103, 'San Luis Jilotepeque', 'Jalapa'),
 (2104, 'San Manuel Chaparrón', 'Jalapa'),
 (2105, 'San Carlos Alzatate', 'Jalapa'),
 (2106, 'Monjas', 'Jalapa'),
 (2107, 'Mataquescuintla', 'Jalapa'),
 (2201, 'Jutiapa', 'Jutiapa'),
 (2202, 'El Progreso', 'Jutiapa'),
 (2203, 'Santa Catarina Mita', 'Jutiapa'),
 (2204, 'Agua Blanca', 'Jutiapa'),
 (2205, 'Asunción Mita', 'Jutiapa'),
 (2206, 'Yupiltepeque', 'Jutiapa'),
 (2207, 'Atescatempa', 'Jutiapa'),
 (2208, 'Jerez', 'Jutiapa'),
 (2209, 'El Adelanto', 'Jutiapa'),
 (2210, 'Zapotitlán', 'Jutiapa'),
 (2211, 'Comapa', 'Jutiapa'),
 (2212, 'Jalpatagua', 'Jutiapa'),
 (2213, 'Conguaco', 'Jutiapa'),
 (2214, 'Moyuta', 'Jutiapa'),
 (2215, 'Pasaco', 'Jutiapa'),
 (2216, 'San José Acatempa', 'Jutiapa'),
 (2217, 'Quesada', 'Jutiapa')]


def buscar_municipio(nombre: str) -> pd.DataFrame:
    """Devuelve codigo, municipio y departamento. Usa el departamento para resolver homónimos."""
    if not isinstance(nombre, str) or not nombre.strip():
        raise ValueError("Escriba el nombre de un municipio.")

    tabla = pd.DataFrame(_MUNICIPIOS, columns=["codigo", "municipio", "departamento"])
    terminos = _normalizar(nombre).split()
    nombres = tabla["municipio"].map(_normalizar)
    coincide = nombres.map(lambda valor: all(t in valor for t in terminos))
    return tabla.loc[coincide].sort_values(
        ["municipio", "departamento"]
    ).reset_index(drop=True)
