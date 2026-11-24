"""Textos de la interfaz, separados del código para poder traducirlos.

Cada idioma es un archivo JSON en esta carpeta (``es.json``, ``en.json``...).
Si falta una clave en el idioma elegido, se usa el español.
El idioma se elige en Ajustes › Aspecto (o con la variable de entorno ``RADIAL_IDIOMA``).
"""

import json
import os

_CARPETA = os.path.dirname(os.path.abspath(__file__))
IDIOMA_BASE = "es"
_cache = {}
_idioma = os.environ.get("RADIAL_IDIOMA", IDIOMA_BASE)


def _cargar(idioma):
    if idioma not in _cache:
        ruta = os.path.join(_CARPETA, idioma + ".json")
        try:
            with open(ruta, encoding="utf-8") as f:
                _cache[idioma] = json.load(f)
        except (OSError, ValueError):
            _cache[idioma] = {}
    return _cache[idioma]


def usar_idioma(idioma):
    global _idioma
    _idioma = idioma or os.environ.get("RADIAL_IDIOMA", IDIOMA_BASE)


def idioma():
    return _idioma


def idiomas():
    """Los idiomas que tienen archivo en esta carpeta: lista de (código, nombre en ese idioma)."""
    resultado = []
    for archivo in sorted(os.listdir(_CARPETA)):
        codigo, extension = os.path.splitext(archivo)
        if extension == ".json" and codigo.isalpha():
            resultado.append((codigo, _cargar(codigo).get("idioma_nombre", codigo)))
    return resultado


def claves(idioma=IDIOMA_BASE):
    return set(_cargar(idioma))


def t(clave, **valores):
    """Devuelve el texto de ``clave`` en el idioma activo, con ``valores`` sustituidos."""
    texto = _cargar(_idioma).get(clave) or _cargar(IDIOMA_BASE).get(clave) or clave
    try:
        return texto.format(**valores)
    except (KeyError, IndexError):
        return texto


_sinonimos = {}


def sinonimos(idioma=None):
    """Nombres y ayudas de las órdenes de Maya en el idioma activo.

    ``{"PolyExtrude": {"es": "Extruir", "ayuda": "Saca caras..."}}``. Están en
    ``sinonimos_<idioma>.json``; se pueden añadir más órdenes sin tocar código.
    """
    idioma = idioma or _idioma
    if idioma not in _sinonimos:
        ruta = os.path.join(_CARPETA, "sinonimos_{}.json".format(idioma))
        try:
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)
        except (OSError, ValueError):
            datos = {}
        _sinonimos[idioma] = {k: v for k, v in datos.items() if isinstance(v, dict)}
    return _sinonimos[idioma]


_glosarios = {}


def glosario(idioma=None):
    """Palabras del idioma del alumno con su equivalente en inglés, para buscar órdenes de Maya.

    ``{"extruir": "extrude", "seleccionar": "select"}`` (claves sin tildes, en minúsculas).
    Está en ``glosario_<idioma>.json``.
    """
    idioma = idioma or _idioma
    if idioma not in _glosarios:
        ruta = os.path.join(_CARPETA, "glosario_{}.json".format(idioma))
        try:
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)
        except (OSError, ValueError):
            datos = {}
        _glosarios[idioma] = {k: v for k, v in datos.items() if isinstance(k, str) and isinstance(v, str)}
    return _glosarios[idioma]
