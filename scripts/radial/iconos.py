"""Iconos de línea del menú radial (24 x 24, trazo sin relleno).

Un botón puede usar uno de estos iconos por su nombre, un icono de Maya
(por ejemplo ``:/polyCube.png``) o la ruta de un archivo de imagen. Si no
tiene icono, ``de_boton`` elige uno del mismo estilo según su acción
(``iconos_acciones.py``) y, si no hay ninguno que encaje, se dibuja la inicial.
"""

import os

from radial import iconos_acciones

TRAZOS = {
    "duplicar": "M8.5 8.5h11v11h-11z M5 15.5V4.5h11",
    "pivote": "M12 3v5 M12 16v5 M3 12h5 M16 12h5 M9.5 12a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0 -5 0",
    "congelar": "M12 3v18 M4.2 7.5l15.6 9 M4.2 16.5l15.6-9 M9.5 4.5L12 7l2.5-2.5 M9.5 19.5L12 17l2.5 2.5",
    "historial": "M4 12a8 8 0 1 0 2.4-5.7 M4 4v4h4 M12 8v4l3 2",
    "hypershade": "M4 12a8 8 0 1 0 16 0a8 8 0 1 0 -16 0 M4.5 13.5c4 2 11 2 15 0 M12 4c-3 3-3 13 0 16",
    "render": "M3 8h18v11H3z M8 8l1.5-3h5L16 8 M9 13.5a3 3 0 1 0 6 0a3 3 0 1 0 -6 0",
    "cubo": "M12 3l8 4.5v9L12 21l-8-4.5v-9z M4 7.5l8 4.5 8-4.5 M12 12v9",
    "mover": "M12 3v18 M3 12h18 M9 6l3-3 3 3 M9 18l3 3 3-3 M6 9l-3 3 3 3 M18 9l3 3-3 3",
    "rotar": "M20 12a8 8 0 1 1-2.4-5.7 M20 4v4h-4",
    "escalar": "M4 20h7v-7H4z M11 13l9-9 M14 4h6v6",
    "camara": "M3 7h13v10H3z M16 10l5-3v10l-5-3",
    "luz": "M9 18h6 M10 21h4 M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z",
    "uv": "M4 4h16v16H4z M4 12h16 M12 4v16",
    "llave": "M3 12h10 M5 12v4 M8 12v3 M13 12a4 4 0 1 0 8 0a4 4 0 1 0 -8 0",
    "codigo": "M8 7l-5 5 5 5 M16 7l5 5-5 5 M14 4l-4 16",
    "grafica": "M3 20h18 M3 4v16 M5 17c4 0 5-10 8.5-10S17 13 21 13",
    "fotogramas": "M4 6h16v12H4z M8 6v12 M12 6v12 M16 6v12",
    "play": "M7 5l12 7-12 7z",
    "inicio": "M6 5v14 M18 5l-9 7 9 7z",
    "hornear": "M5 10h14v9H5z M5 14h14 M9 4.5v3 M12 4v3.5 M15 4.5v3",
    "engranaje": "M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6z M12 2.5v3 M12 18.5v3 M2.5 12h3 M18.5 12h3 M5.3 5.3l2.1 2.1 M16.6 16.6l2.1 2.1 M5.3 18.7l2.1-2.1 M16.6 7.4l2.1-2.1",
    "cielo": "M3 16a9 9 0 0 1 18 0z M12 7V4 M5.6 9.6L3.5 7.5 M18.4 9.6l2.1-2.1",
    "plano": "M3 15l9-5 9 5-9 5z M12 4v6",
    "desplegar": "M4 4h7v7H4z M13 13h7v7h-7z M11 7.5h5v5.5",
    "organizar": "M4 4h7v7H4z M13 4h7v4h-7z M13 10h7v10h-7z M4 13h7v7H4z",
    "ojo": "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z M9 12a3 3 0 1 0 6 0a3 3 0 1 0 -6 0",
    "estrella": "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z",
    "malla": "M4 4h16v16H4z M4 10h16 M4 16h16 M10 4v16 M16 4v16",
    "lapiz": "M4 20l1-5L16 4l4 4L9 19z M14 6l4 4",
    "carpeta": "M3 6h6l2 2h10v11H3z",
    "papelera": "M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13",
    "rayo": "M13 3L5 13.5h6L10 21l8-10.5h-6z",
    "estante": "M3 19h18 M5 19V6h4v13 M10 19V9h4v10 M15 19l2.5-11 3.5.8-2.3 10.2",
    "lupa": "M4.5 10.5a6 6 0 1 0 12 0a6 6 0 1 0 -12 0 M15 15l5 5",
}

