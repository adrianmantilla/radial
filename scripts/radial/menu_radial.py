"""La ventana flotante con el menú radial (estilo «Puntos»).

Seis puntos sobre una línea circular fina. Al acercar el ratón, el punto se
abre en un círculo blanco con su icono y el nombre aparece en el centro. Se
arrastra desde el círculo del centro; clic derecho en el centro abre el
configurador.

La ventana no acepta el foco del teclado, así que Maya sigue recibiendo las
teclas (y el doble Tab) aunque el menú esté a la vista. Fuera de los puntos,
la línea y el centro, los clics pasan a Maya.
"""

import math

from radial import radiales as rd
from radial.dibujo import (COLOR_ABIERTO, COLOR_AGARRE, COLOR_AGARRE_SOBRE, COLOR_BORDE, COLOR_CENTRO,
                           COLOR_DETALLE, COLOR_LINEA, COLOR_PUNTO, COLOR_TEXTO, dibujar_icono_boton,
                           dibujar_texto, mezclar)
from radial.menu_comun import (COLOR_ENCENDIDO, DISTANCIA_GESTO, MenuComun, dibujar_encendido, dibujar_flecha_volver,
                                 dibujar_insignia_opciones, dibujar_marca_carpeta)
from radial.qt import QtCore, QtGui, QtWidgets, posicion_global, posicion_local

Qt = QtCore.Qt

_PASO_ANIMACION = 0.22


