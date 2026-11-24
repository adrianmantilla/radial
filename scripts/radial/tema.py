"""Tema del plugin: oscuro (el de siempre) o claro, y un color de acento opcional.

Los colores son objetos ``QColor`` compartidos por los menús, el buscador y la
tarjeta de ayuda. ``aplicar()`` los cambia en su sitio, así todo el plugin usa el
tema nuevo la próxima vez que se dibuje (las ventanas ya creadas se rehacen).

``normalizar_tema``, ``normalizar_acento`` y ``texto_sobre`` no dependen de Qt.
"""

import importlib
import re
import sys

TEMAS = ("oscuro", "claro")

# Colores de acento que se ofrecen en Ajustes ("" = el del tema: blanco en el oscuro, grafito en el claro)
ACENTOS = (("", "acento_tema"), ("#4c8dff", "acento_azul"), ("#36c28a", "acento_verde"),
           ("#ff9f43", "acento_naranja"), ("#ff6b9a", "acento_rosa"), ("#a78bfa", "acento_morado"))

_OSCURO = {
    "dibujo.COLOR_PUNTO": (16, 17, 19, 178),
    "dibujo.COLOR_FONDO": (16, 17, 19, 158),
    "dibujo.COLOR_ABIERTO": (244, 244, 244, 255),
    "dibujo.COLOR_BORDE": (255, 255, 255, 72),
    "dibujo.COLOR_BORDE_FONDO": (255, 255, 255, 36),
    "dibujo.COLOR_LINEA": (255, 255, 255, 46),
    "dibujo.COLOR_CENTRO": (16, 17, 19, 170),
    "dibujo.COLOR_AGARRE": (255, 255, 255, 95),
    "dibujo.COLOR_AGARRE_SOBRE": (255, 255, 255, 200),
    "dibujo.COLOR_TEXTO": (242, 242, 242, 255),
    "dibujo.COLOR_DETALLE": (196, 196, 196, 255),
    "dibujo.COLOR_SOMBRA": (0, 0, 0, 150),
    "dibujo.COLOR_INICIAL": (236, 236, 236, 255),
    "dibujo.COLOR_INICIAL_ABIERTO": (20, 20, 20, 255),
    "dibujo.COLOR_TARJETA": (22, 23, 26, 236),
    "buscador.COLOR_CAPSULA": (16, 17, 19, 205),
    "buscador.COLOR_LISTA": (22, 23, 26, 238),
    "buscador.COLOR_BORDE_ACTIVO": (255, 255, 255, 110),
    "buscador.COLOR_ELEGIDO": (244, 244, 244, 255),
    "buscador.COLOR_TEXTO_ELEGIDO": (20, 20, 20, 255),
    "buscador.COLOR_DETALLE_ELEGIDO": (90, 90, 90, 255),
    "buscador.COLOR_PISTA": (150, 154, 160, 255),
    "buscador.COLOR_CIRCULO": (255, 255, 255, 22),
}

