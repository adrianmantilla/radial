"""Ventana de ajustes: forma del menú, tamaño, opacidad y velocidad del doble Tab.

Los cambios se ven al momento en el menú, que se muestra mientras la ventana
está abierta. El tamaño y la opacidad se guardan con el radial; la forma y la
velocidad son del usuario.
"""

from radial import automatico
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


OPCIONES = ("carpetas", "automatico", "aprendizaje")


class DialogoReglas(QtWidgets.QDialog):
    """Qué radial va con cada workspace y con cada modo de selección (radial automático)."""

    def __init__(self, reglas, workspaces, radiales, padre=None):
        super(DialogoReglas, self).__init__(padre)
        self.setWindowTitle(t("reglas_titulo"))
        self.setObjectName("RadialReglas")
        self.setMinimumWidth(460)
        capa = QtWidgets.QVBoxLayout(self)
        ayuda = QtWidgets.QLabel(t("reglas_ayuda"))
        ayuda.setWordWrap(True)
        capa.addWidget(ayuda)
        self.combos = {}
        reglas = dict(reglas or {})
        nombres = list(workspaces or [])
        for clave in sorted(reglas):
            if clave.startswith("ws:") and clave[3:] not in nombres:
                nombres.append(clave[3:])
        for titulo, claves in ((t("reglas_workspaces"), [("ws:" + n, n) for n in nombres]),
                               (t("reglas_modos"), [("sel:" + m, t("modo_" + m)) for m in automatico.MODOS])):
            grupo = QtWidgets.QGroupBox(titulo)
            formulario = QtWidgets.QFormLayout(grupo)
            for clave, texto in claves:
                combo = QtWidgets.QComboBox()
                combo.addItem(t("reglas_ninguno"), "")
                for identificador, nombre in radiales:
                    combo.addItem(nombre, identificador)
                indice = combo.findData(reglas.get(clave, ""))
                combo.setCurrentIndex(max(indice, 0))
                formulario.addRow(texto, combo)
                self.combos[clave] = combo
            capa.addWidget(grupo)
        pie = QtWidgets.QHBoxLayout()
        restaurar = QtWidgets.QPushButton(t("boton_restaurar_valores"))
        cancelar = QtWidgets.QPushButton(t("boton_cancelar"))
        aceptar = QtWidgets.QPushButton(t("boton_aceptar"))
        aceptar.setDefault(True)
        pie.addWidget(restaurar)
        pie.addStretch(1)
        pie.addWidget(cancelar)
        pie.addWidget(aceptar)
        capa.addLayout(pie)
        restaurar.clicked.connect(self._restaurar)
        cancelar.clicked.connect(self.reject)
        aceptar.clicked.connect(self.accept)

    def _restaurar(self):
        from radial.ajustes import REGLAS_POR_DEFECTO
        for clave, combo in self.combos.items():
            combo.setCurrentIndex(max(combo.findData(REGLAS_POR_DEFECTO.get(clave, "")), 0))

    def reglas(self):
        return {clave: combo.currentData() for clave, combo in self.combos.items() if combo.currentData()}


