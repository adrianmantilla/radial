"""Ventana de ajustes: forma del menú, tamaño, opacidad y velocidad del doble Tab.

Los cambios se ven al momento en el menú, que se muestra mientras la ventana
está abierta. El tamaño y la opacidad se guardan con el radial; la forma y la
velocidad son del usuario.
"""

from radial import detector_tab as dt
from radial import radiales as rd
from radial.i18n import t
from radial.qt import QtCore, QtWidgets

Qt = QtCore.Qt

# clave, texto, escala del deslizador (valor = posición / escala), unidad
DESLIZADORES = (
    ("radio", "ajustes_radio", 1, "px"),
    ("punto", "ajustes_punto", 2, "px"),
    ("abierto", "ajustes_abierto", 1, "px"),
    ("pill_boton", "ajustes_pill_boton", 1, "px"),
    ("opacidad", "ajustes_opacidad", 100, "%"),
)


class Deslizador(QtWidgets.QWidget):
    cambiado = QtCore.Signal(float)

    def __init__(self, minimo, maximo, escala, unidad, padre=None):
        super(Deslizador, self).__init__(padre)
        self.escala, self.unidad = escala, unidad
        capa = QtWidgets.QHBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        self.barra = QtWidgets.QSlider(Qt.Horizontal)
        self.barra.setRange(int(round(minimo * escala)), int(round(maximo * escala)))
        self.etiqueta = QtWidgets.QLabel()
        self.etiqueta.setMinimumWidth(56)
        self.etiqueta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        capa.addWidget(self.barra, 1)
        capa.addWidget(self.etiqueta)
        self.barra.valueChanged.connect(self._movido)

    def valor(self):
        return self.barra.value() / float(self.escala)

    def fijar(self, valor):
        self.barra.blockSignals(True)
        self.barra.setValue(int(round(valor * self.escala)))
        self.barra.blockSignals(False)
        self._rotular()

    def _rotular(self):
        valor = self.valor()
        if self.unidad == "%":
            self.etiqueta.setText("{:.0f} %".format(valor * 100))
        elif self.escala == 1:
            self.etiqueta.setText("{:.0f} {}".format(valor, self.unidad))
        else:
            self.etiqueta.setText("{:g} {}".format(valor, self.unidad))

    def _movido(self, *_):
        self._rotular()
        self.cambiado.emit(self.valor())


