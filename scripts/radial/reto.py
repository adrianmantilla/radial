"""Modo reto: practicar los atajos de teclado de las herramientas que más usas con Radial.

Radial cuenta cuántas veces lanzas cada comando. El reto pregunta el atajo de los
que más usas (y que tienen atajo en Maya): pulsas las teclas y te dice si está bien.
La idea es que el menú enseñe a no necesitar el menú.

``preguntas()``, ``de_qt()`` e ``iguales()`` no dependen de Maya ni de Qt; ``dialogo()`` sí de Qt.
"""

import random
import sys

PREGUNTAS = 8
# Al lanzar un comando con atajo estas veces desde Radial, se recuerda su atajo
AVISOS = (3, 10, 25)

# Si aún no has usado nada con atajo, se practica con estos (los de siempre de Maya)
BASICOS = ("PolyExtrude", "CenterPivot", "FreezeTransformations", "DeleteHistory", "Duplicate", "Group",
           "SelectAll", "InvertSelection", "FrameSelected", "Undo", "Redo", "SaveScene", "CreatePolygonCube",
           "SmoothPolygon", "ShowManipulators", "MoveTool", "RotateTool", "ScaleTool", "SelectToggleMode",
           "ToggleIsolateSelect", "SetKeyTranslate", "InsertEdgeLoopTool", "MultiCutTool")


def registrar_uso(usos, comando):
    """Suma un uso de ``comando`` a ``usos`` (``{comando: veces}``). Devuelve las veces."""
    usos = usos if isinstance(usos, dict) else {}
    usos[comando] = int(usos.get(comando, 0)) + 1
    return usos[comando]


def preguntas(usos, atajos, cantidad=PREGUNTAS, azar=None):
    """Lista de (comando, atajo) para el reto: primero los más usados, luego algunos básicos."""
    azar = azar or random.Random()
    usados = sorted((c for c in (usos or {}) if atajos.get(c)), key=lambda c: (-int(usos[c]), c))
    elegidos = usados[:cantidad]
    basicos = [c for c in BASICOS if atajos.get(c) and c not in elegidos]
    azar.shuffle(basicos)
    elegidos += basicos[:max(0, cantidad - len(elegidos))]
    azar.shuffle(elegidos)
    return [(c, atajos[c]) for c in elegidos]


def _partes(texto):
    trozos = [p for p in (texto or "").replace(" ", "").split("+") if p]
    if not trozos:
        return None
    modificadores = frozenset(p.upper() for p in trozos[:-1])
    return modificadores, trozos[-1].upper()


def de_qt(texto, mac=None):
    """Lo que da ``QKeySequence.toString()`` («Ctrl+Shift+E») escrito como los atajos de Maya («Ctrl+Mayús+E»).

    «Mayús» sale en el idioma de la interfaz, igual que en los atajos que lee ``fuentes_maya``.

    En macOS, Qt llama «Ctrl» a Cmd y «Meta» a Control.
    """
    mac = sys.platform == "darwin" if mac is None else mac
    partes = _partes(texto)
    if partes is None:
        return ""
    modificadores, tecla = partes
    nombres = []
    if ("META" in modificadores) if mac else ("CTRL" in modificadores):
        nombres.append("Ctrl")
    if "ALT" in modificadores:
        nombres.append("Alt")
    if mac and "CTRL" in modificadores:
        nombres.append("Cmd")
    if "SHIFT" in modificadores:
        from radial.i18n import t
        nombres.append(t("tecla_mayus"))
    return "+".join(nombres + [tecla])


def iguales(atajo, pulsado):
    """True si ``pulsado`` (ya escrito como en Maya, con ``de_qt``) es el atajo ``atajo``."""
    a, b = _partes(atajo), _partes(pulsado)
    return a is not None and a == b


# --- Ventana (Qt) ----------------------------------------------------------------

