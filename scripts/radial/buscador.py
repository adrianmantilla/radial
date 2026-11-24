"""Buscador de acciones: una barra fina debajo del radial o de la pill.

Se escribe en ella (tras hacer clic, para no quitarle el teclado a Maya) y sale
un desplegable con las órdenes de Maya que coinciden. Clic o Intro ejecuta;
Esc borra y devuelve el teclado a Maya. Un resultado se puede arrastrar hasta
un botón del menú para asignárselo.

El buscador sigue al menú: se mueve, se muestra y se oculta con él.
"""

from radial import busqueda, iconos
from radial.arrastre import datos_mime
from radial.dibujo import COLOR_BORDE_FONDO, COLOR_DETALLE, COLOR_TEXTO, pixmap_icono
from radial.i18n import t
from radial.qt import QtCore, QtGui, QtWidgets, posicion_local, sigue_vivo

Qt = QtCore.Qt
QEvent = QtCore.QEvent

ALTO_CAMPO = 30
ALTO_FILA = 38
MARGEN = 5
SEPARACION = 6
ANCHO_RADIAL = 240
ANCHO_VERTICAL = 190
ANCHO_MINIMO = 200

COLOR_CAPSULA = QtGui.QColor(16, 17, 19, 205)
COLOR_LISTA = QtGui.QColor(22, 23, 26, 238)
COLOR_BORDE_ACTIVO = QtGui.QColor(255, 255, 255, 110)
COLOR_ELEGIDO = QtGui.QColor(244, 244, 244)
COLOR_TEXTO_ELEGIDO = QtGui.QColor(20, 20, 20)
COLOR_DETALLE_ELEGIDO = QtGui.QColor(90, 90, 90)
COLOR_PISTA = QtGui.QColor(150, 154, 160)
COLOR_CIRCULO = QtGui.QColor(255, 255, 255, 22)


def _ventana_flotante(widget, acepta_foco):
    banderas = Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
    if not acepta_foco:
        banderas |= Qt.WindowDoesNotAcceptFocus
    # Al aparecer nunca se queda con el teclado: solo al hacer clic en el campo.
    widget.setAttribute(Qt.WA_ShowWithoutActivating)
    widget.setWindowFlags(banderas)
    widget.setAttribute(Qt.WA_TranslucentBackground)


