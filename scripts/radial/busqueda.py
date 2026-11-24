"""Búsqueda de acciones para el buscador del menú (sin Maya ni Qt).

Se busca a la vez en inglés (el nombre de Maya) y en español (la traducción).
Además, cada palabra en español se prueba también en inglés con el glosario
(«seleccionar» -> «select»), así se encuentran órdenes que no tienen traducción.

Una acción es un diccionario con:

- ``texto``: lo que se lee («Center Pivot»).
- ``nombre``: el comando de Maya o el origen («CenterPivot»).
- ``categoria``: dónde está en Maya («Modify», «Estante Poly»).
- ``descripcion``: la ayuda del comando en el idioma del alumno si la hay (también se busca en ella).
- ``descripcion_en``: la ayuda original de Maya en inglés cuando ``descripcion`` es la traducida.
- ``traduccion``: su nombre en el idioma del alumno («Centrar pivote»), o "".
- ``atajo``: su atajo de teclado («Ctrl+E»), o "".
- ``menu``: dónde está en los menús de Maya («Modify › Center Pivot»), o "".
- ``etiqueta``: cómo se llama en ese menú si no es igual que ``texto`` (Maya en otro idioma), o "".
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


def accion_de_comando(nombre, categoria="", descripcion="", traduccion="", ayuda="", atajo=""):
    """``ayuda`` (en el idioma del alumno) sustituye a la descripción en inglés de Maya."""
    return {
        "texto": texto_de_comando(nombre),
        "nombre": nombre,
        "categoria": categoria_legible(categoria),
        "descripcion": ayuda or descripcion or "",
        "descripcion_en": descripcion if ayuda else "",
        "traduccion": traduccion or "",
        "atajo": atajo or "",
        "boton": {"texto": texto_de_comando(nombre)[:40], "detalle": "", "icono": "", "tipo": "comando",
                  "accion": nombre},
    }


def accion_de_estante(estante, boton):
    return {
        "texto": boton.get("texto", ""),
        "nombre": estante,
        "categoria": estante,
        "descripcion": boton.get("descripcion", ""),
        "traduccion": "",
        "atajo": "",
        "boton": {k: boton.get(k, "") for k in ("texto", "detalle", "icono", "tipo", "accion")},
    }


_SUFIJOS = ("Options", "Tool", "Context", "Ctx", "Window", "Editor")


def candidatos_icono(nombre):
    """Nombres de icono de Maya que probar para el comando ``nombre``, del más probable al menos.

    «PolyExtrude» -> «polyExtrude.png», «polyExtrudeFacet.png»...; «CenterPivot» -> «centerPivot.png».
    """
    if not nombre:
        return []
    base = nombre
    for sufijo in _SUFIJOS:
        if base.endswith(sufijo) and len(base) > len(sufijo):
            base = base[:-len(sufijo)]
            break
    minuscula = base[:1].lower() + base[1:]
    candidatos = [minuscula, base]
    if base.startswith("Poly"):
        resto = base[4:]
        candidatos += ["poly" + resto, "poly" + resto + "Facet", "poly" + resto + "Edge"]
    elif base.startswith("Create"):
        resto = base[6:]
        candidatos += ["poly" + resto, resto[:1].lower() + resto[1:]]
    vistos = []
    for c in candidatos:
        nombre_png = c + ".png"
        if c and nombre_png not in vistos:
            vistos.append(nombre_png)
    return vistos


def clave(accion):
    """Identifica una acción para la lista de recientes."""
    boton = accion["boton"]
    return "{}|{}".format(boton.get("tipo", ""), boton.get("accion", ""))


def alternativas(palabra, glosario):
    """La palabra y sus equivalentes en inglés según el glosario (también si está a medio escribir)."""
    resultado = [palabra]
    if palabra in glosario:
        resultado.append(sin_acentos(glosario[palabra]))
    elif len(palabra) >= 4:
        for clave in sorted(glosario):
            if clave.startswith(palabra):
                resultado.append(sin_acentos(glosario[clave]))
                if len(resultado) > 3:
                    break
    return [r for i, r in enumerate(resultado) if r and r not in resultado[:i]]


def _punto_palabra(palabra, nombres, palabras_nombres, nombre, resto):
    if any(n.startswith(palabra) for n in nombres if n):
        return 0
    if any(p.startswith(palabra) for p in palabras_nombres):
        return 1
    if any(palabra in n for n in nombres) or palabra in nombre.replace(" ", ""):
        return 3
    if palabra in resto:
        return 6
    return None


def _puntos(accion, palabras, glosario=None):
    """Menos es mejor. None si alguna palabra no está (ni en inglés ni en español)."""
    nombres = [sin_acentos(accion["texto"]), sin_acentos(accion.get("traduccion", "")),
               sin_acentos(accion.get("etiqueta", ""))]
    nombre = sin_acentos(accion["nombre"])
    resto = sin_acentos(" ".join((accion["categoria"], accion.get("menu", ""), accion["descripcion"],
                                  accion.get("descripcion_en", ""))))
    palabras_nombres = [p for n in nombres for p in n.split()]
    total = 0
    for palabra in palabras:
        mejor = None
        for i, alternativa in enumerate(alternativas(palabra, glosario or {})):
            puntos = _punto_palabra(alternativa, nombres, palabras_nombres, nombre, resto)
            if puntos is not None:
                puntos += 1 if i else 0  # lo traducido con el glosario, un poco detrás
                mejor = puntos if mejor is None else min(mejor, puntos)
        if mejor is None:
            return None
        total += mejor
    return total


def buscar(acciones, consulta, recientes=(), limite=MAX_RESULTADOS, glosario=None, favoritos=()):
    """Las acciones que coinciden con ``consulta``, las mejores primero.

    Todas las palabras de la consulta tienen que aparecer, en cualquier orden.
    Las usadas hace poco suben un poco y las favoritas (claves en ``favoritos``), algo más.
    """
    palabras = sin_acentos(consulta).split()
    if not palabras:
        return []
    if glosario is None:
        from radial.i18n import glosario as cargar_glosario
        glosario = cargar_glosario()
    recientes = list(recientes)
    favoritos = set(favoritos)
    encontradas = []
    vistas = set()
    for orden, accion in enumerate(acciones):
        puntos = _puntos(accion, palabras, glosario)
        if puntos is None:
            continue
        k = clave(accion)
        if k in vistas:
            continue
        vistas.add(k)
        if k in recientes:
            puntos -= 2
        if k in favoritos:
            puntos -= 3
        encontradas.append((puntos, len(accion["texto"]), orden, accion))
    encontradas.sort(key=lambda e: e[:3])
    return [e[3] for e in encontradas[:limite]]


def accion_de_menu(ruta, etiqueta, boton):
    """Una orden de los menús de Maya que no es un comando del Editor de atajos."""
    return {
        "texto": etiqueta,
        "nombre": boton.get("accion", "").strip().splitlines()[0][:60] if boton.get("accion", "").strip() else "",
        "categoria": " › ".join(ruta),
        "menu": " › ".join(list(ruta) + [etiqueta]),
        "descripcion": boton.get("descripcion", ""),
        "traduccion": "",
        "atajo": "",
        "boton": {"texto": etiqueta[:40], "detalle": "", "icono": boton.get("icono", ""),
                  "tipo": boton.get("tipo", "mel"), "accion": boton.get("accion", "")},
    }


def unir_menus(acciones, menus):
    """Añade a ``acciones`` lo que hay en los menús de Maya.

    ``menus`` es una lista de ``(ruta, etiqueta, boton)``. Si el menú lanza un comando
    que ya está en ``acciones``, a ese comando se le apunta dónde está («Modify › Center Pivot»)
    y la etiqueta del menú (la que se ve en Maya, también si Maya está en otro idioma).
    Si no, se añade como acción nueva.
    """
    por_nombre = {a["nombre"]: a for a in acciones if a["boton"].get("tipo") == "comando"}
    for ruta, etiqueta, boton in menus:
        if not etiqueta or not boton.get("accion", "").strip():
            continue
        orden = boton["accion"].strip().rstrip(";").strip()
        existente = por_nombre.get(orden)
        if existente is not None:
            if not existente.get("menu"):
                existente["menu"] = " › ".join(list(ruta) + [etiqueta])
                if sin_acentos(etiqueta) != sin_acentos(existente["texto"]):
                    existente["etiqueta"] = etiqueta
            continue
        acciones.append(accion_de_menu(ruta, etiqueta, boton))
    return acciones


_PROPIOS = ("userSetup.py", "userSetup.mel")


def accion_de_script(ruta, categoria):
    """Un script propio (.py o .mel de la carpeta de scripts del usuario) como acción."""
    import os
    archivo = ruta.replace("\\", "/").rsplit("/", 1)[-1]
    nombre, extension = os.path.splitext(archivo)
    if extension.lower() == ".mel":
        tipo, orden = "mel", 'source "{}";'.format(ruta.replace("\\", "/"))
    else:
        tipo, orden = "python", "import runpy\nrunpy.run_path({!r}, run_name=\"__main__\")".format(ruta)
    return {
        "texto": texto_de_comando(nombre),
        "nombre": archivo,
        "categoria": categoria,
        "descripcion": ruta,
        "traduccion": "",
        "atajo": "",
        "boton": {"texto": texto_de_comando(nombre)[:40], "detalle": "", "icono": "", "tipo": tipo,
                  "accion": orden},
    }


def es_script(archivo):
    """True para los .py y .mel que se pueden lanzar como orden (no los internos ni userSetup)."""
    import os
    nombre, extension = os.path.splitext(archivo)
    return (extension.lower() in (".py", ".mel") and archivo not in _PROPIOS
            and not nombre.startswith(("_", ".")))


def es_favorita(favoritos, accion):
    k = clave(accion)
    return any(clave(a) == k for a in favoritos if isinstance(a, dict) and "boton" in a)


def alternar_favorito(favoritos, accion):
    """Quita ``accion`` de ``favoritos`` si estaba; si no, la añade al final."""
    k = clave(accion)
    resto = [a for a in favoritos if isinstance(a, dict) and "boton" in a and clave(a) != k]
    if len(resto) != len([a for a in favoritos if isinstance(a, dict) and "boton" in a]):
        return resto
    return resto + [_guardable(accion)]


def _guardable(accion):
    guardada = {c: accion.get(c, "") for c in ("texto", "nombre", "categoria", "menu", "descripcion",
                                                 "descripcion_en", "traduccion", "atajo")}
    guardada["boton"] = dict(accion["boton"])
    return guardada


def anadir_reciente(recientes, accion, limite=MAX_RECIENTES):
    """Pone ``accion`` la primera de ``recientes`` (lista de acciones) sin repetirla."""
    k = clave(accion)
    resto = [a for a in recientes if isinstance(a, dict) and "boton" in a and clave(a) != k]
    return [_guardable(accion)] + resto[:limite - 1]


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
