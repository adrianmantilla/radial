"""Lo que comparten el radial y la pill: carpetas, interruptores y Mayúsculas + clic.

- **Carpetas**: un botón ``carpeta`` muestra sus seis botones en lugar de los
  del radial; un clic en el centro (o en el agarre de la pill) vuelve.
- **Estados**: ``fijar_estados([True, None, ...])`` marca los botones encendidos.
- **Mayúsculas**: con Mayúsculas pulsada, el botón bajo el ratón enseña si tiene
  ventana de opciones (``tiene_opciones(boton)``, que pone quien crea el menú).
"""

from radial import radiales as rd
from radial.arrastre import SoltarBoton
from radial.dibujo import COLOR_ABIERTO, COLOR_FONDO
from radial.qt import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt

COLOR_ENCENDIDO = QtGui.QColor(127, 209, 166)


class MenuComun(SoltarBoton):
    """Mezcla para MenuRadial y MenuPill. Llamar a ``_iniciar_comun()`` en ``__init__``."""

    tiene_opciones = staticmethod(lambda boton: False)
    al_carpeta = None  # funcion(carpeta) al abrir o cerrar una carpeta
    al_sobre = None    # funcion(boton o None) al pasar el ratón por un botón (modo aprendizaje)

    def _iniciar_comun(self):
        self.carpeta = None
        self.estados = [None] * rd.NUM_BOTONES
        self._mayus = False
        self._reloj_mayus = QtCore.QTimer(self)
        self._reloj_mayus.setInterval(120)
        self._reloj_mayus.timeout.connect(self._mirar_mayus)
        self.anuncio = ""
        self._reloj_anuncio = QtCore.QTimer(self)
        self._reloj_anuncio.setSingleShot(True)
        self._reloj_anuncio.setInterval(1600)
        self._reloj_anuncio.timeout.connect(self._quitar_anuncio)

    def anunciar(self, texto):
        """Enseña un momento ``texto`` (por ejemplo, el radial al que se ha cambiado solo)."""
        self.anuncio = texto
        self._reloj_anuncio.start()
        self.update()

    def _quitar_anuncio(self):
        self.anuncio = ""
        self.update()

    # --- Carpetas -------------------------------------------------------------

    def botones_visibles(self):
        if self.carpeta is not None:
            boton = self.radial["botones"][self.carpeta]
            if boton["tipo"] == "carpeta":
                return boton["botones"]
            self.carpeta = None
        return self.radial["botones"]

    def boton_carpeta(self):
        return self.radial["botones"][self.carpeta] if self.carpeta is not None else None

    def abrir_carpeta(self, indice):
        self.carpeta = indice
        self._cambio_de_pagina()

    def cerrar_carpeta(self):
        if self.carpeta is None:
            return
        self.carpeta = None
        self._cambio_de_pagina()

    def _cambio_de_pagina(self):
        self.estados = [None] * rd.NUM_BOTONES
        self._sobre = None
        self._apertura = [0.0] * rd.NUM_BOTONES
        if self.al_carpeta is not None:
            self.al_carpeta(self.carpeta)
        self.update()

    def fijar_estados(self, estados):
        estados = list(estados or [])[:rd.NUM_BOTONES]
        self.estados = estados + [None] * (rd.NUM_BOTONES - len(estados))
        self.update()

    # --- Clic en un botón -------------------------------------------------------

    def _pulsar(self, indice, modificadores):
        boton = self.botones_visibles()[indice]
        if boton["tipo"] == "vacio":
            return
        if boton["tipo"] == "carpeta":
            self.abrir_carpeta(indice)
            return
        if self._al_ejecutar:
            self._al_ejecutar(indice, opciones=bool(modificadores & Qt.ShiftModifier))

    # --- Mayúsculas -------------------------------------------------------------

    def _mirar_mayus(self):
        mayus = bool(QtWidgets.QApplication.queryKeyboardModifiers() & Qt.ShiftModifier)
        if mayus != self._mayus:
            self._mayus = mayus
            self.update()
        if not isinstance(self._sobre, int):
            self._reloj_mayus.stop()

    def _seguir_mayus(self):
        if self.al_sobre is not None:
            sobre = self.botones_visibles()[self._sobre] if isinstance(self._sobre, int) else None
            self.al_sobre(sobre if sobre and sobre["tipo"] != "vacio" else None)
        if isinstance(self._sobre, int):
            self._mirar_mayus()
            if not self._reloj_mayus.isActive():
                self._reloj_mayus.start()

    def _muestra_opciones(self, indice):
        if not self._mayus or self._sobre != indice:
            return False
        try:
            return bool(self.tiene_opciones(self.botones_visibles()[indice]))
        except Exception:
            return False


def dibujar_insignia_opciones(pintor, centro, lado=9.0):
    """El cuadradito de «opciones» (como la ❐ de los menús de Maya)."""
    x, y = centro.x(), centro.y()
    pintor.save()
    pintor.setPen(QtGui.QPen(COLOR_ABIERTO, 1.0))
    pintor.setBrush(COLOR_FONDO)
    pintor.drawRoundedRect(QtCore.QRectF(x - lado / 2, y - lado / 2, lado, lado), 2, 2)
    pintor.drawLine(QtCore.QPointF(x - lado / 4, y), QtCore.QPointF(x + lado / 4, y))
    pintor.restore()


def dibujar_encendido(pintor, centro, radio=2.2):
    pintor.save()
    pintor.setPen(Qt.NoPen)
    pintor.setBrush(COLOR_ENCENDIDO)
    pintor.drawEllipse(centro, radio, radio)
    pintor.restore()


def dibujar_flecha_volver(pintor, centro, color, tamano=5.0):
    pintor.save()
    pintor.setPen(QtGui.QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    pintor.setBrush(Qt.NoBrush)
    x, y = centro.x(), centro.y()
    camino = QtGui.QPainterPath(QtCore.QPointF(x + tamano * 0.35, y - tamano))
    camino.lineTo(QtCore.QPointF(x - tamano * 0.65, y))
    camino.lineTo(QtCore.QPointF(x + tamano * 0.35, y + tamano))
    pintor.drawPath(camino)
    pintor.restore()


def dibujar_marca_carpeta(pintor, centro, color):
    """Puntito que indica que un botón es una carpeta."""
    pintor.save()
    pintor.setPen(Qt.NoPen)
    pintor.setBrush(color)
    for dx in (-3.0, 0.0, 3.0):
        pintor.drawEllipse(QtCore.QPointF(centro.x() + dx, centro.y()), 0.9, 0.9)
    pintor.restore()