class ListaResultados(QtWidgets.QWidget):
    """El desplegable. No acepta el foco: el teclado sigue en el campo."""

    def __init__(self, al_elegir, padre=None):
        super(ListaResultados, self).__init__(padre)
        _ventana_flotante(self, acepta_foco=False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setMouseTracking(True)
        self._al_elegir = al_elegir
        self.acciones = []
        self.consulta = ""
        self.titulo = ""
        self.vacio = ""
        self.elegida = 0
        self._pulsada = None
        self._inicio_arrastre = None
        self._iconos = {}
        # funcion(nombre del comando) -> icono de Maya (":/polyBevel.png") o "" (la pone quien crea el buscador)
        self.buscar_icono = None

    def fijar(self, acciones, consulta, titulo="", vacio=""):
        self.acciones = list(acciones)
        self.consulta = consulta
        self.titulo = titulo
        self.vacio = vacio
        self.elegida = 0
        self.setFixedHeight(self.alto_necesario())
        self.update()

    def alto_necesario(self):
        filas = len(self.acciones) if self.acciones else (1 if self.vacio else 0)
        return 2 * MARGEN + (22 if self.titulo else 0) + filas * ALTO_FILA

    def _y0(self):
        return MARGEN + (22 if self.titulo else 0)

    def fila_en(self, punto):
        if not self.acciones:
            return None
        i = int((punto.y() - self._y0()) // ALTO_FILA)
        return i if 0 <= i < len(self.acciones) and punto.y() >= self._y0() else None

    def mover(self, paso):
        if self.acciones:
            self.elegida = (self.elegida + paso) % len(self.acciones)
            self.update()

    def accion_elegida(self):
        return self.acciones[self.elegida] if self.acciones else None

    # --- Ratón ----------------------------------------------------------------

    def mouseMoveEvent(self, evento):
        punto = posicion_local(evento)
        if (self._pulsada is not None and evento.buttons() & Qt.LeftButton
                and (punto - self._inicio_arrastre).manhattanLength() >= QtWidgets.QApplication.startDragDistance()):
            accion = self.acciones[self._pulsada]
            self._pulsada = None
            arrastre = QtGui.QDrag(self)
            arrastre.setMimeData(datos_mime(accion["boton"]))
            mapa = self._icono(accion, 18)[0]
            if mapa is not None:
                arrastre.setPixmap(mapa)
            arrastre.exec(Qt.CopyAction)
            return
        fila = self.fila_en(punto)
        if fila is not None and fila != self.elegida:
            self.elegida = fila
            self.update()

    def mousePressEvent(self, evento):
        fila = self.fila_en(posicion_local(evento))
        if evento.button() == Qt.LeftButton and fila is not None:
            self._pulsada = fila
            self._inicio_arrastre = posicion_local(evento)
        evento.accept()

    def mouseReleaseEvent(self, evento):
        fila = self.fila_en(posicion_local(evento))
        pulsada, self._pulsada = self._pulsada, None
        if evento.button() == Qt.LeftButton and fila is not None and fila == pulsada:
            self._al_elegir(self.acciones[fila])

    # --- Dibujo ---------------------------------------------------------------

    def icono_de(self, accion):
        """El icono de la herramienta: el del botón, el de Maya para ese comando o "" si no tiene."""
        icono = accion["boton"].get("icono", "")
        if not icono and accion["boton"].get("tipo") == "comando" and self.buscar_icono is not None:
            try:
                icono = self.buscar_icono(accion["nombre"]) or ""
            except Exception:  # sin icono la fila se ve igual de bien
                icono = ""
        return icono

    def _icono(self, accion, lado):
        """(pixmap o None, True si es un icono de Maya a color que no se recolorea)."""
        icono = self.icono_de(accion)
        propio = iconos.es_imagen(icono)
        escala = self.devicePixelRatioF()
        clave = (icono, lado, escala)
        if clave not in self._iconos:
            self._iconos[clave] = pixmap_icono(icono, lado, escala, "#ececec") if icono else None
        return self._iconos[clave], propio

    def paintEvent(self, evento):
        pintor = QtGui.QPainter(self)
        pintor.setRenderHint(QtGui.QPainter.Antialiasing)
        pintor.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        rect = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        pintor.setPen(QtGui.QPen(COLOR_BORDE_FONDO, 1.0))
        pintor.setBrush(COLOR_LISTA)
        pintor.drawRoundedRect(rect, 12, 12)

        fuente = QtGui.QFont(self.font())
        fuente.setPixelSize(13)
        negrita = QtGui.QFont(fuente)
        negrita.setBold(True)
        pequena = QtGui.QFont(fuente)
        pequena.setPixelSize(11)

        if self.titulo:
            titulo = QtGui.QFont(pequena)
            titulo.setPixelSize(10)
            titulo.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 0.8)
            pintor.setFont(titulo)
            pintor.setPen(COLOR_PISTA)
            pintor.drawText(QtCore.QRectF(14, MARGEN, self.width() - 28, 22), Qt.AlignVCenter,
                            self.titulo.upper())
        if not self.acciones:
            if self.vacio:
                pintor.setFont(fuente)
                pintor.setPen(COLOR_PISTA)
                pintor.drawText(QtCore.QRectF(14, self._y0(), self.width() - 28, ALTO_FILA), Qt.AlignVCenter,
                                self.vacio)
            pintor.end()
            return

        ancho_texto = self.width() - 2 * MARGEN - 46
        metrica = QtGui.QFontMetrics(pequena)
        for i, accion in enumerate(self.acciones):
            y = self._y0() + i * ALTO_FILA
            fila = QtCore.QRectF(MARGEN, y, self.width() - 2 * MARGEN, ALTO_FILA)
            elegida = i == self.elegida
            if elegida:
                pintor.setPen(Qt.NoPen)
                pintor.setBrush(COLOR_ELEGIDO)
                pintor.drawRoundedRect(fila.adjusted(0, 1, 0, -1), 9, 9)
            # Icono en un círculo
            centro = QtCore.QPointF(fila.left() + 20, fila.center().y())
            pintor.setPen(Qt.NoPen)
            pintor.setBrush(QtGui.QColor(0, 0, 0, 30) if elegida else COLOR_CIRCULO)
            pintor.drawEllipse(centro, 12, 12)
            mapa, propio = self._icono(accion, 20 if iconos.es_imagen(self.icono_de(accion)) else 14)
            if mapa is not None and propio:
                # Icono de Maya a color, tal cual
                pintor.drawPixmap(QtCore.QRectF(centro.x() - 10, centro.y() - 10, 20, 20), mapa,
                                  QtCore.QRectF(mapa.rect()))
            elif mapa is not None:
                if elegida:
                    mapa = self._oscurecer(mapa)
                pintor.drawPixmap(QtCore.QRectF(centro.x() - 7, centro.y() - 7, 14, 14), mapa,
                                  QtCore.QRectF(mapa.rect()))
            else:
                # Sin icono: la inicial de la herramienta
                inicial = QtGui.QFont(negrita)
                inicial.setPixelSize(12)
                pintor.setFont(inicial)
                pintor.setPen(COLOR_TEXTO_ELEGIDO if elegida else COLOR_DETALLE)
                pintor.drawText(QtCore.QRectF(centro.x() - 12, centro.y() - 12, 24, 24), Qt.AlignCenter,
                                (accion["texto"] or "?")[:1].upper())
            # Texto con lo buscado en negrita
            x = fila.left() + 40
            pintor.setPen(COLOR_TEXTO_ELEGIDO if elegida else COLOR_TEXTO)
            hueco = ancho_texto - (metrica.horizontalAdvance(accion.get("atajo", "")) + 12 if accion.get("atajo") else 0)
            texto = QtGui.QFontMetrics(fuente).elidedText(accion["texto"], Qt.ElideRight, int(hueco))
            for trozo, marca in busqueda.partes_resaltadas(texto, self.consulta):
                pintor.setFont(negrita if marca else fuente)
                pintor.drawText(QtCore.QPointF(x, y + 17), trozo)
                x += QtGui.QFontMetrics(negrita if marca else fuente).horizontalAdvance(trozo)
            # Debajo: nombre en español, menú de Maya y nombre del comando
            detalle = " · ".join(p for p in (accion.get("traduccion", ""), accion["categoria"],
                                             accion["nombre"] if accion["nombre"] != accion["categoria"] else "")
                                 if p)
            # A la derecha: el atajo, si tiene
            atajo = accion.get("atajo", "")
            if atajo:
                pintor.setFont(pequena)
                pintor.setPen(COLOR_DETALLE_ELEGIDO if elegida else COLOR_PISTA)
                pintor.drawText(QtCore.QRectF(fila.left(), y, fila.width() - 10, 26),
                                Qt.AlignRight | Qt.AlignVCenter, atajo)
            pintor.setFont(pequena)
            pintor.setPen(COLOR_DETALLE_ELEGIDO if elegida else COLOR_DETALLE)
            detalle = QtGui.QFontMetrics(pequena).elidedText(detalle, Qt.ElideRight, int(ancho_texto))
            pintor.drawText(QtCore.QPointF(fila.left() + 40, y + 31), detalle)
        pintor.end()

    @staticmethod
    def _oscurecer(mapa):
        oscuro = QtGui.QPixmap(mapa.size())
        oscuro.setDevicePixelRatio(mapa.devicePixelRatio())
        oscuro.fill(Qt.transparent)
        pintor = QtGui.QPainter(oscuro)
        pintor.drawPixmap(0, 0, mapa)
        pintor.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
        pintor.fillRect(oscuro.rect(), QtGui.QColor(20, 20, 20))
        pintor.end()
        return oscuro


class Buscador(QtWidgets.QWidget):
    """La barra de búsqueda. Avisa con:

    - ``acciones()``: lista de acciones (ver ``busqueda``); se pide la primera vez.
    - ``al_ejecutar(accion, opciones=False)``: se eligió una acción (con Mayúsculas, ``opciones``).
    - ``recientes()``: las usadas hace poco.
    - ``al_terminar()``: se ejecutó o se pulsó Esc; devuelve el teclado a Maya.
    """

    def __init__(self, acciones, al_ejecutar, recientes=None, al_terminar=None, padre=None, buscar_icono=None):
        super(Buscador, self).__init__(padre)
        _ventana_flotante(self, acepta_foco=True)
        self.setObjectName("RadialBuscador")
        self.setWindowTitle("Radial")
        self.setFixedHeight(ALTO_CAMPO + 2)
        self.setFocusPolicy(Qt.NoFocus)
        self._editando = False  # True solo tras un clic en el campo
        self._acciones_fuente = acciones
        self._acciones = None
        self._al_ejecutar = al_ejecutar
        self._recientes = recientes or (lambda: [])
        self._al_terminar = al_terminar
        self._menu = None
        self.activo = True

        self.campo = QtWidgets.QLineEdit(self)
        self.campo.setPlaceholderText(t("buscador_pista"))
        self.campo.setFrame(False)
        self.campo.setFocusPolicy(Qt.ClickFocus)
        self.campo.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.campo.setStyleSheet("QLineEdit { background: transparent; border: none; color: #f2f2f2; "
                                 "font-size: 13px; selection-background-color: #5a6578; }")
        paleta = self.campo.palette()
        paleta.setColor(QtGui.QPalette.PlaceholderText, COLOR_PISTA)
        self.campo.setPalette(paleta)
        self.campo.textEdited.connect(self._buscar)
        self.campo.installEventFilter(self)
        self._lupa = None

        self.lista = ListaResultados(self.ejecutar, padre)
        self.lista.buscar_icono = buscar_icono

    # --- Seguir al menú -------------------------------------------------------

    def acompanar(self, menu):
        """Se pone debajo de ``menu`` y lo sigue."""
        if sigue_vivo(self._menu):
            self._menu.removeEventFilter(self)
        self._menu = menu
        if menu is not None:
            menu.installEventFilter(self)
        self.actualizar()

    def actualizar(self):
        """Se muestra u oculta según el menú y ``activo``."""
        if not sigue_vivo(self):  # llamada retrasada tras destruirlo
            return
        menu = self._menu if sigue_vivo(self._menu) else None
        if self.activo and menu is not None and menu.isVisible():
            self.colocar()
            self.show()
            self.raise_()
            if not self._editando and self.campo.hasFocus():
                self._soltar_teclado()
        else:
            self.cerrar_lista()
            self.hide()

    def _ancho(self):
        menu = self._menu
        if getattr(menu, "vertical", None) is None:
            return ANCHO_RADIAL
        if menu.vertical:
            return ANCHO_VERTICAL
        return max(ANCHO_MINIMO, menu.width())

    def colocar(self):
        menu = self._menu
        if not sigue_vivo(menu):
            return
        self.setFixedWidth(self._ancho())
        arriba = menu.mapToGlobal(QtCore.QPoint(0, 0))
        centro_x = arriba.x() + menu.width() // 2
        x = centro_x - self.width() // 2
        # El radial ya deja aire bajo el anillo (sitio para el punto abierto).
        separacion = 0 if getattr(menu, "vertical", None) is None else SEPARACION
        y = arriba.y() + menu.height() + separacion
        zona = self._zona(QtCore.QPoint(centro_x, y))
        if zona is not None and y + self.height() > zona.bottom():
            y = arriba.y() - self.height() - SEPARACION  # no cabe debajo: encima del menú
        self.move(x, y)
        self._colocar_lista()

    @staticmethod
    def _zona(punto):
        pantalla = QtGui.QGuiApplication.screenAt(punto) or QtGui.QGuiApplication.primaryScreen()
        return pantalla.availableGeometry() if pantalla is not None else None

    def _colocar_lista(self):
        lista = self.lista
        lista.setFixedWidth(max(self.width(), ANCHO_RADIAL))
        x = self.x() + (self.width() - lista.width()) // 2
        y = self.y() + self.height() + 4
        zona = self._zona(self.geometry().center())
        if zona is not None and y + lista.height() > zona.bottom():
            y = self.y() - lista.height() - 4  # se abre hacia arriba
        lista.move(x, y)

    def resizeEvent(self, evento):
        self.campo.setGeometry(34, 1, self.width() - 34 - 12, ALTO_CAMPO)
        super(Buscador, self).resizeEvent(evento)

    def eventFilter(self, objeto, evento):
        try:
            return self._filtrar(objeto, evento)
        except (AttributeError, RuntimeError):  # a medio destruir
            return False

    def _filtrar(self, objeto, evento):
        tipo = evento.type()
        if objeto is self._menu:
            if tipo in (QEvent.Move, QEvent.Resize, QEvent.Show):
                QtCore.QTimer.singleShot(0, self.actualizar)
            elif tipo == QEvent.Hide:
                self.cerrar_lista()
                self.hide()
            return False
        if objeto is self.campo:
            if tipo == QEvent.KeyPress:
                return self._tecla(evento)
            if tipo == QEvent.MouseButtonPress:
                self._editando = True
            elif tipo == QEvent.FocusIn:
                if not self._editando and evento.reason() != Qt.MouseFocusReason:
                    QtCore.QTimer.singleShot(0, self._soltar_teclado)  # no se pidió: se devuelve
                    return False
                self._editando = True
                self.update()
                self._buscar(self.campo.text())
            elif tipo == QEvent.FocusOut:
                self._editando = False
                self.update()
                QtCore.QTimer.singleShot(200, self._quizas_cerrar)
        return False

    def _tecla(self, evento):
        tecla = evento.key()
        if tecla in (Qt.Key_Down, Qt.Key_Up):
            self.lista.mover(1 if tecla == Qt.Key_Down else -1)
            return True
        if tecla in (Qt.Key_Return, Qt.Key_Enter):
            accion = self.lista.accion_elegida() if self.lista.isVisible() else None
            if accion is not None:
                self.ejecutar(accion, bool(evento.modifiers() & Qt.ShiftModifier))
            return True
        if tecla == Qt.Key_Escape:
            self.terminar()
            return True
        return False

    def _quizas_cerrar(self):
        if not sigue_vivo(self) or not sigue_vivo(self.lista):
            return
        if not self.campo.hasFocus() and not self.lista.underMouse():
            self.cerrar_lista()

    # --- Buscar y ejecutar ----------------------------------------------------

    def acciones(self):
        if self._acciones is None:
            try:
                self._acciones = list(self._acciones_fuente())
            except Exception:  # sin la lista de Maya el buscador no rompe nada
                self._acciones = []
        return self._acciones

    def olvidar_acciones(self):
        self._acciones = None

    def _buscar(self, texto):
        texto = texto.strip()
        if texto:
            recientes = [busqueda.clave(a) for a in self._recientes()]
            resultados = busqueda.buscar(self.acciones(), texto, recientes)
            self.lista.fijar(resultados, texto, vacio=t("buscador_nada", texto=texto))
        else:
            recientes = self._recientes()
            if not recientes:
                self.cerrar_lista()
                return
            self.lista.fijar(recientes, "", titulo=t("buscador_recientes"))
        self._colocar_lista()
        self.lista.show()
        self.lista.raise_()

    def cerrar_lista(self):
        if sigue_vivo(self.lista):
            self.lista.hide()

    def ejecutar(self, accion, opciones=None):
        """Lanza ``accion``. Con Mayúsculas (``opciones``) abre su ventana de opciones."""
        if opciones is None:
            opciones = bool(QtWidgets.QApplication.keyboardModifiers() & Qt.ShiftModifier)
        self.terminar()
        if opciones:
            self._al_ejecutar(accion, opciones=True)
        else:
            self._al_ejecutar(accion)

    def terminar(self):
        """Borra el texto, cierra el desplegable y devuelve el teclado a Maya."""
        self.campo.clear()
        self.cerrar_lista()
        self._soltar_teclado()

    def _soltar_teclado(self):
        if not sigue_vivo(self):
            return
        self._editando = False
        if self.campo.hasFocus():
            self.campo.clearFocus()
        if self._al_terminar:
            self._al_terminar()

    def mousePressEvent(self, evento):
        self._editando = True
        self.activateWindow()
        self.campo.setFocus(Qt.MouseFocusReason)
        evento.accept()

    def closeEvent(self, evento):
        self.lista.close()
        super(Buscador, self).closeEvent(evento)

    # --- Dibujo ---------------------------------------------------------------

    def paintEvent(self, evento):
        pintor = QtGui.QPainter(self)
        pintor.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, ALTO_CAMPO + 1)
        pintor.setPen(QtGui.QPen(COLOR_BORDE_ACTIVO if self.campo.hasFocus() else COLOR_BORDE_FONDO, 1.0))
        pintor.setBrush(COLOR_CAPSULA)
        pintor.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        if self._lupa is None:
            self._lupa = pixmap_icono("lupa", 14, self.devicePixelRatioF(), "#9aa0a8")
        if self._lupa is not None:
            pintor.drawPixmap(QtCore.QRectF(13, (ALTO_CAMPO + 2 - 14) / 2.0, 14, 14), self._lupa,
                              QtCore.QRectF(self._lupa.rect()))
        pintor.end()

