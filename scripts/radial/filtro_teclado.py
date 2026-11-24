"""Escucha el teclado de toda la aplicación y detecta el doble Tab.

No cambia ningún atajo de Maya. El primer Tab llega a Maya como siempre; si
el segundo llega a tiempo, el filtro se lo queda (Maya no lo ve) y avisa.

Qt manda cada pulsación como dos eventos (ShortcutOverride y KeyPress) y a
veces repite el KeyPress en los widgets padre. Todos llevan la misma marca de
tiempo, así que la decisión se toma una vez por pulsación y se aplica a todos.
"""

import ctypes
import sys
import time

from radial.detector_tab import DetectorDobleTab
from radial.qt import QtCore, QtWidgets, sigue_vivo

Qt = QtCore.Qt
QEvent = QtCore.QEvent

_TECLAS_MODIFICADORAS = {Qt.Key_Shift, Qt.Key_Control, Qt.Key_Meta, Qt.Key_Alt, Qt.Key_AltGr,
                         Qt.Key_CapsLock}
_TIPOS = (QEvent.ShortcutOverride, QEvent.KeyPress, QEvent.KeyRelease, QEvent.MouseButtonPress)
_WIDGETS_DE_TEXTO = (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit,
                     QtWidgets.QAbstractSpinBox)


def escribiendo():
    """True si el foco está en un sitio donde se escribe texto."""
    foco = QtWidgets.QApplication.focusWidget()
    if foco is None:
        return False
    if isinstance(foco, _WIDGETS_DE_TEXTO):
        return True
    return isinstance(foco, QtWidgets.QComboBox) and foco.isEditable()


def _ahora_ms():
    return int(time.monotonic() * 1000)


_consulta_tab = []


def _preparar_consulta_tab():
    """La función del sistema que dice si Tab está pulsada ahora (o None si no hay)."""
    try:
        if sys.platform == "darwin":
            ruta = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
            funcion = ctypes.cdll.LoadLibrary(ruta).CGEventSourceKeyState
            funcion.restype = ctypes.c_bool
            funcion.argtypes = [ctypes.c_int32, ctypes.c_uint16]
            return lambda: bool(funcion(0, 48))  # sesión combinada, kVK_Tab
        if sys.platform == "win32":
            funcion = ctypes.windll.user32.GetAsyncKeyState
            return lambda: bool(funcion(0x09) & 0x8000)  # VK_TAB
    except Exception:  # noqa: BLE001 (sin la función se usan solo los eventos de Qt)
        pass
    return None


def tab_pulsado():
    """True o False si el sistema dice si la tecla Tab está pulsada ahora; None si no se puede saber."""
    if not _consulta_tab:
        _consulta_tab.append(_preparar_consulta_tab())
    consulta = _consulta_tab[0]
    if consulta is None:
        return None
    try:
        return consulta()
    except Exception:  # noqa: BLE001
        return None


