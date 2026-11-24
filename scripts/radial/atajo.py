"""Atajo de teclado opcional para mostrar u ocultar el menú (además del doble Tab).

``partes()`` traduce un atajo escrito como en Qt («Ctrl+Alt+R») a lo que pide
el comando ``hotkey`` de Maya. No depende de Maya; ``asignar`` y ``quitar`` sí.

En macOS, Qt llama «Ctrl» a la tecla Cmd y «Meta» a Control; Maya las llama
``commandModifier`` y ``ctrlModifier``.
"""

import sys

NOMBRE_COMANDO = "RadialMostrarOcultarNameCommand"
JUEGO_RADIAL = "Radial"

_TECLAS_ESPECIALES = {"SPACE": "Space", "RETURN": "Return", "ENTER": "Return", "ESC": "Escape",
                      "BACKSPACE": "Backspace", "DEL": "Delete", "DELETE": "Delete", "HOME": "Home",
                      "END": "End", "PGUP": "Page_Up", "PGDOWN": "Page_Down", "UP": "Up", "DOWN": "Down",
                      "LEFT": "Left", "RIGHT": "Right", "INS": "Insert"}


class AtajoNoValido(ValueError):
    pass


def partes(texto, mac=None):
    """«Ctrl+Alt+R» -> {"keyShortcut": "r", "ctrlModifier": True, "altModifier": True, ...}.

    Exige al menos un modificador (Ctrl, Alt o Cmd) para no quitarle a Maya una tecla sola.
    """
    mac = sys.platform == "darwin" if mac is None else mac
    trozos = [p.strip() for p in (texto or "").replace(" ", "").split("+")]
    if len(trozos) < 2 or not trozos[-1]:
        raise AtajoNoValido(texto)
    tecla, modificadores = trozos[-1], {m.upper() for m in trozos[:-1]}
    resultado = {"ctrlModifier": False, "altModifier": False, "commandModifier": False}
    for m in modificadores:
        if m == "CTRL":
            resultado["commandModifier" if mac else "ctrlModifier"] = True
        elif m == "META":
            resultado["ctrlModifier"] = True
        elif m == "ALT":
            resultado["altModifier"] = True
        elif m == "SHIFT":
            pass  # Maya expresa Mayúsculas con la letra en mayúscula
        else:
            raise AtajoNoValido(texto)
    if not any(resultado.values()):
        raise AtajoNoValido(texto)
    if len(tecla) == 1:
        tecla = tecla.upper() if "SHIFT" in modificadores else tecla.lower()
    elif tecla.upper() in _TECLAS_ESPECIALES:
        tecla = _TECLAS_ESPECIALES[tecla.upper()]
    elif not (tecla.upper().startswith("F") and tecla[1:].isdigit()):
        raise AtajoNoValido(texto)
    resultado["keyShortcut"] = tecla
    return resultado


# --- Con Maya -------------------------------------------------------------------

def _juego_editable():
    """El juego de atajos actual; si es el de fábrica (que no se puede cambiar), uno «Radial» copiado de él."""
    from maya import cmds
    actual = cmds.hotkeySet(query=True, current=True)
    if actual != "Maya_Default":
        return actual
    if not cmds.hotkeySet(JUEGO_RADIAL, exists=True):
        cmds.hotkeySet(JUEGO_RADIAL, source="Maya_Default", current=True)
    else:
        cmds.hotkeySet(JUEGO_RADIAL, edit=True, current=True)
    return JUEGO_RADIAL


def ocupado_por(texto):
    """El comando que ya usa ese atajo en Maya, o "" si está libre (o es el nuestro)."""
    from maya import cmds
    p = partes(texto)
    try:
        nombre = cmds.hotkeyCheck(keyString=p["keyShortcut"], ctl=p["ctrlModifier"], alt=p["altModifier"],
                                  cmd=p["commandModifier"]) or ""
    except (RuntimeError, TypeError):
        return ""
    return "" if nombre in ("", NOMBRE_COMANDO, "RadialMostrarOcultar") else nombre


def asignar(texto, comando="RadialMostrarOcultar", anotacion=""):
    """Asigna ``texto`` al comando de Radial. No pisa un atajo de Maya: lanza AtajoNoValido si está ocupado."""
    from maya import cmds
    p = partes(texto)
    ocupado = ocupado_por(texto)
    if ocupado:
        raise AtajoNoValido(ocupado)
    _juego_editable()
    cmds.nameCommand(NOMBRE_COMANDO, annotation=anotacion or comando, command=comando, sourceType="mel")
    cmds.hotkey(name=NOMBRE_COMANDO, **p)


def quitar(texto):
    from maya import cmds
    try:
        p = partes(texto)
    except AtajoNoValido:
        return
    try:
        if cmds.hotkeyCheck(keyString=p["keyShortcut"], ctl=p["ctrlModifier"], alt=p["altModifier"],
                            cmd=p["commandModifier"]) == NOMBRE_COMANDO:
            cmds.hotkey(name="", **p)
    except (RuntimeError, TypeError):
        pass
