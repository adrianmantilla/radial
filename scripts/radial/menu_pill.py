"""El menú en forma de pill: una cápsula con los seis botones en fila.

Va a juego con el radial de puntos: fondo oscuro translúcido, iconos de línea
en blanco y el botón que se vuelve blanco al acercar el ratón. El nombre sale
en una pequeña pill encima (o al lado, en vertical). Se arrastra desde los
puntitos del extremo; clic derecho en ellos abre el configurador. Tiene la
misma interfaz que ``MenuRadial`` para que el resto del plugin no distinga.
"""

from radial import radiales as rd
from radial.dibujo import (COLOR_ABIERTO, COLOR_AGARRE, COLOR_AGARRE_SOBRE, COLOR_BORDE_FONDO,
                           COLOR_DETALLE, COLOR_FONDO, COLOR_ICONO_CLARO, COLOR_INICIAL, COLOR_INICIAL_ABIERTO,
                           COLOR_LINEA, COLOR_TEXTO,
                           mezclar, pixmap_icono)
from radial.menu_comun import (MenuComun, dibujar_encendido, dibujar_flecha_volver,
                                 dibujar_insignia_opciones, dibujar_marca_carpeta)
from radial.qt import QtCore, QtGui, QtWidgets, posicion_global, posicion_local

Qt = QtCore.Qt

_PASO_ANIMACION = 0.25
_BORDE = 1  # margen alrededor de la cápsula dentro de la ventana
_TRANSPARENTE = QtGui.QColor(244, 244, 244, 0)


def _ventana_flotante(widget):
    widget.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
                          | Qt.WindowDoesNotAcceptFocus)
    widget.setAttribute(Qt.WA_TranslucentBackground)
    widget.setAttribute(Qt.WA_ShowWithoutActivating)
    widget.setFocusPolicy(Qt.NoFocus)


