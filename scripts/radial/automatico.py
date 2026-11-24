"""Radial automático: qué radial toca según el workspace de Maya y el modo de selección.

Las reglas son ``{"ws:<workspace>": identificador, "sel:<modo>": identificador}``.
La del modo de selección gana a la del workspace. No depende de Maya: el
contexto lo lee ``interfaz_maya``.
"""

MODOS = ("objeto", "vertices", "aristas", "caras", "uv")


def elegir(reglas, workspace, modo):
    """El identificador del radial que toca, o None si ninguna regla aplica."""
    reglas = reglas or {}
    if modo and reglas.get("sel:" + modo):
        return reglas["sel:" + modo]
    if workspace and reglas.get("ws:" + workspace):
        return reglas["ws:" + workspace]
    return None


def contexto_maya():
    """(workspace, modo de selección) actuales en Maya. Valores None si no se pueden leer."""
    from maya import cmds
    try:
        workspace = cmds.workspaceLayoutManager(query=True, current=True)
    except (RuntimeError, TypeError):
        workspace = None
    modo = None
    try:
        if cmds.selectMode(query=True, object=True):
            modo = "objeto"
        elif cmds.selectType(query=True, polymeshFace=True):
            modo = "caras"
        elif cmds.selectType(query=True, polymeshEdge=True):
            modo = "aristas"
        elif cmds.selectType(query=True, polymeshVertex=True):
            modo = "vertices"
        elif cmds.selectType(query=True, polymeshUV=True):
            modo = "uv"
    except (RuntimeError, TypeError):
        pass
    return workspace, modo


def workspaces_maya():
    from maya import cmds
    try:
        return list(cmds.workspaceLayoutManager(query=True, listLayouts=True) or [])
    except (RuntimeError, TypeError):
        return []
