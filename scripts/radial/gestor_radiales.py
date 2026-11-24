"""Ventana para gestionar los radiales: usar, renombrar, duplicar, exportar, importar y borrar."""

from radial import radiales as rd
from radial.biblioteca import MIO
from radial.i18n import t
from radial.qt import QtCore, QtWidgets

Qt = QtCore.Qt


class GestorRadiales(QtWidgets.QDialog):
    """Trabaja directamente sobre una ``Biblioteca``. ``al_cambiar()`` avisa si cambió el radial activo."""

    def __init__(self, biblioteca, al_cambiar=None, padre=None):
        super(GestorRadiales, self).__init__(padre)
        self.setWindowTitle(t("gestor_titulo"))
        self.setObjectName("RadialGestor")
        self.resize(460, 400)
        self.biblioteca = biblioteca
        self._al_cambiar = al_cambiar

        capa = QtWidgets.QHBoxLayout(self)
        self.lista = QtWidgets.QListWidget()
        capa.addWidget(self.lista, 1)

        botones = QtWidgets.QVBoxLayout()
        self.boton_usar = QtWidgets.QPushButton(t("gestor_usar"))
        self.boton_renombrar = QtWidgets.QPushButton(t("gestor_renombrar"))
        self.boton_duplicar = QtWidgets.QPushButton(t("gestor_duplicar"))
        self.boton_exportar = QtWidgets.QPushButton(t("gestor_exportar"))
        self.boton_borrar = QtWidgets.QPushButton(t("gestor_borrar"))
        self.boton_importar = QtWidgets.QPushButton(t("gestor_importar"))
        cerrar = QtWidgets.QPushButton(t("boton_cerrar"))
        for boton in (self.boton_usar, self.boton_renombrar, self.boton_duplicar, self.boton_exportar,
                      self.boton_borrar):
            botones.addWidget(boton)
        botones.addSpacing(12)
        botones.addWidget(self.boton_importar)
        botones.addStretch(1)
        botones.addWidget(cerrar)
        capa.addLayout(botones)

        self.lista.currentItemChanged.connect(lambda *_: self._actualizar_botones())
        self.lista.itemDoubleClicked.connect(lambda *_: self.usar())
        self.boton_usar.clicked.connect(self.usar)
        self.boton_renombrar.clicked.connect(self.renombrar)
        self.boton_duplicar.clicked.connect(self.duplicar)
        self.boton_exportar.clicked.connect(self.exportar)
        self.boton_borrar.clicked.connect(self.borrar)
        self.boton_importar.clicked.connect(self.importar)
        cerrar.clicked.connect(self.close)
        self.refrescar()

    # --- Lista ----------------------------------------------------------------

    def refrescar(self, elegir=None):
        elegir = elegir or self.seleccionado() or self.biblioteca.origen
        self.lista.clear()
        activo = self.biblioteca.origen

        def cabecera(texto):
            item = QtWidgets.QListWidgetItem(texto)
            item.setFlags(Qt.NoItemFlags)
            fuente = item.font()
            fuente.setBold(True)
            item.setFont(fuente)
            self.lista.addItem(item)

        cabecera(t("menu_preconfigurados"))
        for identificador, nombre in self.biblioteca.preconfigurados():
            self._anadir(identificador, nombre, identificador == activo)
        cabecera(t("menu_mis_radiales"))
        mios = self.biblioteca.mios()
        if not mios:
            item = QtWidgets.QListWidgetItem("   " + t("gestor_sin_mios"))
            item.setFlags(Qt.NoItemFlags)
            self.lista.addItem(item)
        for identificador, nombre in mios:
            self._anadir(identificador, nombre, identificador == activo)
        for i in range(self.lista.count()):
            if self.lista.item(i).data(Qt.UserRole) == elegir:
                self.lista.setCurrentRow(i)
        self._actualizar_botones()

    def _anadir(self, identificador, nombre, activo):
        texto = "   " + nombre
        if activo:
            texto += "   ✓"
            if self.biblioteca.sin_guardar:
                texto += " " + t("sin_guardar")
        item = QtWidgets.QListWidgetItem(texto)
        item.setData(Qt.UserRole, identificador)
        if activo:
            fuente = item.font()
            fuente.setBold(True)
            item.setFont(fuente)
        self.lista.addItem(item)

    def seleccionado(self):
        item = self.lista.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    def _actualizar_botones(self):
        identificador = self.seleccionado()
        hay = identificador is not None
        propio = hay and identificador.startswith(MIO)
        self.boton_usar.setEnabled(hay)
        self.boton_duplicar.setEnabled(hay)
        self.boton_exportar.setEnabled(hay)
        self.boton_renombrar.setEnabled(propio)
        self.boton_borrar.setEnabled(propio)

    def _avisar(self):
        if self._al_cambiar:
            self._al_cambiar()

    def _error(self, error):
        QtWidgets.QMessageBox.warning(self, t("gestor_titulo"), t("gestor_error", error=error))

    # --- Acciones ---------------------------------------------------------------

    def usar(self):
        identificador = self.seleccionado()
        if not identificador or identificador == self.biblioteca.origen:
            return
        if self.biblioteca.sin_guardar and not self._confirmar(t("gestor_descartar")):
            return
        try:
            self.biblioteca.usar(identificador)
        except rd.RadialNoValido as error:
            self._error(error)
            return
        self._avisar()
        self.refrescar(identificador)

    def renombrar(self):
        identificador = self.seleccionado()
        if not identificador or not identificador.startswith(MIO):
            return
        actual = self.biblioteca.nombre_de(identificador)
        nombre, ok = QtWidgets.QInputDialog.getText(self, t("gestor_renombrar_titulo"), t("gestor_nombre"),
                                                    text=actual)
        if not ok or not nombre.strip() or nombre.strip() == actual:
            return
        try:
            nuevo = self.biblioteca.renombrar(identificador, nombre)
        except (rd.RadialNoValido, OSError) as error:
            self._error(error)
            return
        self._avisar()
        self.refrescar(nuevo)

    def duplicar(self):
        identificador = self.seleccionado()
        if not identificador:
            return
        try:
            nuevo = self.biblioteca.duplicar(identificador)
        except (rd.RadialNoValido, OSError) as error:
            self._error(error)
            return
        self.refrescar(nuevo)

    def exportar(self):
        identificador = self.seleccionado()
        if not identificador:
            return
        nombre = rd.nombre_de_archivo(self.biblioteca.nombre_de(identificador)) + rd.EXTENSION
        ruta, _ = QtWidgets.QFileDialog.getSaveFileName(self, t("exportar_titulo"), nombre, t("filtro_radial"))
        if not ruta:
            return
        try:
            ruta = self.biblioteca.exportar(ruta, identificador)
        except (rd.RadialNoValido, OSError) as error:
            self._error(error)
            return
        print(t("exportado", ruta=ruta))

    def importar(self):
        ruta, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("importar_titulo"), "", t("filtro_radial"))
        if not ruta:
            return
        if self.biblioteca.sin_guardar and not self._confirmar(t("gestor_descartar")):
            return
        try:
            self.biblioteca.importar(ruta)
        except (rd.RadialNoValido, OSError) as error:
            self._error(error)
            return
        self._avisar()
        self.refrescar(self.biblioteca.origen)

    def borrar(self):
        identificador = self.seleccionado()
        if not identificador or not identificador.startswith(MIO):
            return
        if not self._confirmar(t("gestor_borrar_pregunta", nombre=self.biblioteca.nombre_de(identificador))):
            return
        era_activo = identificador == self.biblioteca.origen
        try:
            self.biblioteca.borrar(identificador)
        except (rd.RadialNoValido, OSError) as error:
            self._error(error)
            return
        if era_activo:
            self._avisar()
        self.refrescar(self.biblioteca.origen)

    def _confirmar(self, pregunta):
        respuesta = QtWidgets.QMessageBox.question(self, t("gestor_titulo"), pregunta,
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                   QtWidgets.QMessageBox.No)
        return respuesta == QtWidgets.QMessageBox.Yes

