"""Lo que el configurador necesita saber de Maya: comandos, estantes e iconos.

El configurador recibe un objeto con estos métodos; en las pruebas se usa uno
falso, así las ventanas se pueden probar sin Maya.
"""

import os

from maya import cmds, mel


class FuentesMaya(object):
    def __init__(self):
        self._comandos = None

    def comandos(self):
        """Lista de (nombre, categoría, descripción) de los comandos del Editor de atajos."""
        if self._comandos is None:
            resultado = []
            for nombre in cmds.runTimeCommand(query=True, commandArray=True) or []:
                try:
                    categoria = cmds.runTimeCommand(nombre, query=True, category=True) or ""
                    descripcion = cmds.runTimeCommand(nombre, query=True, annotation=True) or ""
                except RuntimeError:
                    continue
                resultado.append((nombre, categoria, descripcion))
            resultado.sort(key=lambda c: c[0].lower())
            self._comandos = resultado
        return self._comandos

    def atajos(self):
        """``{comando: "Ctrl+E"}`` con los atajos de teclado del juego de atajos actual."""
        resultado = {}
        try:
            total = cmds.assignCommand(query=True, numElements=True) or 0
        except RuntimeError:
            return resultado
        for i in range(1, total + 1):
            try:
                nombre = cmds.assignCommand(i, query=True, name=True) or ""
                tecla = cmds.assignCommand(i, query=True, keyString=True)
            except RuntimeError:
                continue
            texto = _texto_atajo(tecla)
            if not texto or not nombre:
                continue
            comando = nombre[:-len("NameCommand")] if nombre.endswith("NameCommand") else nombre
            resultado.setdefault(comando, texto)
        return resultado

    def estantes(self):
        """Lista de (nombre del estante, [botones]) con cada botón como diccionario de radial."""
        try:
            raiz = mel.eval("$radialTmp = $gShelfTopLevel")
            nombres = cmds.shelfTabLayout(raiz, query=True, childArray=True) or []
        except RuntimeError:
            return []
        resultado = []
        for estante in nombres:
            botones = []
            for hijo in cmds.shelfLayout(estante, query=True, childArray=True) or []:
                if cmds.objectTypeUI(hijo) != "shelfButton":
                    continue
                boton = self._boton_estante(hijo)
                if boton:
                    botones.append(boton)
            if botones:
                resultado.append((estante, botones))
        return resultado

    @staticmethod
    def _boton_estante(nombre):
        orden = cmds.shelfButton(nombre, query=True, command=True)
        if not isinstance(orden, str) or not orden.strip():
            return None
        lenguaje = cmds.shelfButton(nombre, query=True, sourceType=True) or "mel"
        etiqueta = (cmds.shelfButton(nombre, query=True, label=True)
                    or cmds.shelfButton(nombre, query=True, imageOverlayLabel=True) or "")
        descripcion = cmds.shelfButton(nombre, query=True, annotation=True) or ""
        imagen = cmds.shelfButton(nombre, query=True, image=True) or ""
        if imagen and not os.path.isfile(imagen) and not imagen.startswith(":"):
            imagen = ":/" + imagen
        texto = etiqueta or descripcion or orden.strip().splitlines()[0]
        return {"texto": texto[:40], "detalle": "", "icono": imagen,
                "tipo": "python" if lenguaje.lower() == "python" else "mel", "accion": orden,
                "descripcion": descripcion}

    def iconos_maya(self, filtro="", limite=400):
        """Rutas de iconos de Maya (``:/nombre.png``) que contienen ``filtro``."""
        patron = "*{}*.png".format(filtro.strip()) if filtro.strip() else "*.png"
        nombres = cmds.resourceManager(nameFilter=patron) or []
        nombres = sorted(n for n in nombres if not n.endswith("_150.png") and not n.endswith("_200.png"))
        return [":/" + n for n in nombres[:limite]]

    def probar(self, boton):
        from radial import acciones
        return acciones.ejecutar(boton)


def _texto_atajo(tecla):
    """``["e", "0", "1", "0", "0"]`` (tecla, alt, ctrl, al soltar, cmd) -> ``"Ctrl+E"``."""
    if isinstance(tecla, str):
        tecla = [tecla]
    if not tecla or not tecla[0] or tecla[0] == "NONE":
        return ""
    banderas = list(tecla[1:]) + ["0"] * 4
    if banderas[2] in ("1", 1, True):  # se lanza al soltar la tecla: no es un atajo normal
        return ""
    partes = []
    if banderas[1] in ("1", 1, True):
        partes.append("Ctrl")
    if banderas[0] in ("1", 1, True):
        partes.append("Alt")
    if banderas[3] in ("1", 1, True):
        partes.append("Cmd")
    letra = tecla[0]
    if len(letra) == 1 and letra.isupper():
        partes.append("Mayús")
    partes.append(letra.upper() if len(letra) == 1 else letra)
    return "+".join(partes)
