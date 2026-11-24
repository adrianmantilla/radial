"""Modo aprendizaje: una tarjeta junto al menú explica el botón que está bajo el ratón.

``contenido()`` no depende de Qt; ``TarjetaAyuda`` es la ventana que lo enseña.
La tarjeta no recibe el ratón ni el teclado: solo se mira.
"""

from radial import iconos
from radial import dibujo
from radial.dibujo import COLOR_BORDE, COLOR_DETALLE, COLOR_TARJETA, COLOR_TEXTO, pixmap_icono
from radial.i18n import t
from radial.qt import QtCore, QtGui, QtWidgets, sigue_vivo

Qt = QtCore.Qt

ANCHO = 280
SEPARACION = 12
RETARDO_MS = 350
LADO_ICONO = 26


def contenido(boton, info=None, encendido=None, opciones=False, icono=""):
    """Lo que dice la tarjeta del ``boton``: dict con titulo, subtitulo, descripcion, lineas e icono.

    ``info`` es la acción del buscador para ese comando (traducción, ayuda, categoría, menú y atajo),
    ``encendido`` el estado si es un interruptor, ``opciones`` si tiene ventana de opciones e
    ``icono`` el de la herramienta en Maya (si el botón no tiene uno propio).
    None si el botón no tiene nada que explicar.
    """
    if not boton or boton.get("tipo") in (None, "", "vacio"):
        return None
    info = info or {}
    tipo = boton.get("tipo")
    titulo = info.get("traduccion") or boton.get("texto") or info.get("texto", "")
    partes = []
    if tipo == "comando":
        partes.append(boton.get("accion", ""))
        if info.get("categoria") and not info.get("menu"):
            partes.append(info["categoria"])
    elif tipo in ("python", "mel", "estante", "carpeta"):
        partes.append(t("tipo_" + tipo))
    subtitulo = " · ".join(p for p in partes if p and p != titulo)
    descripcion = info.get("descripcion") or boton.get("descripcion", "") or ""
    lineas = []
    if tipo == "carpeta":
        lineas.append(t("aprendizaje_carpeta"))
    if encendido is not None:
        lineas.append(t("aprendizaje_interruptor",
                        estado=t("aprendizaje_encendido") if encendido else t("aprendizaje_apagado")))
    if info.get("menu"):
        lineas.append(t("aprendizaje_menu", menu=info["menu"]))
    if info.get("atajo"):
        lineas.append(t("aprendizaje_atajo", atajo=info["atajo"]))
    if opciones:
        lineas.append(t("aprendizaje_opciones"))
    return {"titulo": titulo, "subtitulo": subtitulo, "descripcion": descripcion, "lineas": lineas,
            "icono": boton.get("icono") or icono or ""}


class TarjetaAyuda(QtWidgets.QWidget):
    """Ventana flotante con la explicación. ``mostrar(datos, menu)`` y ``ocultar()``."""

    def __init__(self, padre=None):
        super(TarjetaAyuda, self).__init__(padre)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                            | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.NoFocus)
        self.setObjectName("RadialAyuda")
        self.setFixedWidth(ANCHO)
        capa = QtWidgets.QVBoxLayout(self)
        capa.setContentsMargins(14, 11, 14, 12)
        capa.setSpacing(3)
        self.titulo = self._etiqueta(13, True, COLOR_TEXTO)
        self.subtitulo = self._etiqueta(10, False, COLOR_DETALLE)
        self.descripcion = self._etiqueta(11, False, COLOR_TEXTO)
        self.lineas = self._etiqueta(10, False, QtGui.QColor(127, 209, 166))
        # Cabecera: el icono de la herramienta a la izquierda del título
        self.icono = QtWidgets.QLabel()
        self.icono.setFixedSize(LADO_ICONO, LADO_ICONO)
        self.icono.setStyleSheet("background: transparent;")
        cabecera = QtWidgets.QHBoxLayout()
        cabecera.setSpacing(9)
        cabecera.addWidget(self.icono, 0, Qt.AlignTop)
        textos = QtWidgets.QVBoxLayout()
        textos.setSpacing(1)
        textos.addWidget(self.titulo)
        textos.addWidget(self.subtitulo)
        cabecera.addLayout(textos, 1)
        capa.addLayout(cabecera)
        for etiqueta in (self.descripcion, self.lineas):
            capa.addWidget(etiqueta)
        self.datos = None
        self._menu = None
        self._reloj = QtCore.QTimer(self)
        self._reloj.setSingleShot(True)
        self._reloj.setInterval(RETARDO_MS)
        self._reloj.timeout.connect(self._aparecer)

    @staticmethod
    def _etiqueta(tamano, negrita, color):
        etiqueta = QtWidgets.QLabel()
        etiqueta.setWordWrap(True)
        letra = etiqueta.font()
        letra.setPixelSize(tamano + 2)
        letra.setBold(negrita)
        etiqueta.setFont(letra)
        etiqueta.setStyleSheet("color: {}; background: transparent;".format(color.name()))
        return etiqueta

    def mostrar(self, datos, menu):
        """Enseña ``datos`` (de ``contenido``) junto a ``menu`` tras un momento sin moverse."""
        if not datos:
            self.ocultar()
            return
        self.datos = datos
        self._menu = menu
        self.titulo.setText(datos["titulo"])
        icono = datos.get("icono", "")
        mapa = None
        if icono:
            try:
                lado = LADO_ICONO if iconos.es_imagen(icono) else 18
                mapa = pixmap_icono(icono, lado, self.devicePixelRatioF(), dibujo.COLOR_ICONO_CLARO)
            except Exception:  # un icono que no se lee no impide la ayuda
                mapa = None
        if mapa is not None:
            self.icono.setPixmap(mapa)
        self.icono.setVisible(mapa is not None)
        for etiqueta, texto in ((self.subtitulo, datos["subtitulo"]), (self.descripcion, datos["descripcion"]),
                                (self.lineas, "\n".join(datos["lineas"]))):
            etiqueta.setText(texto)
            etiqueta.setVisible(bool(texto))
        self.adjustSize()
        if self.isVisible():
            self._aparecer()
        else:
            self._reloj.start()

    def ocultar(self):
        self._reloj.stop()
        self.datos = None
        self.hide()

    def _aparecer(self):
        if not self.datos or not sigue_vivo(self._menu) or not self._menu.isVisible():
            self.hide()
            return
        self.colocar()
        self.show()
        self.raise_()

    def colocar(self):
        """A la derecha del menú; si no cabe, a la izquierda."""
        menu = self._menu
        arriba = menu.mapToGlobal(QtCore.QPoint(0, 0))
        y = arriba.y() + (menu.height() - self.height()) // 2
        x = arriba.x() + menu.width() + SEPARACION
        pantalla = QtGui.QGuiApplication.screenAt(arriba) or QtGui.QGuiApplication.primaryScreen()
        if pantalla is not None:
            zona = pantalla.availableGeometry()
            if x + self.width() > zona.right():
                x = arriba.x() - self.width() - SEPARACION
            y = max(zona.top(), min(zona.bottom() - self.height(), y))
        self.move(x, y)

    def paintEvent(self, evento):
        pintor = QtGui.QPainter(self)
        pintor.setRenderHint(QtGui.QPainter.Antialiasing)
        pintor.setPen(QtGui.QPen(COLOR_BORDE, 1))
        pintor.setBrush(COLOR_TARJETA)
        pintor.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
