"""Paquete de clase: el menú, la pill extra y las opciones del profesor en un solo archivo.

El profesor lo exporta desde el menú Radial («Exportar paquete de clase…»). Hay dos
formas de usarlo:

- El alumno lo importa («Importar paquete de clase…»): los radiales pasan a ser suyos y
  las opciones se aplican, pero puede cambiarlas después (por ejemplo, en casa).
- El profesor lo deja en la carpeta de clase con las opciones fijadas: mientras el alumno
  use esa carpeta, esas opciones mandan y salen bloqueadas en Ajustes. Sus propias
  opciones no se pierden: vuelven al quitar la carpeta de clase.

No depende de Maya.
"""

import json
import os

from radial import radiales as rd

EXTENSION = ".radialclase"
FORMATO = 1

# Opciones que viajan en el paquete (y que el profesor puede fijar)
OPCIONES = ("forma", "pill_vertical", "ventana_ms", "buscador", "carpetas", "automatico", "aprendizaje")


class PaqueteNoValido(ValueError):
    pass


def crear(nombre, menu, ajustes, extra=None, extra_activa=False, fijar=False):
    """El paquete (un diccionario) con el radial ``menu``, la pill extra y las opciones de ``ajustes``."""
    opciones = {clave: getattr(ajustes, clave) for clave in OPCIONES}
    return {
        "paquete_radial": FORMATO,
        "nombre": (nombre or "").strip() or rd.normalizar(menu)["nombre"],
        "menu": rd.normalizar(menu),
        "extra": rd.normalizar(extra) if extra is not None else None,
        "extra_activa": bool(extra_activa and extra is not None),
        "opciones": opciones,
        "fijas": list(OPCIONES) if fijar else [],
    }


def normalizar(datos):
    if not isinstance(datos, dict) or "paquete_radial" not in datos:
        raise PaqueteNoValido("no es un paquete de clase de Radial")
    if not isinstance(datos["paquete_radial"], int) or datos["paquete_radial"] > FORMATO:
        raise PaqueteNoValido("formato más nuevo que esta versión del plugin")
    try:
        menu = rd.normalizar(datos.get("menu"))
        extra = rd.normalizar(datos["extra"]) if datos.get("extra") is not None else None
    except rd.RadialNoValido as error:
        raise PaqueteNoValido(str(error))
    opciones = datos.get("opciones") if isinstance(datos.get("opciones"), dict) else {}
    opciones = {k: v for k, v in opciones.items() if k in OPCIONES}
    fijas = datos.get("fijas") if isinstance(datos.get("fijas"), list) else []
    nombre = datos.get("nombre") if isinstance(datos.get("nombre"), str) else ""
    return {
        "paquete_radial": FORMATO,
        "nombre": nombre.strip() or menu["nombre"],
        "menu": menu,
        "extra": extra,
        "extra_activa": bool(datos.get("extra_activa")) and extra is not None,
        "opciones": opciones,
        "fijas": [k for k in fijas if k in opciones],
    }


def leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError) as error:
        raise PaqueteNoValido(str(error))
    return normalizar(datos)


def escribir(paquete, ruta):
    if not ruta.endswith(EXTENSION):
        ruta += EXTENSION
    paquete = normalizar(paquete)
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    temporal = ruta + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(paquete, f, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta)
    return ruta


def fijadas_de_carpeta(carpeta):
    """``{opción: valor}`` que fija el profesor con los paquetes de la carpeta de clase.

    Si hay varios paquetes, manda el primero por orden alfabético en cada opción.
    """
    if not carpeta or not os.path.isdir(carpeta):
        return {}
    resultado = {}
    for archivo in sorted(os.listdir(carpeta)):
        if not archivo.endswith(EXTENSION):
            continue
        try:
            paquete = leer(os.path.join(carpeta, archivo))
        except PaqueteNoValido:
            continue
        for clave in paquete["fijas"]:
            resultado.setdefault(clave, paquete["opciones"][clave])
    return resultado
