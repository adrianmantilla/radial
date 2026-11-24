"""Escucha el teclado de toda la aplicación y detecta el doble Tab.

No cambia ningún atajo de Maya. El primer Tab llega a Maya como siempre; si
el segundo llega a tiempo, el filtro se lo queda (Maya no lo ve) y avisa.

Qt manda cada pulsación como dos eventos (ShortcutOverride y KeyPress) y a
veces repite el KeyPress en los widgets padre. Todos llevan la misma marca de
tiempo, así que la decisión se toma una vez por pulsación y se aplica a todos.
"""

import time

from radial.detector_tab import DetectorDobleTab
from radial.qt import QtCore, QtWidgets, sigue_vivo

Qt = QtCore.Qt
QEvent = QtCore.QEvent

_TECLAS_MODIFICADORAS = {Qt.Key_Shift, Qt.Key_Control, Qt.Key_Meta, Qt.Key_Alt, Qt.Key_AltGr,
                         Qt.Key_CapsLock}
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


class FiltroTeclado(QtCore.QObject):
    """Filtro de eventos para ``QApplication``.

    - ``puede_contar(es_segundo)`` dice si un Tab cuenta en este momento.
      ``es_segundo`` es True cuando este Tab completaría un doble Tab.
    - ``al_doble_tab()`` se llama (justo después) cuando hay doble Tab.
    """

    def __init__(self, puede_contar, al_doble_tab, ventana_ms=250, padre=None):
        super(FiltroTeclado, self).__init__(padre)
        self.detector = DetectorDobleTab(ventana_ms)
        self._puede_contar = puede_contar
        self._al_doble_tab = al_doble_tab
        self._sello = None
        self._momento_decision = None
        self._quedarse = False
        self._foco_primer_tab = None

    def instalar(self):
        QtWidgets.QApplication.instance().installEventFilter(self)

    def quitar(self):
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)

    def eventFilter(self, objeto, evento):
        tipo = evento.type()
        if tipo == QEvent.ShortcutOverride or tipo == QEvent.KeyPress:
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
        if evento.key() != Qt.Key_Tab:
            if tipo == QEvent.KeyPress and evento.key() not in _TECLAS_MODIFICADORAS:
                self.detector.olvidar()
            return False

        ahora = _ahora_ms()
        sello = evento.timestamp()
        if not self._misma_pulsacion(sello, ahora):
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
        QtCore.QTimer.singleShot(0, lambda: self._avisar(foco))
        return True

    def _avisar(self, foco):
        if sigue_vivo(foco) and QtWidgets.QApplication.focusWidget() is not foco:
            foco.setFocus(Qt.OtherFocusReason)
        self._al_doble_tab()