def dialogo(lista, nombres=None, padre=None):
    """Ventana del reto con ``lista`` de (comando, atajo). ``nombres`` da el nombre legible de un comando."""
    from radial.i18n import t
    from radial.qt import QtCore, QtGui, QtWidgets
    Qt = QtCore.Qt
    nombres = nombres or (lambda comando: comando)

    class DialogoReto(QtWidgets.QDialog):
        def __init__(self):
            super(DialogoReto, self).__init__(padre)
            self.setWindowTitle(t("reto_titulo"))
            self.setObjectName("RadialReto")
            self.setMinimumWidth(420)
            self.lista = list(lista)
            self.indice = 0
            self.aciertos = 0
            self.fallos = []
            capa = QtWidgets.QVBoxLayout(self)
            self.progreso = QtWidgets.QLabel()
            self.progreso.setEnabled(False)
            capa.addWidget(self.progreso)
            self.pregunta = QtWidgets.QLabel()
            letra = self.pregunta.font()
            letra.setPixelSize(18)
            letra.setBold(True)
            self.pregunta.setFont(letra)
            self.pregunta.setWordWrap(True)
            capa.addWidget(self.pregunta)
            ayuda = QtWidgets.QLabel(t("reto_ayuda"))
            ayuda.setWordWrap(True)
            capa.addWidget(ayuda)
            self.teclas = QtWidgets.QKeySequenceEdit()
            if hasattr(self.teclas, "setMaximumSequenceLength"):
                self.teclas.setMaximumSequenceLength(1)
            self.teclas.editingFinished.connect(self._comprobar)
            capa.addWidget(self.teclas)
            self.resultado = QtWidgets.QLabel()
            self.resultado.setWordWrap(True)
            capa.addWidget(self.resultado)
            pie = QtWidgets.QHBoxLayout()
            self.saltar = QtWidgets.QPushButton(t("reto_saltar"))
            self.siguiente = QtWidgets.QPushButton(t("reto_siguiente"))
            cerrar = QtWidgets.QPushButton(t("boton_cerrar"))
            pie.addWidget(self.saltar)
            pie.addStretch(1)
            pie.addWidget(cerrar)
            pie.addWidget(self.siguiente)
            capa.addLayout(pie)
            self.saltar.clicked.connect(lambda *_: self._fallar(saltada=True))
            self.siguiente.clicked.connect(self._avanzar)
            cerrar.clicked.connect(self.close)
            self._preguntar()

        def actual(self):
            return self.lista[self.indice] if self.indice < len(self.lista) else None

        def _preguntar(self):
            actual = self.actual()
            self.teclas.clear()
            self.resultado.setText("")
            self.siguiente.setEnabled(False)
            if actual is None:
                self.progreso.setText("")
                self.pregunta.setText(t("reto_final", aciertos=self.aciertos, total=len(self.lista)))
                repasar = ", ".join("{} ({})".format(nombres(c), a) for c, a in self.fallos)
                self.resultado.setText(t("reto_repasar", lista=repasar) if repasar else t("reto_perfecto"))
                self.teclas.setEnabled(False)
                self.saltar.setEnabled(False)
                return
            self.progreso.setText(t("reto_progreso", numero=self.indice + 1, total=len(self.lista),
                                    aciertos=self.aciertos))
            self.pregunta.setText(t("reto_pregunta", nombre=nombres(actual[0])))
            self.teclas.setEnabled(True)
            self.saltar.setEnabled(True)
            self.teclas.setFocus(Qt.OtherFocusReason)

        def responder(self, pulsado):
            """Comprueba ``pulsado`` (como en Maya: «Ctrl+E»). True si acierta."""
            actual = self.actual()
            if actual is None or self.siguiente.isEnabled():
                return None
            if iguales(actual[1], pulsado):
                self.aciertos += 1
                self.resultado.setText("✔ " + t("reto_bien", atajo=actual[1]))
                self.resultado.setStyleSheet("color: #7fd1a6;")
                self.teclas.setEnabled(False)
                self.saltar.setEnabled(False)
                self.siguiente.setEnabled(True)
                self.siguiente.setDefault(True)
                return True
            self.resultado.setText("✖ " + t("reto_mal", pulsado=pulsado))
            self.resultado.setStyleSheet("color: #e8826e;")
            self.teclas.clear()
            return False

        def _comprobar(self):
            secuencia = self.teclas.keySequence()
            texto = secuencia.toString(QtGui.QKeySequence.PortableText)
            if texto:
                self.responder(de_qt(texto))

        def _fallar(self, saltada=False):
            actual = self.actual()
            if actual is None:
                return
            self.fallos.append(actual)
            self.resultado.setText(t("reto_era", atajo=actual[1]))
            self.resultado.setStyleSheet("")
            self.teclas.setEnabled(False)
            self.saltar.setEnabled(False)
            self.siguiente.setEnabled(True)
            self.siguiente.setDefault(True)

        def _avanzar(self, *_):
            self.indice += 1
            self._preguntar()

    return DialogoReto()