class VentanaAjustes(QtWidgets.QDialog):
    """Avisa con ``al_apariencia(dict)``, ``al_forma(forma, vertical)``, ``al_velocidad(ms)``,
    ``al_buscador(bool)``, ``al_opcion(clave, valor)`` (carpetas, automatico, aprendizaje,
    carpeta_clase) y ``al_reglas()`` (abrir las reglas del radial automático)."""

    def __init__(self, apariencia, forma, vertical, ventana_ms, al_apariencia=None, al_forma=None,
                 al_velocidad=None, padre=None, buscador=True, al_buscador=None, opciones=None,
                 al_opcion=None, al_reglas=None, extra=None, al_extra=None):
        super(VentanaAjustes, self).__init__(padre)
        self.setWindowTitle(t("ajustes_titulo"))
        self.setObjectName("RadialAjustes")
        self.setMinimumWidth(520)
        self._al_apariencia = al_apariencia
        self._al_forma = al_forma
        self._al_velocidad = al_velocidad
        self._al_buscador = al_buscador
        self._al_opcion = al_opcion
        self._al_reglas = al_reglas
        self._al_extra = al_extra
        opciones = dict(opciones or {})
        self.apariencia = rd.normalizar_apariencia(apariencia)

        exterior = QtWidgets.QVBoxLayout(self)
        self.pestanas = QtWidgets.QTabWidget()
        exterior.addWidget(self.pestanas)
        pagina = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(pagina)
        self.pestanas.addTab(pagina, t("ajustes_pestana_menu"))
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

        self.buscador = QtWidgets.QCheckBox(t("ajustes_buscador_casilla"))
        self.buscador.setChecked(bool(buscador))
        self.buscador.toggled.connect(lambda valor: self._al_buscador and self._al_buscador(bool(valor)))
        formulario.addRow(t("ajustes_buscador"), self.buscador)

        capa.addStretch(1)
        grupo = QtWidgets.QWidget()
        opciones_capa = QtWidgets.QVBoxLayout(grupo)
        self.casillas = {}
        for clave in OPCIONES:
            casilla = QtWidgets.QCheckBox(t("ajustes_" + clave))
            casilla.setChecked(bool(opciones.get(clave, clave == "aprendizaje")))
            casilla.toggled.connect(lambda valor, c=clave: self._opcion(c, bool(valor)))
            self.casillas[clave] = casilla
            if clave == "automatico":
                fila = QtWidgets.QHBoxLayout()
                fila.addWidget(casilla)
                fila.addStretch(1)
                self.boton_reglas = QtWidgets.QPushButton(t("ajustes_reglas"))
                self.boton_reglas.clicked.connect(lambda *_: self._al_reglas and self._al_reglas())
                self.boton_reglas.setEnabled(casilla.isChecked())
                fila.addWidget(self.boton_reglas)
                opciones_capa.addLayout(fila)
            else:
                opciones_capa.addWidget(casilla)
            nota = QtWidgets.QLabel(t("ajustes_" + clave + "_ayuda"))
            nota.setWordWrap(True)
            nota.setEnabled(False)
            nota.setContentsMargins(22, 0, 0, 4)
            opciones_capa.addWidget(nota)

        fila = QtWidgets.QHBoxLayout()
        fila.addWidget(QtWidgets.QLabel(t("ajustes_clase")))
        self.clase = QtWidgets.QLabel()
        self.clase.setTextInteractionFlags(Qt.TextSelectableByMouse)
        fila.addWidget(self.clase, 1)
        elegir = QtWidgets.QPushButton(t("ajustes_clase_elegir"))
        self.quitar_clase = QtWidgets.QPushButton(t("ajustes_clase_quitar"))
        elegir.clicked.connect(self._elegir_clase)
        self.quitar_clase.clicked.connect(lambda *_: self.fijar_clase("", avisar=True))
        fila.addWidget(elegir)
        fila.addWidget(self.quitar_clase)
        opciones_capa.addLayout(fila)
        nota = QtWidgets.QLabel(t("ajustes_clase_ayuda"))
        nota.setWordWrap(True)
        nota.setEnabled(False)
        opciones_capa.addWidget(nota)
        opciones_capa.addStretch(1)
        self.pestanas.addTab(grupo, t("ajustes_opciones"))
        self.fijar_clase(opciones.get("carpeta_clase", ""))

        self.pestanas.addTab(self._grupo_extra(), t("ajustes_extra"))
        self.fijar_extra(extra or {})
        capa = exterior


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
        self.resize(self.sizeHint())  # que las notas de varias líneas no se corten

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

    # --- Pill extra -------------------------------------------------------------

    def _grupo_extra(self):
        grupo = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(grupo)
        self.extra_activa = QtWidgets.QCheckBox(t("ajustes_extra_casilla"))
        self.extra_activa.toggled.connect(lambda valor: self._extra("activa", bool(valor)))
        capa.addWidget(self.extra_activa)
        nota = QtWidgets.QLabel(t("ajustes_extra_ayuda"))
        nota.setWordWrap(True)
        nota.setEnabled(False)
        nota.setContentsMargins(22, 0, 0, 4)
        capa.addWidget(nota)
        self.extra_controles = QtWidgets.QWidget()
        formulario = QtWidgets.QFormLayout(self.extra_controles)
        formulario.setContentsMargins(0, 0, 0, 0)
        self.extra_radial = QtWidgets.QComboBox()
        self.extra_radial.activated.connect(
            lambda indice: self._extra("radial", self.extra_radial.itemData(indice)))
        formulario.addRow(t("ajustes_extra_radial"), self.extra_radial)
        self.extra_cantidad = QtWidgets.QSpinBox()
        self.extra_cantidad.setRange(rd.MIN_BOTONES, rd.MAX_BOTONES)
        self.extra_cantidad.setValue(rd.NUM_BOTONES)
        self.extra_cantidad.valueChanged.connect(lambda valor: self._extra("cantidad", int(valor)))
        fila = QtWidgets.QHBoxLayout()
        fila.addWidget(self.extra_cantidad)
        fila.addStretch(1)
        formulario.addRow(t("ajustes_extra_cantidad"), fila)
        self.extra_horizontal = QtWidgets.QRadioButton(t("pill_horizontal"))
        self.extra_vertical = QtWidgets.QRadioButton(t("pill_vertical"))
        orientacion = QtWidgets.QButtonGroup(grupo)
        orientacion.addButton(self.extra_horizontal)
        orientacion.addButton(self.extra_vertical)
        fila = QtWidgets.QHBoxLayout()
        fila.addWidget(self.extra_horizontal)
        fila.addWidget(self.extra_vertical)
        fila.addStretch(1)
        formulario.addRow(t("ajustes_orientacion"), fila)
        self.extra_vertical.toggled.connect(lambda valor: self._extra("vertical", bool(valor)))
        self.extra_deslizadores = {}
        for clave, texto, escala, unidad in DESLIZADORES:
            if clave not in ("pill_boton", "opacidad"):
                continue
            minimo, maximo, _ = rd.APARIENCIA[clave]
            deslizador = Deslizador(minimo, maximo, escala, unidad)
            deslizador.cambiado.connect(lambda valor, c=clave: self._extra_apariencia(c, valor))
            formulario.addRow(t(texto), deslizador)
            self.extra_deslizadores[clave] = deslizador
        self.boton_extra_configurar = QtWidgets.QPushButton(t("ajustes_extra_configurar"))
        self.boton_extra_configurar.clicked.connect(lambda *_: self._extra("configurar"))
        formulario.addRow("", self.boton_extra_configurar)
        capa.addWidget(self.extra_controles)
        capa.addStretch(1)
        return grupo

    def fijar_extra(self, extra):
        """Pone los controles de la pill extra: activa, radial, vertical, apariencia y radiales."""
        self.extra = dict(extra)
        self.extra["apariencia"] = rd.normalizar_apariencia(extra.get("apariencia"))
        widgets = [self.extra_activa, self.extra_radial, self.extra_vertical, self.extra_horizontal,
                   self.extra_cantidad]
        for widget in widgets:
            widget.blockSignals(True)
        self.extra_activa.setChecked(bool(extra.get("activa")))
        self.extra_radial.clear()
        for identificador, nombre in extra.get("radiales", []):
            self.extra_radial.addItem(nombre, identificador)
        self.extra_radial.setCurrentIndex(max(0, self.extra_radial.findData(extra.get("radial"))))
        self.extra_cantidad.setValue(rd.normalizar_cantidad(extra.get("cantidad")))
        self.extra_vertical.setChecked(bool(extra.get("vertical")))
        self.extra_horizontal.setChecked(not extra.get("vertical"))
        for widget in widgets:
            widget.blockSignals(False)
        for clave, deslizador in self.extra_deslizadores.items():
            deslizador.fijar(self.extra["apariencia"][clave])
        self.extra_controles.setEnabled(bool(extra.get("activa")))

    def _extra(self, clave, valor=None):
        if clave == "activa":
            self.extra_controles.setEnabled(valor)
        if self._al_extra:
            self._al_extra(clave, valor)

    def _extra_apariencia(self, clave, valor):
        self.extra["apariencia"][clave] = valor
        self.extra["apariencia"] = rd.normalizar_apariencia(self.extra["apariencia"])
        if self._al_extra:
            self._al_extra("apariencia", dict(self.extra["apariencia"]))

    def _opcion(self, clave, valor):
        if clave == "automatico":
            self.boton_reglas.setEnabled(valor)
        if self._al_opcion:
            self._al_opcion(clave, valor)

    def fijar_clase(self, carpeta, avisar=False):
        self.carpeta_clase = carpeta or ""
        self.clase.setText(self.carpeta_clase or t("ajustes_clase_ninguna"))
        self.quitar_clase.setEnabled(bool(self.carpeta_clase))
        if avisar and self._al_opcion:
            self._al_opcion("carpeta_clase", self.carpeta_clase)

    def _elegir_clase(self):
        carpeta = QtWidgets.QFileDialog.getExistingDirectory(self, t("ajustes_clase_titulo"),
                                                             self.carpeta_clase or "")
        if carpeta:
            self.fijar_clase(carpeta, avisar=True)

    def _restaurar(self):
        por_defecto = rd.normalizar_apariencia({})
        self.fijar(por_defecto, self.forma(), self.vertical.isChecked(), dt.VENTANA_POR_DEFECTO_MS)
        if self._al_apariencia:
            self._al_apariencia(dict(por_defecto))
        if self._al_velocidad:
            self._al_velocidad(dt.VENTANA_POR_DEFECTO_MS)
