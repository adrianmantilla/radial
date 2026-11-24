"""Búsqueda de acciones para el buscador del menú (sin Maya ni Qt).

Una acción es un diccionario con:

- ``texto``: lo que se lee («Center Pivot»).
- ``nombre``: el comando de Maya o el origen («CenterPivot»).
- ``categoria``: dónde está en Maya («Modify», «Estante Poly»).
- ``descripcion``: la ayuda del comando (también se busca en ella).
- ``boton``: el botón de radial que se ejecuta.
"""

import re
import unicodedata

MAX_RESULTADOS = 7
MAX_RECIENTES = 6

_CAMELLO = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def sin_acentos(texto):
    """Minúsculas y sin tildes, para comparar."""
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def texto_de_comando(nombre):
    """«CenterPivot» -> «Center Pivot»; «UVEditor» -> «UV Editor»."""
    return _CAMELLO.sub(" ", nombre).replace("_", " ").strip()


def categoria_legible(categoria):
    """«Menu items.Modify.Pivot» -> «Modify › Pivot»."""
    partes = [p for p in (categoria or "").split(".") if p]
    if partes and partes[0].lower() in ("menu items", "other items"):
        partes = partes[1:]
    return " › ".join(partes)


def accion_de_comando(nombre, categoria="", descripcion=""):
    return {
        "texto": texto_de_comando(nombre),
        "nombre": nombre,
        "categoria": categoria_legible(categoria),
        "descripcion": descripcion or "",
        "boton": {"texto": texto_de_comando(nombre)[:40], "detalle": "", "icono": "", "tipo": "comando",
                  "accion": nombre},
    }


def accion_de_estante(estante, boton):
    return {
        "texto": boton.get("texto", ""),
        "nombre": estante,
        "categoria": estante,
        "descripcion": boton.get("descripcion", ""),
        "boton": {k: boton.get(k, "") for k in ("texto", "detalle", "icono", "tipo", "accion")},
    }


def clave(accion):
    """Identifica una acción para la lista de recientes."""
    boton = accion["boton"]
    return "{}|{}".format(boton.get("tipo", ""), boton.get("accion", ""))


def _puntos(accion, palabras):
    """Menos es mejor. None si alguna palabra no está."""
    texto = sin_acentos(accion["texto"])
    nombre = sin_acentos(accion["nombre"])
    resto = sin_acentos(accion["categoria"] + " " + accion["descripcion"])
    palabras_texto = texto.split()
    total = 0
    for palabra in palabras:
        if texto.startswith(palabra):
            total += 0
        elif any(p.startswith(palabra) for p in palabras_texto):
            total += 1
        elif palabra in texto or palabra in nombre:
            total += 3
        elif palabra in resto:
            total += 6
        else:
            return None
    return total


def buscar(acciones, consulta, recientes=(), limite=MAX_RESULTADOS):
    """Las acciones que coinciden con ``consulta``, las mejores primero.

    Todas las palabras de la consulta tienen que aparecer, en cualquier orden.
    Las usadas hace poco suben un poco.
    """
    palabras = sin_acentos(consulta).split()
    if not palabras:
        return []
    recientes = list(recientes)
    encontradas = []
    vistas = set()
    for orden, accion in enumerate(acciones):
        puntos = _puntos(accion, palabras)
        if puntos is None:
            continue
        k = clave(accion)
        if k in vistas:
            continue
        vistas.add(k)
        if k in recientes:
            puntos -= 2
        encontradas.append((puntos, len(accion["texto"]), orden, accion))
    encontradas.sort(key=lambda e: e[:3])
    return [e[3] for e in encontradas[:limite]]


def anadir_reciente(recientes, accion, limite=MAX_RECIENTES):
    """Pone ``accion`` la primera de ``recientes`` (lista de acciones) sin repetirla."""
    k = clave(accion)
    resto = [a for a in recientes if isinstance(a, dict) and "boton" in a and clave(a) != k]
    guardada = {c: accion.get(c, "") for c in ("texto", "nombre", "categoria", "descripcion")}
    guardada["boton"] = dict(accion["boton"])
    return [guardada] + resto[:limite - 1]


def partes_resaltadas(texto, consulta):
    """Divide ``texto`` en trozos (trozo, coincide) para resaltar lo buscado."""
    palabras = [p for p in sin_acentos(consulta).split() if p]
    comparable = sin_acentos(texto)
    marcas = [False] * len(texto)
    if len(comparable) == len(texto):
        for palabra in palabras:
            inicio = comparable.find(palabra)
            if inicio >= 0:
                for i in range(inicio, inicio + len(palabra)):
                    marcas[i] = True
    trozos = []
    for letra, marca in zip(texto, marcas):
        if trozos and trozos[-1][1] == marca:
            trozos[-1][0] += letra
        else:
            trozos.append([letra, marca])
    return [(t, m) for t, m in trozos]
