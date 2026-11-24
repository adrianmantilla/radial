"""Ejecuta la acción de un botón del radial dentro de Maya."""

import traceback

from radial.i18n import t


def comando_existe(nombre):
    """True si ``nombre`` es un comando de Maya (runTimeCommand o procedimiento MEL)."""
    from maya import cmds, mel
    if not nombre or not nombre.replace("_", "").isalnum():
        return False
    if cmds.runTimeCommand(nombre, exists=True):
        return True
    return mel.eval('exists "{}"'.format(nombre)) == 1


def comando_de_opciones(boton):
    """El comando que abre la ventana de opciones del botón («PolyExtrudeOptions»), o None."""
    if boton.get("tipo") != "comando":
        return None
    accion = boton.get("accion", "")
    if accion.endswith("Options"):
        return None
    candidato = accion + "Options"
    return candidato if comando_existe(candidato) else None


def estado(boton):
    """True o False si el botón dice si está encendido; None si no lo dice o falla."""
    expresion = (boton or {}).get("estado", "")
    if not expresion:
        return None
    from radial import interruptores
    clave = interruptores.clave_de(boton)
    try:
        if clave:
            return bool(interruptores.encendido(clave))
        import __main__
        from maya import cmds
        espacio = dict(__main__.__dict__)
        espacio.setdefault("cmds", cmds)
        return bool(eval(compile(expresion, "<Radial: estado>", "eval"), espacio))
    except Exception:
        return None


def ejecutar(boton, opciones=False):
    """Lanza la acción de ``boton``. Un error se avisa en Maya y no se propaga.

    Con ``opciones`` (Mayúsculas + clic), abre la ventana de opciones del comando si la tiene.
    """
    from maya import cmds, mel

    tipo, accion = boton.get("tipo"), boton.get("accion", "")
    if opciones:
        con_opciones = comando_de_opciones(boton)
        if con_opciones:
            accion = con_opciones
    nombre = " ".join(p for p in (boton.get("texto"), boton.get("detalle")) if p) or accion
    if tipo == "vacio" or not accion.strip():
        return False
    try:
        if tipo == "comando":
            if not comando_existe(accion):
                cmds.warning(t("accion_no_existe", nombre=nombre, comando=accion))
                return False
            mel.eval(accion)
        else:
            # Las líneas propias se deshacen de una vez con Ctrl+Z.
            cmds.undoInfo(openChunk=True, chunkName="Radial: " + nombre)
            try:
                if tipo == "mel":
                    mel.eval(accion)
                elif tipo == "python":
                    import __main__
                    exec(compile(accion, "<Radial: {}>".format(nombre), "exec"), __main__.__dict__)
            finally:
                cmds.undoInfo(closeChunk=True)
        return True
    except Exception as error:
        traceback.print_exc()
        cmds.warning(t("accion_error", nombre=nombre, error=error))
        return False
