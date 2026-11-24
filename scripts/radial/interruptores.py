"""Interruptores: botones que encienden o apagan algo y muestran si está encendido.

Un botón interruptor es un botón de Python con un campo ``estado``:

- ``"radial:<clave>"`` para los que vienen preparados aquí (Wireframe, Rayos X...).
- O una línea de Python que devuelve True o False (para usuarios avanzados),
  por ejemplo ``cmds.snapMode(q=True, grid=True)``.

La lista ``INTERRUPTORES`` no necesita Maya; las funciones sí.
"""

PREFIJO = "radial:"

# clave: (texto, detalle, icono)
INTERRUPTORES = {
    "wireframe": ("Malla", "wireframe", "malla"),
    "xray": ("Rayos X", "", "ojo"),
    "aislar": ("Aislar", "selección", "ojo"),
    "suavizado": ("Suavizado", "vista previa", "cubo"),
    "snap_rejilla": ("Imán", "rejilla", "plano"),
    "snap_vertice": ("Imán", "vértices", "pivote"),
    "rejilla": ("Rejilla", "", "plano"),
    "simetria": ("Simetría", "", "escalar"),
}
ORDEN = ("wireframe", "xray", "aislar", "suavizado", "snap_rejilla", "snap_vertice", "rejilla", "simetria")


def boton(clave):
    """El botón de radial del interruptor ``clave``."""
    texto, detalle, icono = INTERRUPTORES[clave]
    return {"texto": texto, "detalle": detalle, "icono": icono, "tipo": "python",
            "accion": "from radial import interruptores\ninterruptores.alternar({!r})".format(clave),
            "estado": PREFIJO + clave}


def clave_de(boton_radial):
    estado = (boton_radial or {}).get("estado", "")
    if estado.startswith(PREFIJO) and estado[len(PREFIJO):] in INTERRUPTORES:
        return estado[len(PREFIJO):]
    return None


# --- Con Maya -------------------------------------------------------------------

def _panel():
    """El visor 3D con el foco, o el primero visible."""
    from maya import cmds
    panel = cmds.getPanel(withFocus=True)
    if panel and cmds.getPanel(typeOf=panel) == "modelPanel":
        return panel
    for panel in cmds.getPanel(visiblePanels=True) or []:
        if cmds.getPanel(typeOf=panel) == "modelPanel":
            return panel
    return None


def _mallas_seleccionadas():
    from maya import cmds
    return cmds.ls(selection=True, objectsOnly=True, dagObjects=True, type="mesh", noIntermediate=True) or []


def encendido(clave):
    """True o False según el estado de ``clave`` en Maya."""
    from maya import cmds
    panel = _panel()
    if clave == "wireframe":
        return bool(panel) and cmds.modelEditor(panel, query=True, displayAppearance=True) == "wireframe"
    if clave == "xray":
        return bool(panel) and bool(cmds.modelEditor(panel, query=True, xray=True))
    if clave == "aislar":
        return bool(panel) and bool(cmds.isolateSelect(panel, query=True, state=True))
    if clave == "suavizado":
        mallas = _mallas_seleccionadas()
        if not mallas:
            return False
        valor = cmds.displaySmoothness(mallas[0], query=True, polygonObject=True) or [1]
        return valor[0] == 3
    if clave == "snap_rejilla":
        return bool(cmds.snapMode(query=True, grid=True))
    if clave == "snap_vertice":
        return bool(cmds.snapMode(query=True, point=True))
    if clave == "rejilla":
        return bool(cmds.grid(query=True, toggle=True))
    if clave == "simetria":
        return bool(cmds.symmetricModelling(query=True, symmetry=True))
    return False


def alternar(clave):
    """Enciende o apaga ``clave``."""
    from maya import cmds, mel
    nuevo = not encendido(clave)
    panel = _panel()
    if clave == "wireframe" and panel:
        cmds.modelEditor(panel, edit=True, displayAppearance="wireframe" if nuevo else "smoothShaded")
    elif clave == "xray" and panel:
        cmds.modelEditor(panel, edit=True, xray=nuevo)
    elif clave == "aislar" and panel:
        mel.eval('enableIsolateSelect "{}" {}'.format(panel, int(nuevo)))
    elif clave == "suavizado":
        mallas = _mallas_seleccionadas()
        if mallas:
            cmds.displaySmoothness(mallas, polygonObject=3 if nuevo else 1)
    elif clave == "snap_rejilla":
        cmds.snapMode(grid=nuevo)
    elif clave == "snap_vertice":
        cmds.snapMode(point=nuevo)
    elif clave == "rejilla":
        cmds.grid(toggle=nuevo)
    elif clave == "simetria":
        cmds.symmetricModelling(symmetry=nuevo)
    return nuevo
