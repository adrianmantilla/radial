"""Iconos de línea del menú radial (24 x 24, trazo sin relleno).

Un botón puede usar uno de estos iconos por su nombre, un icono de Maya
(por ejemplo ``:/polyCube.png``) o la ruta de un archivo de imagen. Si no
tiene icono, se dibuja la inicial de su texto.
"""

import os

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
}

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