_CLARO = dict(_OSCURO, **{
    "dibujo.COLOR_PUNTO": (248, 248, 250, 215),
    "dibujo.COLOR_FONDO": (246, 246, 248, 222),
    "dibujo.COLOR_ABIERTO": (30, 31, 35, 255),
    "dibujo.COLOR_BORDE": (0, 0, 0, 60),
    "dibujo.COLOR_BORDE_FONDO": (0, 0, 0, 38),
    "dibujo.COLOR_LINEA": (0, 0, 0, 40),
    "dibujo.COLOR_CENTRO": (248, 248, 250, 215),
    "dibujo.COLOR_AGARRE": (0, 0, 0, 90),
    "dibujo.COLOR_AGARRE_SOBRE": (0, 0, 0, 190),
    "dibujo.COLOR_TEXTO": (24, 24, 27, 255),
    "dibujo.COLOR_DETALLE": (78, 80, 86, 255),
    "dibujo.COLOR_SOMBRA": (255, 255, 255, 170),
    "dibujo.COLOR_INICIAL": (36, 36, 40, 255),
    "dibujo.COLOR_INICIAL_ABIERTO": (244, 244, 244, 255),
    "dibujo.COLOR_TARJETA": (250, 250, 251, 242),
    "buscador.COLOR_CAPSULA": (248, 248, 250, 228),
    "buscador.COLOR_LISTA": (250, 250, 251, 244),
    "buscador.COLOR_BORDE_ACTIVO": (0, 0, 0, 110),
    "buscador.COLOR_ELEGIDO": (222, 224, 229, 255),
    "buscador.COLOR_TEXTO_ELEGIDO": (20, 20, 20, 255),
    "buscador.COLOR_DETALLE_ELEGIDO": (80, 82, 88, 255),
    "buscador.COLOR_PISTA": (112, 116, 122, 255),
    "buscador.COLOR_CIRCULO": (44, 45, 50, 235),  # los iconos claros de la lista se ven sobre un círculo oscuro
})

# Iconos de línea: sobre el botón en reposo y sobre el botón abierto (o el acento)
_ICONOS = {"oscuro": ("#ececec", "#141414"), "claro": ("#1c1c1f", "#f4f4f4")}

_actual = {"tema": "oscuro", "acento": ""}


def normalizar_tema(valor):
    return valor if valor in TEMAS else TEMAS[0]


def normalizar_acento(valor):
    """«#4C8DFF» -> «#4c8dff»; lo que no es un color, ""."""
    if isinstance(valor, str) and re.match(r"^#[0-9a-fA-F]{6}$", valor.strip()):
        return valor.strip().lower()
    return ""


def _rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def texto_sobre(color):
    """Color de texto o icono que se lee sobre ``color`` («#rrggbb»): casi negro o casi blanco."""
    r, g, b = _rgb(color)
    luz = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#141414" if luz > 150 else "#f4f4f4"


def actual():
    return dict(_actual)


def aplicar(tema="oscuro", acento=""):
    """Pone el tema y el acento en los colores compartidos. Devuelve True si cambió algo."""
    from radial.qt import QtGui
    tema, acento = normalizar_tema(tema), normalizar_acento(acento)
    cambia = (tema, acento) != (_actual["tema"], _actual["acento"])
    paleta = dict(_CLARO if tema == "claro" else _OSCURO)
    reposo, abierto = _ICONOS[tema]
    if acento:
        r, g, b = _rgb(acento)
        sobre = texto_sobre(acento)
        paleta["dibujo.COLOR_ABIERTO"] = (r, g, b, 255)
        paleta["dibujo.COLOR_INICIAL_ABIERTO"] = _rgb(sobre) + (255,)
        paleta["buscador.COLOR_BORDE_ACTIVO"] = (r, g, b, 200)
        paleta["buscador.COLOR_ELEGIDO"] = (r, g, b, 255)
        paleta["buscador.COLOR_TEXTO_ELEGIDO"] = _rgb(sobre) + (255,)
        paleta["buscador.COLOR_DETALLE_ELEGIDO"] = _rgb(sobre) + (175,)
        abierto = sobre
    for nombre, rgba in paleta.items():
        modulo, constante = nombre.split(".")
        color = getattr(importlib.import_module("radial." + modulo), constante)
        if isinstance(color, QtGui.QColor):
            color.setRgb(*rgba)
    # Los colores de los iconos son textos: se cambian en cada módulo que los usa
    for modulo in list(sys.modules.values()):
        if getattr(modulo, "__name__", "").startswith("radial."):
            for constante, valor in (("COLOR_ICONO_CLARO", reposo), ("COLOR_ICONO_OSCURO", abierto)):
                if isinstance(getattr(modulo, constante, None), str):
                    setattr(modulo, constante, valor)
    _actual.update(tema=tema, acento=acento)
    return cambia