# Los iconos de las acciones de Maya (extruir, biselar, luces, claves...)
for _nombre, _trazo in iconos_acciones.TRAZOS_ACCIONES.items():
    TRAZOS.setdefault(_nombre, _trazo)

_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="{trazo}"/></svg>')


def svg(nombre, color="#141414"):
    """SVG del icono de línea ``nombre`` en bytes, o None si no existe."""
    trazo = TRAZOS.get(nombre)
    if trazo is None:
        return None
    return _SVG.format(color=color, trazo=trazo).encode("utf-8")


def es_imagen(icono):
    """True si ``icono`` apunta a una imagen (recurso de Maya o archivo)."""
    return bool(icono) and (icono.startswith(":") or os.path.isfile(icono))


MODOS = ("propios", "maya")

# Qué iconos automáticos se usan: los de línea del plugin («propios», por defecto) o los de Maya a color.
# ``icono_maya(comando)`` da el icono de Maya de un comando (":/polyExtrude.png") o ""; lo pone el plugin.
_preferencia = {"modo": "propios", "icono_maya": None}


def usar_iconos(modo, icono_maya=None):
    """Elige los iconos automáticos: «propios» (los del plugin) o «maya» (los de Maya, si los tiene)."""
    _preferencia["modo"] = modo if modo in MODOS else MODOS[0]
    if icono_maya is not None:
        _preferencia["icono_maya"] = icono_maya


def modo():
    return _preferencia["modo"]


def _de_maya(boton):
    buscar = _preferencia["icono_maya"]
    if _preferencia["modo"] != "maya" or buscar is None or boton.get("tipo") != "comando":
        return ""
    try:
        return buscar((boton.get("accion") or "").strip()) or ""
    except Exception:  # sin Maya, el icono del plugin
        return ""


def de_boton(boton, categoria=""):
    """El icono que se dibuja en ``boton``: el suyo o, si no tiene, uno del mismo estilo.

    Los comandos de Maya sin icono propio usan el de su acción (``"PolyExtrude"``
    -> ``"extruir"``) o, si no se conoce, el genérico ``"orden"``. Con ``usar_iconos("maya")``,
    primero el icono de Maya del comando, si lo tiene. Los botones de
    Python o MEL usan el del comando que llaman, si se reconoce. Devuelve "" si
    no hay icono (entonces se dibuja la inicial del texto).
    """
    if not boton:
        return ""
    icono = boton.get("icono", "") or ""
    if icono:
        return icono
    if boton.get("tipo") == "carpeta":
        return "carpeta"
    icono = _de_maya(boton) or iconos_acciones.icono_de_boton(boton, categoria)
    if not icono and boton.get("tipo") == "comando" and (boton.get("accion") or "").strip():
        icono = "orden"
    return icono


def de_imagen_maya(boton):
    """Para botones traídos de un estante: el icono propio que sustituye a su imagen de Maya, o "".

    Con los iconos de Maya elegidos, "" (el botón se queda con su imagen del estante).
    """
    if _preferencia["modo"] == "maya":
        return ""
    return iconos_acciones.icono_de_boton(dict(boton, icono=""))
