"""La ventana flotante con el menú radial (estilo «Puntos»).

Seis puntos sobre una línea circular fina. Al acercar el ratón, el punto se
abre en un círculo blanco con su icono y el nombre aparece en el centro. Se
arrastra desde el círculo del centro; clic derecho en el centro abre el
configurador.

La ventana no acepta el foco del teclado, así que Maya sigue recibiendo las
teclas (y el doble Tab) aunque el menú esté a la vista. Fuera de los puntos,
la línea y el centro, los clics pasan a Maya.
"""

from radial import iconos
from radial import radiales as rd
from radial.qt import QtCore, QtGui, QtSvg, QtWidgets, posicion_global, posicion_local

Qt = QtCore.Qt

_PASO_ANIMACION = 0.22
_TAM_ICONO = 22.0


def _mezclar(a, b, t):
    return QtGui.QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


COLOR_PUNTO = QtGui.QColor(16, 17, 19, 178)
COLOR_ABIERTO = QtGui.QColor(244, 244, 244, 255)
COLOR_BORDE = QtGui.QColor(255, 255, 255, 72)
COLOR_LINEA = QtGui.QColor(255, 255, 255, 46)
COLOR_CENTRO = QtGui.QColor(16, 17, 19, 170)
COLOR_AGARRE = QtGui.QColor(255, 255, 255, 95)
COLOR_AGARRE_SOBRE = QtGui.QColor(255, 255, 255, 200)
COLOR_TEXTO = QtGui.QColor(242, 242, 242)
COLOR_DETALLE = QtGui.QColor(196, 196, 196)
COLOR_SOMBRA = QtGui.QColor(0, 0, 0, 150)


