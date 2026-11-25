"""Run explicitly with harness.py live. All requests use the real INE portal."""
import math

import ine_gt as ine

from test_persona import verificar_cita


def test_catalogo_y_muestra():
    with ine.INEClient() as cliente:
        conjuntos = cliente.buscar_conjuntos("IPC")
        assert not conjuntos.empty
        recurso = ine.buscar_serie("IPC").recurso.item()
        for conjunto in conjuntos.itertuples():
            recursos = cliente.recursos(conjunto.id)
            if not recursos.empty and recurso in recursos.id.values:
                assert recursos.loc[recursos.id == recurso, "datastore_active"].item()
                break
        else:
            raise AssertionError(f"Recurso IPC {recurso} ausente del catálogo consultado")
        muestra = cliente.datos(recurso, max_rows=1)
        assert len(muestra) == 1 and "República" in muestra
        print(f"Catálogo IPC: {len(conjuntos)} conjuntos. Recurso: {recurso}. Muestra: 1 fila.")


def test_ipc_en_portal():
    ipc = ine.cargar_serie("ipc_nacional_mensual", año=2026)
    assert not ipc.empty and ipc.periodo.is_unique
    assert all(math.isfinite(v) and v >= 0 for v in ipc.valor)
    fuente = ine.mostrar_fuente(ipc).iloc[0]
    print(f"IPC: {len(ipc)} meses. {ipc.periodo.iloc[-1]}: {ipc.valor.iloc[-1]} "
          f"{fuente.unidad}. {fuente.fecha_consulta_utc} {fuente.consulta}")


def test_poblacion_en_portal():
    opciones = ine.buscar_municipio("San Pedro Sacatepéquez")
    codigo = int(opciones.loc[opciones.departamento == "San Marcos", "codigo"].item())
    tabla = ine.cargar_serie("poblacion_municipal_anual", año=2026, municipio=codigo)
    assert tabla.periodo.tolist() == [2026] and tabla.valor.item() > 0
    fuente = ine.mostrar_fuente(tabla).iloc[0]
    verificar_cita(fuente, codigo)
    print(f"Municipio {codigo}, 2026: {tabla.valor.item()} {fuente.unidad}. "
          f"{fuente.fecha_consulta_utc} {fuente.consulta}")
