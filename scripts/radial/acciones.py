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


def ejecutar(boton):
    """Lanza la acción de ``boton``. Un error se avisa en Maya y no se propaga."""
    from maya import cmds, mel

    tipo, accion = boton.get("tipo"), boton.get("accion", "")
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
