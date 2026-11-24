"""Ventana para configurar los seis botones del radial activo.

A la izquierda, los seis huecos (se reordenan arrastrándolos). A la derecha,
el texto, el icono y la acción del hueco elegido. Cada cambio se aplica al
momento en el menú; «Guardar» lo escribe en el archivo del radial.
"""

from radial import iconos
from radial import radiales as rd
from radial.dibujo import qicono
from radial.i18n import t
from radial.qt import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt

TIPOS_PAGINA = ("comando", "estante", "python", "mel", "vacio")


def _titulo_boton(boton):
    if boton["tipo"] == "vacio":
        return t("config_hueco_vacio")
    return " ".join(p for p in (boton["texto"], boton["detalle"]) if p) or boton["accion"][:30]


class SelectorIconosMaya(QtWidgets.QDialog):
    """Buscador de iconos de Maya."""

    def __init__(self, fuentes, padre=None):
        super(SelectorIconosMaya, self).__init__(padre)
        self.setWindowTitle(t("config_iconos_maya_titulo"))
        self.resize(520, 440)
        self.fuentes = fuentes
        self.elegido = None
        capa = QtWidgets.QVBoxLayout(self)
        self.buscar = QtWidgets.QLineEdit()
        self.buscar.setPlaceholderText(t("config_buscar_icono"))
        self.buscar.setClearButtonEnabled(True)
        self.lista = QtWidgets.QListWidget()
        self.lista.setViewMode(QtWidgets.QListView.IconMode)
        self.lista.setIconSize(QtCore.QSize(32, 32))
        self.lista.setGridSize(QtCore.QSize(52, 52))
        self.lista.setResizeMode(QtWidgets.QListView.Adjust)
        self.lista.setUniformItemSizes(True)
        botones = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        botones.button(QtWidgets.QDialogButtonBox.Ok).setText(t("boton_usar_icono"))
        botones.button(QtWidgets.QDialogButtonBox.Cancel).setText(t("boton_cancelar"))
        capa.addWidget(self.buscar)
        capa.addWidget(self.lista)
        capa.addWidget(botones)
        botones.accepted.connect(self._aceptar)
        botones.rejected.connect(self.reject)
        self.lista.itemDoubleClicked.connect(lambda *_: self._aceptar())
        self._temporizador = QtCore.QTimer(self, singleShot=True, interval=200)
        self._temporizador.timeout.connect(self._llenar)
        self.buscar.textChanged.connect(lambda *_: self._temporizador.start())
        self._llenar()

    def _llenar(self):
        self.lista.clear()
        for ruta in self.fuentes.iconos_maya(self.buscar.text()):
            item = QtWidgets.QListWidgetItem(QtGui.QIcon(ruta), "")
            item.setToolTip(ruta[2:])
            item.setData(Qt.UserRole, ruta)
            self.lista.addItem(item)

    def _aceptar(self):
        item = self.lista.currentItem()
        if item is not None:
            self.elegido = item.data(Qt.UserRole)
            self.accept()