class EtiquetaPill(QtWidgets.QWidget):
    """La pill pequeña con el nombre del botón. No recibe el ratón."""

    def __init__(self, padre=None):
        super(EtiquetaPill, self).__init__(padre)
        _ventana_flotante(self)
        self.setWindowFlags(self.windowFlags() | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.texto = ""
        self.detalle = ""
        self._fuente = QtGui.QFont(self.font())
        self._fuente.setPixelSize(12)
        self._negrita = QtGui.QFont(self._fuente)
        self._negrita.setBold(True)

    def fijar(self, texto, detalle):
        self.texto, self.detalle = texto, detalle
        ancho = QtGui.QFontMetrics(self._negrita).horizontalAdvance(texto)
        if detalle:
            ancho += QtGui.QFontMetrics(self._fuente).horizontalAdvance(" " + detalle)
        self.setFixedSize(int(ancho) + 24, 24)
        self.update()

    def paintEvent(self, evento):
        pintor = QtGui.QPainter(self)
        pintor.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        pintor.setPen(QtGui.QPen(COLOR_BORDE_FONDO, 1.0))
        pintor.setBrush(QtGui.QColor(16, 17, 19, 210))
        pintor.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        x = 12
        pintor.setFont(self._negrita)
        pintor.setPen(COLOR_TEXTO)
        pintor.drawText(QtCore.QRectF(x, 0, self.width(), self.height()), Qt.AlignVCenter, self.texto)
        if self.detalle:
            x += QtGui.QFontMetrics(self._negrita).horizontalAdvance(self.texto + " ")
            pintor.setFont(self._fuente)
            pintor.setPen(COLOR_DETALLE)
            pintor.drawText(QtCore.QRectF(x, 0, self.width(), self.height()), Qt.AlignVCenter, self.detalle)
        pintor.end()


class MenuPill(MenuComun, QtWidgets.QWidget):
    def __init__(self, padre=None, al_ejecutar=None, al_mover=None, al_configurar=None, vertical=False):
        super(MenuPill, self).__init__(padre)
        _ventana_flotante(self)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setObjectName("RadialPill")
        self.setWindowTitle("Radial")

        self._al_ejecutar = al_ejecutar
        self._al_mover = al_mover
        self._al_configurar = al_configurar
        self.vertical = vertical

        self.radial = rd.normalizar({"botones": []})
        self._apertura = [0.0] * self.num()
        self._sobre = None
        self._pulsado = None
        self._arrastre = None
        self._cache = {}
        self._inicio_clic = None
        self._iniciar_comun()
        self.etiqueta = EtiquetaPill(padre)

        self._reloj = QtCore.QTimer(self)
        self._reloj.setInterval(16)
        self._reloj.timeout.connect(self._animar)
        self.usar_radial(self.radial)

    @property
    def apariencia(self):
        return self.radial["apariencia"]

    def _geometria(self):
        return rd.geometria_pill(self.apariencia, self.vertical, self.num())

    def usar_radial(self, radial, vertical=None):
        centro = self.centro_global() if self.isVisible() else None
        self.radial = rd.normalizar(radial)
        self._ajustar_a_cantidad()
        if vertical is not None:
            self.vertical = bool(vertical)
        self._cache = {}
        ancho, alto, _, _ = self._geometria()
        self.setFixedSize(ancho + 2 * _BORDE, alto + 2 * _BORDE)
        camino = QtGui.QPainterPath()
        radio = min(ancho, alto) / 2.0
        camino.addRoundedRect(QtCore.QRectF(0, 0, ancho + 2 * _BORDE, alto + 2 * _BORDE), radio + _BORDE,
                              radio + _BORDE)
        self.setMask(QtGui.QRegion(camino.toFillPolygon().toPolygon()))
        if centro is not None:
            self.colocar(centro)
        self.update()

    def centro_global(self):
        return self.pos() + QtCore.QPoint(self.width() // 2, self.height() // 2)

    def colocar(self, centro):
        self.move(centro - QtCore.QPoint(self.width() // 2, self.height() // 2))
        self._colocar_etiqueta()

    def _que_hay(self, punto):
        return rd.que_hay_en_pill(punto.x() - _BORDE, punto.y() - _BORDE, self.apariencia, self.vertical,
                                  self.num())

    # --- Etiqueta -------------------------------------------------------------

    def anunciar(self, texto):
        super(MenuPill, self).anunciar(texto)
        self._colocar_etiqueta()

    def _quitar_anuncio(self):
        super(MenuPill, self)._quitar_anuncio()
        self._colocar_etiqueta()

    def _colocar_etiqueta(self):
        rotulo = self.anuncio or (self.boton_carpeta()["texto"] if self.carpeta is not None else "")
        if not isinstance(self._sobre, int) and rotulo and self.isVisible():
            self.etiqueta.fijar(rotulo, "")
            centro = self.mapToGlobal(QtCore.QPoint(self.width() // 2, self.height() // 2))
            if self.vertical:
                self.etiqueta.move(self.mapToGlobal(QtCore.QPoint(self.width(), 0)).x() + 8,
                                   centro.y() - self.etiqueta.height() // 2)
            else:
                self.etiqueta.move(centro.x() - self.etiqueta.width() // 2,
                                   self.mapToGlobal(QtCore.QPoint(0, 0)).y() - self.etiqueta.height() - 8)
            self.etiqueta.show()
            self.etiqueta.raise_()
            return
        if not isinstance(self._sobre, int):
            self.etiqueta.hide()
            return
        boton = self.botones_visibles()[self._sobre]
        if boton["tipo"] == "vacio" or not self.isVisible():
            self.etiqueta.hide()
            return
        self.etiqueta.fijar(boton["texto"], boton["detalle"])
        bx, by, bw, bh = self._geometria()[3][self._sobre]
        centro = self.mapToGlobal(QtCore.QPoint(int(_BORDE + bx + bw / 2), int(_BORDE + by + bh / 2)))
        if self.vertical:
            x = self.mapToGlobal(QtCore.QPoint(self.width(), 0)).x() + 8
            y = centro.y() - self.etiqueta.height() // 2
        else:
            x = centro.x() - self.etiqueta.width() // 2
            y = self.mapToGlobal(QtCore.QPoint(0, 0)).y() - self.etiqueta.height() - 8
        self.etiqueta.move(x, y)
        self.etiqueta.show()
        self.etiqueta.raise_()

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
        self._colocar_etiqueta()
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
        self._fijar_sobre(self._que_hay(posicion_local(evento)))

    def leaveEvent(self, evento):
        if self._arrastre is None:
            self._fijar_sobre(None)

    def mousePressEvent(self, evento):
        sobre = self._que_hay(posicion_local(evento))
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
                self.cerrar_carpeta()  # clic en el agarre dentro de una carpeta: volver
            elif not quieto and self._al_mover:
                self._al_mover(self.centro_global())
            return
        sobre = self._que_hay(posicion_local(evento))
        pulsado, self._pulsado = self._pulsado, None
        if evento.button() == Qt.LeftButton and isinstance(sobre, int) and sobre == pulsado:
            self._pulsar(sobre, evento.modifiers())

    def moveEvent(self, evento):
        self._colocar_etiqueta()
        super(MenuPill, self).moveEvent(evento)

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
        self.etiqueta.hide()
        super(MenuPill, self).hideEvent(evento)

    def closeEvent(self, evento):
        self.etiqueta.close()
        super(MenuPill, self).closeEvent(evento)

    # --- Animación y dibujo ---------------------------------------------------

    def _animar(self):
        quietos = True
        for i in range(self.num()):
            vacio = self.botones_visibles()[i]["tipo"] == "vacio"
            objetivo = 1.0 if (self._sobre == i and (not vacio or self._soltando)) else 0.0
            actual = self._apertura[i]
            if abs(objetivo - actual) > 1e-3:
                paso = _PASO_ANIMACION if objetivo > actual else -_PASO_ANIMACION
                actual += paso
                self._apertura[i] = min(actual, objetivo) if paso > 0 else max(actual, objetivo)
                quietos = False
        if quietos:
            self._reloj.stop()
        self.update()

    def _iconos(self, boton, lado):
        escala = self.devicePixelRatioF()
        clave = (boton["icono"], lado, escala)
        if clave not in self._cache:
            self._cache[clave] = (pixmap_icono(boton["icono"], lado, escala, COLOR_ICONO_CLARO),
                                  pixmap_icono(boton["icono"], lado, escala))
        return self._cache[clave]

    def paintEvent(self, evento):
        ap = self.apariencia
        ancho, alto, agarre, botones = self._geometria()
        pintor = QtGui.QPainter(self)
        pintor.setRenderHint(QtGui.QPainter.Antialiasing)
        pintor.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        pintor.setOpacity(ap["opacidad"])
        pintor.translate(_BORDE, _BORDE)

        radio = min(ancho, alto) / 2.0
        pintor.setPen(QtGui.QPen(COLOR_BORDE_FONDO, 1.0))
        pintor.setBrush(COLOR_FONDO)
        pintor.drawRoundedRect(QtCore.QRectF(0.5, 0.5, ancho - 1, alto - 1), radio - 0.5, radio - 0.5)

        # Agarre de seis puntitos y raya
        ax, ay, aw, ah = agarre
        cx, cy = ax + aw / 2.0, ay + ah / 2.0
        pintor.setPen(Qt.NoPen)
        color_agarre = COLOR_AGARRE_SOBRE if self._sobre == "centro" else COLOR_AGARRE
        if self.carpeta is not None:
            dibujar_flecha_volver(pintor, QtCore.QPointF(cx - 0.5, cy), color_agarre)
        else:
            pintor.setBrush(color_agarre)
            for a in (-2.8, 2.8):
                for b in (-4.0, 0.0, 4.0):
                    px, py = (cx + b, cy + a) if self.vertical else (cx + a, cy + b)
                    pintor.drawEllipse(QtCore.QPointF(px, py), 1.3, 1.3)
        pintor.setPen(QtGui.QPen(COLOR_LINEA, 1.0))
        raya = rd.PILL_MARGEN + rd.PILL_AGARRE + rd.PILL_RAYA / 2.0
        mitad = ap["pill_boton"] * 0.28
        if self.vertical:
            pintor.drawLine(QtCore.QPointF(cx - mitad, raya), QtCore.QPointF(cx + mitad, raya))
        else:
            pintor.drawLine(QtCore.QPointF(raya, cy - mitad), QtCore.QPointF(raya, cy + mitad))

        # Botones
        lado_icono = round(ap["pill_boton"] * 0.56)
        for i, (bx, by, bw, bh) in enumerate(botones):
            boton = self.botones_visibles()[i]
            a = self._apertura[i]
            centro = QtCore.QPointF(bx + bw / 2.0, by + bh / 2.0)
            if a > 0:
                pintor.setPen(Qt.NoPen)
                pintor.setBrush(mezclar(_TRANSPARENTE, COLOR_ABIERTO, a))
                pintor.drawEllipse(centro, bw / 2.0, bh / 2.0)
            claro, oscuro = self._iconos(boton, lado_icono)
            rect = QtCore.QRectF(centro.x() - lado_icono / 2.0, centro.y() - lado_icono / 2.0,
                                 lado_icono, lado_icono)
            base = ap["opacidad"] * (0.45 if boton["tipo"] == "vacio" else 1.0)
            if claro is None:
                self._inicial(pintor, boton, rect, a, base)
            else:
                if a < 1:
                    pintor.setOpacity(base * (1 - a))
                    pintor.drawPixmap(rect, claro, QtCore.QRectF(claro.rect()))
                if a > 0:
                    pintor.setOpacity(base * a)
                    pintor.drawPixmap(rect, oscuro, QtCore.QRectF(oscuro.rect()))
            pintor.setOpacity(ap["opacidad"])
            abajo = QtCore.QPointF(centro.x(), centro.y() + bh / 2.0 - 4)
            if self.estados[i] is True:
                dibujar_encendido(pintor, abajo, 2.0)
            elif boton["tipo"] == "carpeta":
                dibujar_marca_carpeta(pintor, abajo, mezclar(COLOR_INICIAL, COLOR_INICIAL_ABIERTO, a))
            if self._muestra_opciones(i):
                dibujar_insignia_opciones(pintor, QtCore.QPointF(centro.x() + bw * 0.36, centro.y() + bh * 0.36), 8)
        pintor.end()

    def _inicial(self, pintor, boton, rect, a, base):
        if boton["tipo"] == "vacio" or not boton["texto"]:
            pintor.setPen(Qt.NoPen)
            pintor.setBrush(COLOR_AGARRE)
            pintor.drawEllipse(rect.center(), 2.5, 2.5)
            return
        fuente = QtGui.QFont(self.font())
        fuente.setPixelSize(max(9, int(rect.height() * 0.8)))
        fuente.setBold(True)
        pintor.setFont(fuente)
        pintor.setOpacity(base)
        pintor.setPen(mezclar(COLOR_INICIAL, COLOR_INICIAL_ABIERTO, a))
        pintor.drawText(rect, Qt.AlignCenter, boton["texto"][:1].upper())
        pintor.setOpacity(self.apariencia["opacidad"])