class FiltroTeclado(QtCore.QObject):
    """Filtro de eventos para ``QApplication``.

    - ``puede_contar(es_segundo)`` dice si un Tab cuenta en este momento.
      ``es_segundo`` es True cuando este Tab completaría un doble Tab.
    - ``al_doble_tab()`` se llama (justo después) cuando hay doble Tab.
    - ``al_soltar_tab()`` se llama al soltar ese segundo Tab (para el gesto).

    Mientras el segundo Tab sigue pulsado, su auto-repetición y su soltar también
    se los queda el filtro: Maya no ve nada de esa pulsación, así que mantener Tab
    (que en Maya es suyo) solo cuenta cuando no hay doble Tab.
    """

    def __init__(self, puede_contar, al_doble_tab, ventana_ms=250, padre=None, al_soltar_tab=None):
        super(FiltroTeclado, self).__init__(padre)
        self.detector = DetectorDobleTab(ventana_ms)
        self._puede_contar = puede_contar
        self._al_doble_tab = al_doble_tab
        self._sello = None
        self._momento_decision = None
        self._quedarse = False
        self._foco_primer_tab = None
        self._objetivos = []
        self._al_soltar_tab = al_soltar_tab
        self.manteniendo = False  # el segundo Tab del doble Tab sigue pulsado
        self.ultimo_tab = 0  # cuándo llegó el último evento de ese Tab (también su auto-repetición)
        self._tragar_soltar = False

    def instalar(self, ventanas=None):
        """Empieza a escuchar.

        En Maya se escuchan solo sus ventanas (``ventanas``: objetos QWindow), no
        toda la aplicación: un filtro de Python en la QApplication recibe todos
        los eventos de Maya, también los de objetos a medio destruir, y Maya se
        puede cerrar de golpe. Sin ``ventanas`` (pruebas) se usa la aplicación.
        """
        self._objetivos = []
        if ventanas is None:
            ventanas = [QtWidgets.QApplication.instance()]
        for ventana in ventanas:
            self.escuchar(ventana)

    def escuchar(self, objeto):
        """Añade una ventana más (por ejemplo, un panel separado de la ventana principal)."""
        if not sigue_vivo(objeto) or any(o is objeto for o in self._objetivos):
            return
        objeto.installEventFilter(self)
        self._objetivos.append(objeto)

    def quitar(self):
        for objeto in getattr(self, "_objetivos", []):
            if sigue_vivo(objeto):
                objeto.removeEventFilter(self)
        self._objetivos = []

    def eventFilter(self, objeto, evento):
        tipo = evento.type()
        if tipo not in _TIPOS:
            return False
        if tipo in (QEvent.ShortcutOverride, QEvent.KeyPress, QEvent.KeyRelease):
            try:
                return self._tecla(tipo, evento)
            except Exception:  # un error aquí no puede bloquear el teclado de Maya
                return False
        if tipo == QEvent.MouseButtonPress:
            self.detector.olvidar()
        return False

    def _misma_pulsacion(self, sello, ahora):
        if sello:
            return sello == self._sello
        # Sin marca de tiempo: los eventos de una misma pulsación llegan seguidos.
        return self._momento_decision is not None and ahora - self._momento_decision < 15

    def _tecla(self, tipo, evento):
        if tipo == QEvent.KeyRelease:
            return self._soltar(evento)
        if self.manteniendo and evento.key() == Qt.Key_Tab and evento.isAutoRepeat():
            self.ultimo_tab = _ahora_ms()
            evento.accept()
            return True  # la auto-repetición del segundo Tab no llega a Maya
        if evento.key() != Qt.Key_Tab:
            if tipo == QEvent.KeyPress and evento.key() not in _TECLAS_MODIFICADORAS:
                self.detector.olvidar()
            return False

        ahora = _ahora_ms()
        sello = evento.timestamp()
        if not self._misma_pulsacion(sello, ahora):
            self.manteniendo = False  # una pulsación nueva: el gesto anterior ya acabó
            self._tragar_soltar = False
            self._sello = sello
            self._momento_decision = ahora
            self._quedarse = self._decidir(evento, sello or ahora)
        if self._quedarse:
            evento.accept()
            return True
        return False

    def _decidir(self, evento, momento):
        modificadores = evento.modifiers() & ~Qt.KeypadModifier
        if evento.isAutoRepeat() or modificadores != Qt.NoModifier:
            self.detector.olvidar()
            return False
        es_segundo = self.detector.esperando(momento)
        if not es_segundo:
            # Se recuerda el foco: el primer Tab puede moverlo y al abrir el menú se devuelve.
            self._foco_primer_tab = QtWidgets.QApplication.focusWidget()
        if not self.detector.pulsar(momento, self._puede_contar(es_segundo)):
            return False
        foco = self._foco_primer_tab
        self._foco_primer_tab = None
        self.manteniendo = True
        self.ultimo_tab = _ahora_ms()
        QtCore.QTimer.singleShot(0, lambda: self._avisar(foco))
        return True

    def _soltar(self, evento):
        if evento.key() != Qt.Key_Tab or not (self.manteniendo or self._tragar_soltar):
            return False
        if not evento.isAutoRepeat():
            avisar = self.manteniendo
            self.manteniendo = False
            self._tragar_soltar = False
            if avisar and self._al_soltar_tab is not None:
                QtCore.QTimer.singleShot(0, self._al_soltar_tab)
        evento.accept()
        return True

    def terminar(self):
        """Da por soltado el segundo Tab sin esperar a su evento (que a veces no llega).

        Si el evento llega después, el filtro se lo sigue quedando: Maya no ve un
        Tab soltado sin haberlo visto pulsado.
        """
        if self.manteniendo:
            self.manteniendo = False
            self._tragar_soltar = True

    def _avisar(self, foco):
        if sigue_vivo(foco) and QtWidgets.QApplication.focusWidget() is not foco:
            foco.setFocus(Qt.OtherFocusReason)
        self._al_doble_tab()