class VentanaAjustes(QtWidgets.QDialog):
    """Avisa con ``al_apariencia(dict)``, ``al_forma(forma, vertical)`` y ``al_velocidad(ms)``."""

    def __init__(self, apariencia, forma, vertical, ventana_ms, al_apariencia=None, al_forma=None,
                 al_velocidad=None, padre=None):
        super(VentanaAjustes, self).__init__(padre)
        self.setWindowTitle(t("ajustes_titulo"))
        self.setObjectName("RadialAjustes")
        self.setMinimumWidth(420)
        self._al_apariencia = al_apariencia
        self._al_forma = al_forma
        self._al_velocidad = al_velocidad
        self.apariencia = rd.normalizar_apariencia(apariencia)

        capa = QtWidgets.QVBoxLayout(self)
        ayuda = QtWidgets.QLabel(t("ajustes_ayuda"))
        ayuda.setWordWrap(True)
        capa.addWidget(ayuda)

        formulario = QtWidgets.QFormLayout()
        capa.addLayout(formulario)

        self.forma_radial = QtWidgets.QRadioButton(t("forma_radial"))
        self.forma_pill = QtWidgets.QRadioButton(t("forma_pill"))
        fila = QtWidgets.QHBoxLayout()
        fila.addWidget(self.forma_radial)
        fila.addWidget(self.forma_pill)
        fila.addStretch(1)
        formulario.addRow(t("ajustes_forma"), fila)
        grupo_forma = QtWidgets.QButtonGroup(self)
        grupo_forma.addButton(self.forma_radial)
        grupo_forma.addButton(self.forma_pill)

        self.horizontal = QtWidgets.QRadioButton(t("pill_horizontal"))
        self.vertical = QtWidgets.QRadioButton(t("pill_vertical"))
        fila = QtWidgets.QHBoxLayout()
        fila.addWidget(self.horizontal)
        fila.addWidget(self.vertical)
        fila.addStretch(1)
        formulario.addRow(t("ajustes_orientacion"), fila)
        grupo_orientacion = QtWidgets.QButtonGroup(self)
        grupo_orientacion.addButton(self.horizontal)
        grupo_orientacion.addButton(self.vertical)

        self.deslizadores = {}
        self._filas = {}
        for clave, texto, escala, unidad in DESLIZADORES:
            minimo, maximo, _ = rd.APARIENCIA[clave]
            deslizador = Deslizador(minimo, maximo, escala, unidad)
            deslizador.cambiado.connect(lambda valor, c=clave: self._apariencia_cambiada(c, valor))
            etiqueta = QtWidgets.QLabel(t(texto))
            formulario.addRow(etiqueta, deslizador)
            self.deslizadores[clave] = deslizador
            self._filas[clave] = (etiqueta, deslizador)

        self.velocidad = Deslizador(dt.VENTANA_MINIMA_MS, dt.VENTANA_MAXIMA_MS, 1, "ms")
        self.velocidad.barra.setSingleStep(10)
        self.velocidad.barra.setPageStep(50)
        self.velocidad.cambiado.connect(lambda valor: self._al_velocidad and self._al_velocidad(int(valor)))
        formulario.addRow(t("ajustes_velocidad"), self.velocidad)
        nota = QtWidgets.QLabel(t("ajustes_velocidad_ayuda"))
        nota.setWordWrap(True)
        nota.setEnabled(False)
        formulario.addRow("", nota)

        pie = QtWidgets.QHBoxLayout()
        restaurar = QtWidgets.QPushButton(t("boton_restaurar_valores"))
        cerrar = QtWidgets.QPushButton(t("boton_cerrar"))
        cerrar.setDefault(True)
        pie.addWidget(restaurar)
        pie.addStretch(1)
        pie.addWidget(cerrar)
        capa.addLayout(pie)

        self.fijar(self.apariencia, forma, vertical, ventana_ms)
        self.forma_radial.toggled.connect(self._forma_cambiada)
        self.vertical.toggled.connect(self._forma_cambiada)
        restaurar.clicked.connect(self._restaurar)
        cerrar.clicked.connect(self.close)

    def fijar(self, apariencia, forma, vertical, ventana_ms):
        self.apariencia = rd.normalizar_apariencia(apariencia)
        for clave, deslizador in self.deslizadores.items():
            deslizador.fijar(self.apariencia[clave])
        for boton, valor in ((self.forma_radial, forma == "radial"), (self.forma_pill, forma == "pill"),
                             (self.horizontal, not vertical), (self.vertical, vertical)):
            boton.blockSignals(True)
            boton.setChecked(valor)
            boton.blockSignals(False)
        self.velocidad.fijar(dt.limitar_ventana(ventana_ms))
        self._mostrar_filas()

    def forma(self):
        return "pill" if self.forma_pill.isChecked() else "radial"

    def _mostrar_filas(self):
        pill = self.forma() == "pill"
        for clave in ("radio", "punto", "abierto"):
            for widget in self._filas[clave]:
                widget.setEnabled(not pill)
        for widget in self._filas["pill_boton"]:
            widget.setEnabled(pill)
        self.horizontal.setEnabled(pill)
        self.vertical.setEnabled(pill)

    def _apariencia_cambiada(self, clave, valor):
        self.apariencia[clave] = valor
        self.apariencia = rd.normalizar_apariencia(self.apariencia)
        if self._al_apariencia:
            self._al_apariencia(dict(self.apariencia))

    def _forma_cambiada(self, *_):
        self._mostrar_filas()
        if self._al_forma:
            self._al_forma(self.forma(), self.vertical.isChecked())

    def _restaurar(self):
        por_defecto = rd.normalizar_apariencia({})
        self.fijar(por_defecto, self.forma(), self.vertical.isChecked(), dt.VENTANA_POR_DEFECTO_MS)
        if self._al_apariencia:
            self._al_apariencia(dict(por_defecto))
        if self._al_velocidad:
            self._al_velocidad(dt.VENTANA_POR_DEFECTO_MS)