class Configurador(QtWidgets.QDialog):
    """``al_cambiar(radial)`` se llama con cada cambio; ``al_guardar()`` al pulsar Guardar."""

    def __init__(self, radial, fuentes, al_cambiar=None, al_guardar=None, al_restaurar=None,
                 puede_guardar=True, padre=None):
        super(Configurador, self).__init__(padre)
        self.setWindowTitle(t("config_titulo"))
        self.setObjectName("RadialConfigurador")
        self.resize(760, 520)
        self.fuentes = fuentes
        self._al_cambiar = al_cambiar
        self._al_guardar = al_guardar
        self._al_restaurar = al_restaurar
        self.radial = rd.normalizar(radial)
        self._cargando = False
        self._construir(puede_guardar)
        self._llenar_huecos()
        self.huecos.setCurrentRow(0)

    # --- Construcción ---------------------------------------------------------

    def _construir(self, puede_guardar):
        capa = QtWidgets.QVBoxLayout(self)
        self.cabecera = QtWidgets.QLabel()
        capa.addWidget(self.cabecera)

        cuerpo = QtWidgets.QHBoxLayout()
        capa.addLayout(cuerpo, 1)

        izquierda = QtWidgets.QVBoxLayout()
        self.huecos = QtWidgets.QListWidget()
        self.huecos.setFixedWidth(210)
        self.huecos.setIconSize(QtCore.QSize(20, 20))
        self.huecos.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.huecos.setDefaultDropAction(Qt.MoveAction)
        self.huecos.model().rowsMoved.connect(self._reordenado)
        self.huecos.currentRowChanged.connect(self._mostrar_hueco)
        nota = QtWidgets.QLabel(t("config_nota_orden"))
        nota.setWordWrap(True)
        nota.setEnabled(False)
        izquierda.addWidget(self.huecos, 1)
        izquierda.addWidget(nota)
        cuerpo.addLayout(izquierda)

        derecha = QtWidgets.QFormLayout()
        derecha.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        cuerpo.addLayout(derecha, 1)

        self.texto = QtWidgets.QLineEdit()
        self.texto.setMaxLength(40)
        self.detalle = QtWidgets.QLineEdit()
        self.detalle.setMaxLength(40)
        self.detalle.setPlaceholderText(t("config_detalle_ayuda"))
        derecha.addRow(t("config_texto"), self.texto)
        derecha.addRow(t("config_detalle"), self.detalle)

        fila_iconos = QtWidgets.QVBoxLayout()
        self.lista_iconos = QtWidgets.QListWidget()
        self.lista_iconos.setViewMode(QtWidgets.QListView.IconMode)
        self.lista_iconos.setIconSize(QtCore.QSize(20, 20))
        self.lista_iconos.setGridSize(QtCore.QSize(32, 32))
        self.lista_iconos.setMovement(QtWidgets.QListView.Static)
        self.lista_iconos.setResizeMode(QtWidgets.QListView.Adjust)
        self.lista_iconos.setFixedHeight(76)
        for nombre in sorted(iconos.TRAZOS):
            item = QtWidgets.QListWidgetItem(qicono(nombre), "")
            item.setToolTip(nombre)
            item.setData(Qt.UserRole, nombre)
            self.lista_iconos.addItem(item)
        botones_icono = QtWidgets.QHBoxLayout()
        self.icono_actual = QtWidgets.QLabel()
        self.boton_icono_maya = QtWidgets.QPushButton(t("config_icono_maya"))
        self.boton_sin_icono = QtWidgets.QPushButton(t("config_sin_icono"))
        botones_icono.addWidget(self.icono_actual, 1)
        botones_icono.addWidget(self.boton_icono_maya)
        botones_icono.addWidget(self.boton_sin_icono)
        fila_iconos.addWidget(self.lista_iconos)
        fila_iconos.addLayout(botones_icono)
        derecha.addRow(t("config_icono"), fila_iconos)

        self.tipo = QtWidgets.QComboBox()
        for clave in TIPOS_PAGINA:
            self.tipo.addItem(t("tipo_" + clave), clave)
        derecha.addRow(t("config_accion"), self.tipo)

        self.paginas = QtWidgets.QStackedWidget()
        self.paginas.addWidget(self._pagina_comandos())
        self.paginas.addWidget(self._pagina_estante())
        self.codigo_python = self._editor_codigo()
        self.codigo_mel = self._editor_codigo()
        self.paginas.addWidget(self.codigo_python)
        self.paginas.addWidget(self.codigo_mel)
        vacio = QtWidgets.QLabel(t("config_vacio_ayuda"))
        vacio.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        vacio.setWordWrap(True)
        self.paginas.addWidget(vacio)
        derecha.addRow("", self.paginas)

        self.estado = QtWidgets.QLabel()
        self.estado.setWordWrap(True)
        derecha.addRow("", self.estado)

        pie = QtWidgets.QHBoxLayout()
        self.boton_probar = QtWidgets.QPushButton(t("boton_probar"))
        self.boton_restaurar = QtWidgets.QPushButton(t("boton_restaurar_cambios"))
        self.boton_guardar = QtWidgets.QPushButton(t("boton_guardar") if puede_guardar
                                                   else t("boton_guardar_como_nuevo"))
        self.boton_guardar.setDefault(True)
        cerrar = QtWidgets.QPushButton(t("boton_cerrar"))
        pie.addWidget(self.boton_probar)
        pie.addStretch(1)
        pie.addWidget(self.boton_restaurar)
        pie.addWidget(self.boton_guardar)
        pie.addWidget(cerrar)
        capa.addLayout(pie)

        self.texto.textEdited.connect(lambda v: self._cambiar(texto=v))
        self.detalle.textEdited.connect(lambda v: self._cambiar(detalle=v))
        self.lista_iconos.itemClicked.connect(lambda item: self._cambiar(icono=item.data(Qt.UserRole)))
        self.boton_icono_maya.clicked.connect(self._elegir_icono_maya)
        self.boton_sin_icono.clicked.connect(lambda: self._cambiar(icono=""))
        self.tipo.currentIndexChanged.connect(self._tipo_cambiado)
        self.codigo_python.textChanged.connect(lambda: self._codigo_cambiado("python", self.codigo_python))
        self.codigo_mel.textChanged.connect(lambda: self._codigo_cambiado("mel", self.codigo_mel))
        self.boton_probar.clicked.connect(self._probar)
        self.boton_restaurar.clicked.connect(self._restaurar)
        self.boton_guardar.clicked.connect(self._guardar)
        cerrar.clicked.connect(self.close)

    def _editor_codigo(self):
        editor = QtWidgets.QPlainTextEdit()
        fuente = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        editor.setFont(fuente)
        editor.setTabChangesFocus(False)
        editor.setPlaceholderText(t("config_codigo_ayuda"))
        return editor

    def _pagina_comandos(self):
        pagina = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(pagina)
        capa.setContentsMargins(0, 0, 0, 0)
        self.buscar_comando = QtWidgets.QLineEdit()
        self.buscar_comando.setPlaceholderText(t("config_buscar_comando"))
        self.buscar_comando.setClearButtonEnabled(True)
        self.lista_comandos = QtWidgets.QTreeWidget()
        self.lista_comandos.setHeaderLabels([t("config_col_comando"), t("config_col_categoria"),
                                             t("config_col_descripcion")])
        self.lista_comandos.setRootIsDecorated(False)
        self.lista_comandos.setUniformRowHeights(True)
        self.lista_comandos.setColumnWidth(0, 210)
        self.lista_comandos.setColumnWidth(1, 120)
        capa.addWidget(self.buscar_comando)
        capa.addWidget(self.lista_comandos)
        self._comandos_cargados = False
        self._temporizador = QtCore.QTimer(self, singleShot=True, interval=150)
        self._temporizador.timeout.connect(self._filtrar_comandos)
        self.buscar_comando.textChanged.connect(lambda *_: self._temporizador.start())
        self.lista_comandos.currentItemChanged.connect(self._comando_elegido)
        return pagina

    def _pagina_estante(self):
        pagina = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(pagina)
        capa.setContentsMargins(0, 0, 0, 0)
        self.combo_estantes = QtWidgets.QComboBox()
        self.lista_estante = QtWidgets.QListWidget()
        self.lista_estante.setIconSize(QtCore.QSize(24, 24))
        ayuda = QtWidgets.QLabel(t("config_estante_ayuda"))
        ayuda.setWordWrap(True)
        ayuda.setEnabled(False)
        capa.addWidget(self.combo_estantes)
        capa.addWidget(self.lista_estante)
        capa.addWidget(ayuda)
        self._estantes = None
        self.combo_estantes.currentIndexChanged.connect(self._mostrar_estante)
        self.lista_estante.itemClicked.connect(self._copiar_de_estante)
        return pagina

    # --- Datos ----------------------------------------------------------------

    @property
    def indice(self):
        return max(0, self.huecos.currentRow())

    @property
    def boton(self):
        return self.radial["botones"][self.indice]

    def fijar_radial(self, radial, sin_guardar=False, nombre=None):
        """Recarga la ventana con ``radial`` (por ejemplo tras Restaurar o cambiar de radial)."""
        fila = self.indice
        self.radial = rd.normalizar(radial)
        self._llenar_huecos()
        self.huecos.setCurrentRow(fila)
        self._mostrar_hueco(fila)
        self.fijar_cabecera(nombre or self.radial["nombre"], sin_guardar)

    def fijar_cabecera(self, nombre, sin_guardar):
        texto = t("config_cabecera", nombre=nombre)
        if sin_guardar:
            texto += "  ·  " + t("sin_guardar")
        self.cabecera.setText(texto)

    def _llenar_huecos(self):
        self.huecos.blockSignals(True)
        self.huecos.clear()
        for i, boton in enumerate(self.radial["botones"]):
            item = QtWidgets.QListWidgetItem(qicono(boton["icono"]) if boton["icono"] else QtGui.QIcon(),
                                             "{}   {}".format(i + 1, _titulo_boton(boton)))
            item.setData(Qt.UserRole, i)
            self.huecos.addItem(item)
        self.huecos.blockSignals(False)

    def _actualizar_hueco(self, i):
        boton = self.radial["botones"][i]
        item = self.huecos.item(i)
        item.setText("{}   {}".format(i + 1, _titulo_boton(boton)))
        item.setIcon(qicono(boton["icono"]) if boton["icono"] else QtGui.QIcon())

    def _mostrar_hueco(self, fila):
        if fila < 0:
            return
        self._cargando = True
        boton = self.radial["botones"][fila]
        self.texto.setText(boton["texto"])
        self.detalle.setText(boton["detalle"])
        self._mostrar_icono(boton["icono"])
        tipo = boton["tipo"]
        self.tipo.setCurrentIndex(TIPOS_PAGINA.index(tipo))
        self.paginas.setCurrentIndex(TIPOS_PAGINA.index(tipo))
        self.codigo_python.setPlainText(boton["accion"] if tipo == "python" else "")
        self.codigo_mel.setPlainText(boton["accion"] if tipo == "mel" else "")
        if tipo == "comando":
            self._asegurar_comandos()
            self.buscar_comando.setText(boton["accion"])
            self._filtrar_comandos()
        self._mostrar_estado()
        self._cargando = False

    def _mostrar_icono(self, icono):
        self.lista_iconos.clearSelection()
        for i in range(self.lista_iconos.count()):
            if self.lista_iconos.item(i).data(Qt.UserRole) == icono:
                self.lista_iconos.item(i).setSelected(True)
        if icono and icono not in iconos.TRAZOS:
            self.icono_actual.setPixmap(QtGui.QIcon(icono).pixmap(24, 24))
            self.icono_actual.setToolTip(icono)
        else:
            self.icono_actual.clear()
            self.icono_actual.setText(t("config_icono_ninguno") if not icono else "")

    def _mostrar_estado(self):
        boton = self.boton
        if boton["tipo"] == "vacio":
            self.estado.setText("")
        elif boton["tipo"] == "comando":
            nombres = {c[0] for c in self.fuentes.comandos()}
            self.estado.setText(t("config_estado_comando", comando=boton["accion"])
                                if boton["accion"] in nombres else t("config_estado_sin_comando"))
        else:
            self.estado.setText(t("config_estado_codigo"))
        self.boton_probar.setEnabled(boton["tipo"] != "vacio")

    def _cambiar(self, **cambios):
        if self._cargando:
            return
        boton = dict(self.boton)
        boton.update(cambios)
        self.radial["botones"][self.indice] = rd.normalizar_boton(boton) if boton["tipo"] == "vacio" \
            else self._normalizar_sin_vaciar(boton)
        if "icono" in cambios:
            self._mostrar_icono(self.boton["icono"])
        self._actualizar_hueco(self.indice)
        self._mostrar_estado()
        self._avisar()

    @staticmethod
    def _normalizar_sin_vaciar(boton):
        """Como normalizar_boton, pero sin pasar a «vacío» mientras se escribe la acción."""
        limpio = rd.normalizar_boton(dict(boton, accion=boton.get("accion") or " "))
        limpio["accion"] = boton.get("accion", "")
        limpio["tipo"] = boton["tipo"]
        return limpio

    def _avisar(self):
        if self._al_cambiar:
            self._al_cambiar(rd.normalizar(self.radial))

    # --- Acciones ---------------------------------------------------------------

    def _tipo_cambiado(self, indice):
        clave = TIPOS_PAGINA[indice]
        self.paginas.setCurrentIndex(indice)
        if clave == "estante":
            self._asegurar_estantes()
            return
        if clave == "comando":
            self._asegurar_comandos()
        if self._cargando:
            return
        if clave == "vacio":
            self._cambiar(tipo="vacio", accion="")
        elif clave == "comando":
            self._cambiar(tipo="comando", accion="")
            self.buscar_comando.setFocus()
        else:
            editor = self.codigo_python if clave == "python" else self.codigo_mel
            self._cambiar(tipo=clave, accion=editor.toPlainText())

    def _codigo_cambiado(self, tipo, editor):
        if self._cargando or TIPOS_PAGINA[self.tipo.currentIndex()] != tipo:
            return
        self._cambiar(tipo=tipo, accion=editor.toPlainText())

    def _asegurar_comandos(self):
        if not self._comandos_cargados:
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self._todos_comandos = self.fuentes.comandos()
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()
            self._comandos_cargados = True
            self._filtrar_comandos()

    def _filtrar_comandos(self):
        if not self._comandos_cargados:
            return
        filtro = self.buscar_comando.text().strip().lower()
        self.lista_comandos.blockSignals(True)
        self.lista_comandos.clear()
        elegido = None
        mostrados = 0
        for nombre, categoria, descripcion in self._todos_comandos:
            if filtro and filtro not in nombre.lower() and filtro not in descripcion.lower():
                continue
            item = QtWidgets.QTreeWidgetItem([nombre, categoria.split(".")[-1], descripcion])
            item.setToolTip(2, descripcion)
            self.lista_comandos.addTopLevelItem(item)
            if nombre == self.boton["accion"]:
                elegido = item
            mostrados += 1
            if mostrados >= 500:
                break
        if elegido is not None:
            self.lista_comandos.setCurrentItem(elegido)
        self.lista_comandos.blockSignals(False)

    def _comando_elegido(self, item, _anterior=None):
        if item is None or self._cargando:
            return
        nombre, descripcion = item.text(0), item.text(2)
        cambios = {"tipo": "comando", "accion": nombre}
        if not self.boton["texto"] or self.boton["tipo"] != "comando":
            cambios["texto"] = nombre
            cambios["detalle"] = ""
            self.texto.setText(nombre)
            self.detalle.setText("")
        self._cambiar(**cambios)
        self.lista_comandos.setToolTip(descripcion)

    def _asegurar_estantes(self):
        if self._estantes is None:
            self._estantes = self.fuentes.estantes()
            self.combo_estantes.blockSignals(True)
            self.combo_estantes.clear()
            for nombre, _ in self._estantes:
                self.combo_estantes.addItem(nombre)
            self.combo_estantes.blockSignals(False)
            self._mostrar_estante(0)

    def _mostrar_estante(self, indice):
        self.lista_estante.clear()
        if not self._estantes or indice < 0:
            return
        for boton in self._estantes[indice][1]:
            item = QtWidgets.QListWidgetItem(QtGui.QIcon(boton["icono"]) if boton["icono"] else QtGui.QIcon(),
                                             boton["texto"])
            item.setToolTip(boton.get("descripcion") or boton["accion"][:300])
            item.setData(Qt.UserRole, boton)
            self.lista_estante.addItem(item)

    def _copiar_de_estante(self, item):
        boton = dict(item.data(Qt.UserRole))
        boton.pop("descripcion", None)
        self.radial["botones"][self.indice] = rd.normalizar_boton(boton)
        self._actualizar_hueco(self.indice)
        self._mostrar_hueco(self.indice)
        self._avisar()

    def _elegir_icono_maya(self):
        selector = SelectorIconosMaya(self.fuentes, self)
        if selector.exec() and selector.elegido:
            self._cambiar(icono=selector.elegido)

    def _reordenado(self, *_):
        orden = [self.huecos.item(i).data(Qt.UserRole) for i in range(self.huecos.count())]
        self.radial["botones"] = [self.radial["botones"][i] for i in orden]
        fila = self.huecos.currentRow()
        self._llenar_huecos()
        self.huecos.setCurrentRow(fila)
        self._avisar()

    def _probar(self):
        self.fuentes.probar(rd.normalizar_boton(self.boton))

    def _restaurar(self):
        if self._al_restaurar:
            self._al_restaurar()

    def _guardar(self):
        if self._al_guardar:
            self._al_guardar()
