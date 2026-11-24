"""Soltar en un botón del menú: una acción del buscador, un botón de otro menú o texto.

Si lo que llega es texto (por ejemplo, un botón arrastrado desde un estante de
Maya o unas líneas de código), se convierte en un botón de MEL o de Python.
"""

import json

from radial.qt import posicion_local

MIME = "application/x-radial-boton"


def datos_mime(boton):
    from radial.qt import QtCore
    datos = QtCore.QMimeData()
    datos.setData(MIME, QtCore.QByteArray(json.dumps(boton).encode("utf-8")))
    datos.setText(boton.get("texto", ""))
    return datos


def boton_de_texto(texto):
    """Un botón de radial con ``texto`` como código. Python si lo parece; si no, MEL."""
    codigo = (texto or "").strip()
    if not codigo or len(codigo) > 20000:
        return None
    lineas = [linea.strip() for linea in codigo.splitlines() if linea.strip()]
    if ";" not in codigo and "(" not in codigo:
        return None  # texto suelto («hola»): no parece una orden
    python = any(linea.startswith(("import ", "from ", "def ", "cmds.", "mc.", "pm.")) for linea in lineas) or (
        "cmds." in codigo and not codigo.rstrip().endswith(";"))
    rotulo = lineas[0].split("(")[0].split(" ")[0].rstrip(";")
    if python and "." in rotulo:
        rotulo = rotulo.split(".")[-1]
    return {"texto": rotulo[:20] or "Código", "detalle": "", "icono": "", "tipo": "python" if python else "mel",
            "accion": codigo}


def _texto_de(mime):
    for formato in mime.formats():
        if "maya" in formato.lower():
            try:
                texto = bytes(mime.data(formato)).decode("utf-8").strip("\x00").strip()
            except UnicodeDecodeError:
                continue
            if texto:
                return texto
    return mime.text() if mime.hasText() else ""


def boton_de(mime):
    if not mime.hasFormat(MIME):
        return boton_de_texto(_texto_de(mime))
    try:
        boton = json.loads(bytes(mime.data(MIME)).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return boton if isinstance(boton, dict) else None


class SoltarBoton(object):
    """Para el radial y la pill: aceptan una acción soltada encima de un botón.

    Quien crea el menú pone ``menu.al_soltar = funcion(indice, boton)``.
    El menú tiene que tener ``_que_hay(punto)`` y ``_fijar_sobre(sobre)``.
    """

    al_soltar = None
    _soltando = False

    def _indice_soltar(self, evento):
        if boton_de(evento.mimeData()) is None:
            return None
        sobre = self._que_hay(posicion_local(evento))
        return sobre if isinstance(sobre, int) else None

    def dragEnterEvent(self, evento):
        if boton_de(evento.mimeData()) is not None and self.al_soltar is not None:
            self._soltando = True
            evento.acceptProposedAction()
        else:
            evento.ignore()

    def dragMoveEvent(self, evento):
        indice = self._indice_soltar(evento)
        self._fijar_sobre(indice)
        if indice is None:
            evento.ignore()
        else:
            evento.acceptProposedAction()

    def dragLeaveEvent(self, evento):
        self._soltando = False
        self._fijar_sobre(None)

    def dropEvent(self, evento):
        indice = self._indice_soltar(evento)
        self._soltando = False
        if indice is None or self.al_soltar is None:
            evento.ignore()
            return
        evento.acceptProposedAction()
        self.al_soltar(indice, boton_de(evento.mimeData()))
