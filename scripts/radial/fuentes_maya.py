"""Lo que el configurador necesita saber de Maya: comandos, estantes e iconos.

El configurador recibe un objeto con estos métodos; en las pruebas se usa uno
falso, así las ventanas se pueden probar sin Maya.
"""

import os

from maya import cmds, mel


class FuentesMaya(object):
    def __init__(self):
        self._comandos = None
        self._iconos_comando = {}

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

    def menus(self, profundidad=3):
        """Lista de (ruta, etiqueta, botón) con las órdenes de los menús de la ventana de Maya.

        ``ruta`` es la lista de menús hasta la orden (["Modify", "Pivot"]). Maya crea
        los menús al abrirlos: los que aún están vacíos se crean aquí (lo mismo que hace Maya).
        """
        try:
            principales = cmds.window("MayaWindow", query=True, menuArray=True) or []
        except RuntimeError:
            return []
        resultado = []
        for menu in principales:
            menu = menu if "|" in menu else "MayaWindow|" + menu
            try:
                etiqueta = (cmds.menu(menu, query=True, label=True) or "").replace("&", "")
            except RuntimeError:
                continue
            self._recorrer_menu(menu, [etiqueta], resultado, profundidad, es_menu=True)
        return resultado

    def _recorrer_menu(self, menu, ruta, resultado, profundidad, es_menu=False):
        consulta = cmds.menu if es_menu else cmds.menuItem
        try:
            hijos = consulta(menu, query=True, itemArray=True) or []
            if not hijos:
                construir = consulta(menu, query=True, postMenuCommand=True)
                if isinstance(construir, str) and construir.strip():
                    mel.eval(construir)
                    hijos = consulta(menu, query=True, itemArray=True) or []
        except RuntimeError:
            return
        for hijo in hijos:
            completo = menu + "|" + hijo
            try:
                if cmds.menuItem(completo, query=True, divider=True) or \
                        cmds.menuItem(completo, query=True, optionBox=True):
                    continue
                etiqueta = (cmds.menuItem(completo, query=True, label=True) or "").replace("&", "").strip()
                if not etiqueta:
                    continue
                if cmds.menuItem(completo, query=True, subMenu=True):
                    if profundidad > 1:
                        self._recorrer_menu(completo, ruta + [etiqueta], resultado, profundidad - 1)
                    continue
                boton = self._boton_menu(completo)
            except RuntimeError:
                continue
            if boton:
                resultado.append((list(ruta), etiqueta.rstrip(".…").strip(), boton))

    @staticmethod
    def _boton_menu(item):
        try:
            orden = cmds.menuItem(item, query=True, runTimeCommand=True) or ""
        except (RuntimeError, TypeError):
            orden = ""
        tipo = "comando" if orden else "mel"
        if not orden:
            orden = cmds.menuItem(item, query=True, command=True)
            if not isinstance(orden, str) or not orden.strip():
                return None  # una función de Python: no se puede guardar en un botón
            if (cmds.menuItem(item, query=True, sourceType=True) or "mel").lower() == "python":
                tipo = "python"
        imagen = cmds.menuItem(item, query=True, image=True) or ""
        descripcion = cmds.menuItem(item, query=True, annotation=True) or ""
        if imagen and not os.path.isfile(imagen) and not imagen.startswith(":"):
            imagen = ":/" + imagen
        return {"tipo": tipo, "accion": orden, "icono": imagen, "descripcion": descripcion}

    def scripts(self):
        """Rutas de los .py y .mel de las carpetas de scripts del usuario."""
        from radial import busqueda
        carpetas = []
        for clave in ("userScriptDir", "userAppDir"):
            try:
                carpeta = cmds.internalVar(**{clave: True}) or ""
            except (RuntimeError, TypeError):
                continue
            if clave == "userAppDir":
                carpeta = os.path.join(carpeta, "scripts")
            if carpeta and os.path.isdir(carpeta) and os.path.normpath(carpeta) not in carpetas:
                carpetas.append(os.path.normpath(carpeta))
        rutas = []
        for carpeta in carpetas:
            for archivo in sorted(os.listdir(carpeta)):
                ruta = os.path.join(carpeta, archivo)
                if busqueda.es_script(archivo) and os.path.isfile(ruta):
                    rutas.append(ruta)
        return rutas

    def iconos_maya(self, filtro="", limite=400):
        """Rutas de iconos de Maya (``:/nombre.png``) que contienen ``filtro``."""
        patron = "*{}*.png".format(filtro.strip()) if filtro.strip() else "*.png"
        nombres = cmds.resourceManager(nameFilter=patron) or []
        nombres = sorted(n for n in nombres if not n.endswith("_150.png") and not n.endswith("_200.png"))
        return [":/" + n for n in nombres[:limite]]

    def icono_de_comando(self, nombre):
        """El icono de Maya de la herramienta ``nombre`` (``":/polyBevel.png"``) o "" si no tiene."""
        if nombre in self._iconos_comando:
            return self._iconos_comando[nombre]
        from radial import busqueda
        icono = ""
        try:
            imagen = cmds.runTimeCommand(nombre, query=True, image=True) or ""
        except (RuntimeError, TypeError):
            imagen = ""
        candidatos = ([imagen] if imagen else []) + busqueda.candidatos_icono(nombre)
        for candidato in candidatos:
            if os.path.isabs(candidato) and os.path.isfile(candidato):
                icono = candidato
                break
            nombre_png = candidato.lstrip(":/")
            try:
                if cmds.resourceManager(nameFilter=nombre_png):
                    icono = ":/" + nombre_png
                    break
            except RuntimeError:
                continue
        self._iconos_comando[nombre] = icono
        return icono

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
        from radial.i18n import t
        partes.append(t("tecla_mayus"))
    partes.append(letra.upper() if len(letra) == 1 else letra)
    return "+".join(partes)
