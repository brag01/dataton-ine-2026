"""Demostración del IPC. Ejecutar con el entorno del proyecto."""

from pathlib import Path

import ine_gt as ine


def main() -> None:
    recurso = ine.buscar_serie("ipc").recurso.item()
    captura = Path(__file__).resolve().parents[1] / "outputs" / f"demo_ipc_{recurso}.txt"
    with ine.INEClient(timeout=5) as cliente:
        try:
            tabla = cliente.vista_previa(recurso, filas=2)
        except ine.INEAPIError as error:
            print(f"Consulta en vivo fallida: {error}")
            if captura.is_file():
                print("ÚLTIMA CAPTURA GUARDADA")
                print(captura.read_text(encoding="utf-8"))
            else:
                print("CATÁLOGO LOCAL | Series disponibles en esta versión de la biblioteca")
                print(cliente.catalogo()[["nombre", "ejemplo"]].to_string(index=False))
            return

    contenido = (f"INE Guatemala | {tabla.attrs['fecha_consulta_utc']} | Recurso {recurso}\n"
                 + tabla.to_string(index=False))
    print("CONSULTA EN VIVO")
    print(contenido)
    captura.parent.mkdir(exist_ok=True)
    temporal = captura.with_suffix(".tmp")
    temporal.write_text(contenido, encoding="utf-8")
    temporal.replace(captura)


if __name__ == "__main__":
    main()