class MenuRadial(MenuComun, QtWidgets.QWidget):
    """Menú radial. Avisa con tres funciones que le pasa quien lo crea:

    - ``al_ejecutar(indice, opciones=False)``: clic en un botón (``opciones`` con Mayúsculas).
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
        self.setAcceptDrops(True)
        self.setObjectName("RadialMenu")
        self.setWindowTitle("Radial")

        self._al_ejecutar = al_ejecutar
        self._al_mover = al_mover
        self._al_configurar = al_configurar

        self.radial = rd.normalizar({"botones": []})
        self._apertura = [0.0] * self.num()
        self._sobre = None          # índice de botón, "centro" o None
        self._pulsado = None        # botón donde empezó el clic
        self._arrastre = None       # desplazamiento ratón - esquina durante el arrastre
        self._cache_iconos = {}
        self._inicio_clic = None
        self._iniciar_comun()

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
        self._ajustar_a_cantidad()
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

    def _que_hay(self, punto):
        return rd.que_hay_en(*self._local(punto), apariencia=self.apariencia, n=self.num())

    # --- Máscara: solo los puntos, la línea, el centro y el texto reciben clics

    def _actualizar_mascara(self):
        ap = self.apariencia
        c = self.width() // 2

        def circulo(x, y, r):
            r = int(r + 0.999)
            return QtGui.QRegion(int(c + x - r), int(c + y - r), 2 * r, 2 * r, QtGui.QRegion.Ellipse)

        region = circulo(0, 0, ap["radio"] + 2.5).subtracted(circulo(0, 0, ap["radio"] - 2.5))
        for x, y in rd.posiciones(ap["radio"], self.num()):
            region = region.united(circulo(x, y, ap["abierto"] + 3))
        region = region.united(circulo(0, 0, rd.RADIO_CENTRO + 4))
        ancho = int(max(80, 2 * (ap["radio"] - ap["abierto"]) - 4))
        for y in self._lineas_texto_y():
            region = region.united(QtGui.QRegion(c - ancho // 2, int(c + y - 11), ancho, 22))
        self.setMask(region)

    def _lineas_texto_y(self):
        return (-rd.RADIO_CENTRO - 14, rd.RADIO_CENTRO + 14)

    def _direccion(self, dx, dy):
        """El botón en la dirección (dx, dy), como en los marking menus."""
        if math.hypot(dx, dy) < DISTANCIA_GESTO:
            return None
        n = self.num()
        angulo = (math.degrees(math.atan2(dy, dx)) + 90) % 360  # 0 = arriba, sentido del reloj
        indice = int(round(angulo / (360.0 / n))) % n
        return indice if self.botones_visibles()[indice]["tipo"] != "vacio" else None

    # --- Ratón ----------------------------------------------------------------

    def _fijar_sobre(self, sobre):
        if sobre == self._sobre:
            return
        self._sobre = sobre
        if sobre == "centro":
            self.setCursor(Qt.OpenHandCursor)
        elif isinstance(sobre, int) and self.botones_visibles()[sobre]["tipo"] != "vacio":
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.unsetCursor()
        self._seguir_mayus()
        if not self._reloj.isActive():
            self._reloj.start()
        self.update()

    def mouseMoveEvent(self, evento):
        if self._arrastre is not None:
            self.move(posicion_global(evento) - self._arrastre)
            return
        if self._arrastrar_boton(evento):
            return
        self._fijar_sobre(rd.que_hay_en(*self._local(posicion_local(evento)), apariencia=self.apariencia,
                                       n=self.num()))

    def leaveEvent(self, evento):
        if self._arrastre is None:
            self._fijar_sobre(None)

    def mousePressEvent(self, evento):
        sobre = rd.que_hay_en(*self._local(posicion_local(evento)), apariencia=self.apariencia,
                              n=self.num())
        if sobre == "centro" and evento.button() == Qt.LeftButton:
            self._inicio_clic = posicion_global(evento)
            self._arrastre = posicion_global(evento) - self.pos()
            self.setCursor(Qt.ClosedHandCursor)
        elif sobre == "centro" and evento.button() == Qt.RightButton:
            if self._al_configurar:
                self._al_configurar()
        elif isinstance(sobre, int) and evento.button() == Qt.LeftButton:
            self._pulsado = sobre
            self._inicio_pulsado = posicion_local(evento)
        evento.accept()

    def mouseReleaseEvent(self, evento):
        if self._arrastre is not None and evento.button() == Qt.LeftButton:
            self._arrastre = None
            self.setCursor(Qt.OpenHandCursor)
            quieto = (self._inicio_clic is not None
                      and (posicion_global(evento) - self._inicio_clic).manhattanLength() < 4)
            if quieto and self.carpeta is not None:
                self.cerrar_carpeta()  # clic en el centro dentro de una carpeta: volver
            elif not quieto and self._al_mover:
                self._al_mover(self.centro_global())
            return
        sobre = rd.que_hay_en(*self._local(posicion_local(evento)), apariencia=self.apariencia,
                              n=self.num())
        pulsado, self._pulsado = self._pulsado, None
        if evento.button() == Qt.LeftButton and isinstance(sobre, int) and sobre == pulsado:
            self._pulsar(sobre, evento.modifiers())

    def hideEvent(self, evento):
        if self.al_sobre is not None:
            self.al_sobre(None)
        self.carpeta = None
        self._reloj_mayus.stop()
        self._arrastre = None
        self._pulsado = None
        self._sobre = None
        self._apertura = [0.0] * self.num()
        self._reloj.stop()
        super(MenuRadial, self).hideEvent(evento)

    # --- Animación ----------------------------------------------------------

    def _animar(self):
        quietos = True
        for i in range(self.num()):
            vacio = self.botones_visibles()[i]["tipo"] == "vacio"
            objetivo = 1.0 if (self._sobre == i and (not vacio or self._soltando)) else 0.0
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
        color_agarre = COLOR_AGARRE_SOBRE if self._sobre == "centro" else COLOR_AGARRE
        if self.carpeta is not None:
            dibujar_flecha_volver(pintor, QtCore.QPointF(-0.5, 0), color_agarre)
        else:
            pintor.setBrush(color_agarre)
            for x in (-2.8, 2.8):
                for y in (-4.0, 0.0, 4.0):
                    pintor.drawEllipse(QtCore.QPointF(x, y), 1.3, 1.3)

        # Botones
        for i, (x, y) in enumerate(rd.posiciones(ap["radio"], self.num())):
            boton = self.botones_visibles()[i]
            a = self._apertura[i]
            r = ap["punto"] + (ap["abierto"] - ap["punto"]) * a
            encendido = self.estados[i] is True
            pintor.setBrush(mezclar(COLOR_ENCENDIDO if encendido else COLOR_PUNTO, COLOR_ABIERTO, a))
            borde = mezclar(COLOR_BORDE, COLOR_ABIERTO, a)
            if boton["tipo"] == "vacio":
                borde.setAlpha(borde.alpha() // 2)
            pintor.setPen(QtGui.QPen(borde, 1.0))
            pintor.drawEllipse(QtCore.QPointF(x, y), r, r)
            if a > 0.05:
                dibujar_icono_boton(pintor, boton, (x, y), r, ap["opacidad"] * a, self._cache_iconos,
                                    self.devicePixelRatioF())
            if a > 0.6:
                abajo = QtCore.QPointF(x, y + r - 4.5)
                if encendido:
                    dibujar_encendido(pintor, abajo)
                elif boton["tipo"] == "carpeta":
                    dibujar_marca_carpeta(pintor, abajo, QtGui.QColor(40, 40, 40))
                if self._muestra_opciones(i):
                    dibujar_insignia_opciones(pintor, QtCore.QPointF(x + r * 0.72, y + r * 0.72))

        # Nombre del botón bajo el ratón (o de la carpeta abierta)
        rotulo = self.anuncio or (self.boton_carpeta()["texto"] if self.carpeta is not None else "")
        if rotulo and not isinstance(self._sobre, int):
            y_texto, _ = self._lineas_texto_y()
            ancho = max(80.0, 2 * (ap["radio"] - ap["abierto"]) - 4)
            dibujar_texto(pintor, rotulo, QtCore.QRectF(-ancho / 2, y_texto - 10, ancho, 20),
                          COLOR_TEXTO if self.anuncio else COLOR_DETALLE, negrita=True)
        if isinstance(self._sobre, int):
            boton = self.botones_visibles()[self._sobre]
            if boton["tipo"] != "vacio":
                y_texto, y_detalle = self._lineas_texto_y()
                ancho = max(80.0, 2 * (ap["radio"] - ap["abierto"]) - 4)
                dibujar_texto(pintor, boton["texto"], QtCore.QRectF(-ancho / 2, y_texto - 10, ancho, 20),
                              COLOR_TEXTO, negrita=True)
                dibujar_texto(pintor, boton["detalle"], QtCore.QRectF(-ancho / 2, y_detalle - 10, ancho, 20),
                              COLOR_DETALLE)
        pintor.end()