class MenuRadial(QtWidgets.QWidget):
    """Menú radial. Avisa con tres funciones que le pasa quien lo crea:

    - ``al_ejecutar(indice)``: clic en un botón.
    - ``al_mover(centro)``: se soltó tras arrastrarlo (centro en pantalla, QPoint).
    - ``al_configurar()``: clic derecho en el centro.
    """

    def __init__(self, padre=None, al_ejecutar=None, al_mover=None, al_configurar=None):
        super(MenuRadial, self).__init__(padre)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
                            | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setMouseTracking(True)
        self.setObjectName("RadialMenu")
        self.setWindowTitle("Radial")

        self._al_ejecutar = al_ejecutar
        self._al_mover = al_mover
        self._al_configurar = al_configurar

        self.radial = rd.normalizar({"botones": []})
        self._apertura = [0.0] * rd.NUM_BOTONES
        self._sobre = None          # índice de botón, "centro" o None
        self._pulsado = None        # botón donde empezó el clic
        self._arrastre = None       # desplazamiento ratón - esquina durante el arrastre
        self._cache_iconos = {}

        self._reloj = QtCore.QTimer(self)
        self._reloj.setInterval(16)
        self._reloj.timeout.connect(self._animar)

        self.usar_radial(self.radial)

    # --- Datos --------------------------------------------------------------

    @property
    def apariencia(self):
        return self.radial["apariencia"]

    def usar_radial(self, radial):
        """Cambia los botones y el tamaño, conservando el centro en pantalla."""
        centro = self.centro_global() if self.isVisible() else None
        self.radial = rd.normalizar(radial)
        self._cache_iconos = {}
        lado = rd.lado_ventana(self.apariencia)
        self.setFixedSize(lado, lado)
        self._actualizar_mascara()
        if centro is not None:
            self.colocar(centro)
        self.update()

    # --- Posición -----------------------------------------------------------

    def centro_global(self):
        return self.pos() + QtCore.QPoint(self.width() // 2, self.height() // 2)

    def colocar(self, centro):
        self.move(centro - QtCore.QPoint(self.width() // 2, self.height() // 2))

    def _local(self, punto):
        """Pasa un punto de la ventana a coordenadas con origen en el centro."""
        return punto.x() - self.width() / 2.0, punto.y() - self.height() / 2.0

    # --- Máscara: solo los puntos, la línea, el centro y el texto reciben clics

    def _actualizar_mascara(self):
        ap = self.apariencia
        c = self.width() // 2

        def circulo(x, y, r):
            r = int(r + 0.999)
            return QtGui.QRegion(int(c + x - r), int(c + y - r), 2 * r, 2 * r, QtGui.QRegion.Ellipse)

        region = circulo(0, 0, ap["radio"] + 2.5).subtracted(circulo(0, 0, ap["radio"] - 2.5))
        for x, y in rd.posiciones(ap["radio"]):
            region = region.united(circulo(x, y, ap["abierto"] + 3))
        region = region.united(circulo(0, 0, rd.RADIO_CENTRO + 4))
        ancho = int(max(80, 2 * (ap["radio"] - ap["abierto"]) - 4))
        for y in self._lineas_texto_y():
            region = region.united(QtGui.QRegion(c - ancho // 2, int(c + y - 11), ancho, 22))
        self.setMask(region)

    def _lineas_texto_y(self):
        return (-rd.RADIO_CENTRO - 14, rd.RADIO_CENTRO + 14)

    # --- Ratón ----------------------------------------------------------------

    def _fijar_sobre(self, sobre):
        if sobre == self._sobre:
            return
        self._sobre = sobre
        if sobre == "centro":
            self.setCursor(Qt.OpenHandCursor)
        elif isinstance(sobre, int) and self.radial["botones"][sobre]["tipo"] != "vacio":
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.unsetCursor()
        if not self._reloj.isActive():
            self._reloj.start()
        self.update()

    def mouseMoveEvent(self, evento):
        if self._arrastre is not None:
            self.move(posicion_global(evento) - self._arrastre)
            return
        self._fijar_sobre(rd.que_hay_en(*self._local(posicion_local(evento)), apariencia=self.apariencia))

    def leaveEvent(self, evento):
        if self._arrastre is None:
            self._fijar_sobre(None)

    def mousePressEvent(self, evento):
        sobre = rd.que_hay_en(*self._local(posicion_local(evento)), apariencia=self.apariencia)
        if sobre == "centro" and evento.button() == Qt.LeftButton:
            self._arrastre = posicion_global(evento) - self.pos()
            self.setCursor(Qt.ClosedHandCursor)
        elif sobre == "centro" and evento.button() == Qt.RightButton:
            if self._al_configurar:
                self._al_configurar()
        elif isinstance(sobre, int) and evento.button() == Qt.LeftButton:
            self._pulsado = sobre
        evento.accept()

    def mouseReleaseEvent(self, evento):
        if self._arrastre is not None and evento.button() == Qt.LeftButton:
            self._arrastre = None
            self.setCursor(Qt.OpenHandCursor)
            if self._al_mover:
                self._al_mover(self.centro_global())
            return
        sobre = rd.que_hay_en(*self._local(posicion_local(evento)), apariencia=self.apariencia)
        pulsado, self._pulsado = self._pulsado, None
        if (evento.button() == Qt.LeftButton and isinstance(sobre, int) and sobre == pulsado
                and self.radial["botones"][sobre]["tipo"] != "vacio" and self._al_ejecutar):
            self._al_ejecutar(sobre)

    def hideEvent(self, evento):
        self._arrastre = None
        self._pulsado = None
        self._sobre = None
        self._apertura = [0.0] * rd.NUM_BOTONES
        self._reloj.stop()
        super(MenuRadial, self).hideEvent(evento)

    # --- Animación ----------------------------------------------------------

    def _animar(self):
        quietos = True
        for i in range(rd.NUM_BOTONES):
            vacio = self.radial["botones"][i]["tipo"] == "vacio"
            objetivo = 1.0 if (self._sobre == i and not vacio) else 0.0
            actual = self._apertura[i]
            if abs(objetivo - actual) > 1e-3:
                paso = _PASO_ANIMACION if objetivo > actual else -_PASO_ANIMACION
                actual += paso
                actual = min(actual, objetivo) if paso > 0 else max(actual, objetivo)
                self._apertura[i] = actual
                quietos = False
        if quietos:
            self._reloj.stop()
        self.update()

    # --- Dibujo ---------------------------------------------------------------

    def _icono(self, boton, tamano):
        """QPixmap del icono del botón (en negro, para el círculo blanco) o None."""
        clave = (boton["icono"], boton["texto"], int(tamano), self.devicePixelRatioF())
        if clave in self._cache_iconos:
            return self._cache_iconos[clave]
        escala = self.devicePixelRatioF()
        lado = max(1, int(tamano * escala))
        mapa = None
        datos = iconos.svg(boton["icono"])
        if datos is not None and QtSvg is not None:
            mapa = QtGui.QPixmap(lado, lado)
            mapa.fill(Qt.transparent)
            pintor = QtGui.QPainter(mapa)
            pintor.setRenderHint(QtGui.QPainter.Antialiasing)
            QtSvg.QSvgRenderer(QtCore.QByteArray(datos)).render(pintor)
            pintor.end()
        elif iconos.es_imagen(boton["icono"]):
            imagen = QtGui.QPixmap(boton["icono"])
            if not imagen.isNull():
                mapa = imagen.scaled(lado, lado, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if mapa is not None:
            mapa.setDevicePixelRatio(escala)
        self._cache_iconos[clave] = mapa
        return mapa

    def paintEvent(self, evento):
        ap = self.apariencia
        pintor = QtGui.QPainter(self)
        pintor.setRenderHint(QtGui.QPainter.Antialiasing)
        pintor.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        pintor.setOpacity(ap["opacidad"])
        pintor.translate(self.width() / 2.0, self.height() / 2.0)

        # Línea circular
        pintor.setPen(QtGui.QPen(COLOR_LINEA, 1.0))
        pintor.setBrush(Qt.NoBrush)
        pintor.drawEllipse(QtCore.QPointF(0, 0), ap["radio"], ap["radio"])

        # Centro con el agarre de seis puntitos
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(COLOR_CENTRO)
        pintor.drawEllipse(QtCore.QPointF(0, 0), rd.RADIO_CENTRO, rd.RADIO_CENTRO)
        pintor.setBrush(COLOR_AGARRE_SOBRE if self._sobre == "centro" else COLOR_AGARRE)
        for x in (-2.8, 2.8):
            for y in (-4.0, 0.0, 4.0):
                pintor.drawEllipse(QtCore.QPointF(x, y), 1.3, 1.3)

        # Botones
        for i, (x, y) in enumerate(rd.posiciones(ap["radio"])):
            boton = self.radial["botones"][i]
            a = self._apertura[i]
            r = ap["punto"] + (ap["abierto"] - ap["punto"]) * a
            pintor.setBrush(_mezclar(COLOR_PUNTO, COLOR_ABIERTO, a))
            borde = _mezclar(COLOR_BORDE, COLOR_ABIERTO, a)
            if boton["tipo"] == "vacio":
                borde.setAlpha(borde.alpha() // 2)
            pintor.setPen(QtGui.QPen(borde, 1.0))
            pintor.drawEllipse(QtCore.QPointF(x, y), r, r)
            if a > 0.05:
                self._dibujar_icono(pintor, boton, x, y, r, a)

        # Nombre del botón bajo el ratón
        if isinstance(self._sobre, int):
            boton = self.radial["botones"][self._sobre]
            if boton["tipo"] != "vacio":
                y_texto, y_detalle = self._lineas_texto_y()
                self._texto(pintor, boton["texto"], y_texto, COLOR_TEXTO, negrita=True)
                self._texto(pintor, boton["detalle"], y_detalle, COLOR_DETALLE)
        pintor.end()

    def _dibujar_icono(self, pintor, boton, x, y, r, a):
        tamano = min(_TAM_ICONO, r * 1.25)
        mapa = self._icono(boton, _TAM_ICONO)
        pintor.save()
        pintor.setOpacity(self.apariencia["opacidad"] * a)
        if mapa is not None:
            rect = QtCore.QRectF(x - tamano / 2, y - tamano / 2, tamano, tamano)
            pintor.drawPixmap(rect, mapa, QtCore.QRectF(mapa.rect()))
        elif boton["texto"]:
            fuente = QtGui.QFont(self.font())
            fuente.setPixelSize(max(8, int(r * 0.9)))
            fuente.setBold(True)
            pintor.setFont(fuente)
            pintor.setPen(QtGui.QColor(20, 20, 20))
            pintor.drawText(QtCore.QRectF(x - r, y - r, 2 * r, 2 * r), Qt.AlignCenter,
                            boton["texto"][:1].upper())
        pintor.restore()

    def _texto(self, pintor, texto, y, color, negrita=False):
        if not texto:
            return
        fuente = QtGui.QFont(self.font())
        fuente.setPixelSize(12)
        fuente.setBold(negrita)
        pintor.setFont(fuente)
        ancho = max(80.0, 2 * (self.apariencia["radio"] - self.apariencia["abierto"]) - 4)
        rect = QtCore.QRectF(-ancho / 2, y - 10, ancho, 20)
        metrica = QtGui.QFontMetrics(fuente)
        texto = metrica.elidedText(texto, Qt.ElideRight, int(ancho))
        pintor.setPen(COLOR_SOMBRA)
        pintor.drawText(rect.translated(0, 1), Qt.AlignCenter, texto)
        pintor.setPen(color)
        pintor.drawText(rect, Qt.AlignCenter, texto)
