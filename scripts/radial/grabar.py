"""«Botón con lo último que hice»: convierte las últimas órdenes del Script Editor en un botón.

Maya escribe en el Script Editor (la parte de arriba) las órdenes MEL que vas
haciendo con los menús y las herramientas. ``ordenes()`` se queda con esas
líneas, sin comentarios ni resultados. No depende de Maya salvo ``registro_maya()``.
"""

import re

MAX_ORDENES = 40

# Órdenes que no tiene sentido repetir en un botón (moverse por la interfaz, seleccionar...)
_RUIDO = re.compile(r"^(select\b|changeSelectMode|setToolTo|toolPropertyWindow|editMenuUpdate|"
                    r"buildObjectMenuItemsNow|dR_|hotBox|undoInfo|scriptEditorInfo|autoUpdateAttrEd|"
                    r"updateAE|showEditor|ScriptEditor|modelEditor|lookThroughModelPanel|currentTime|"
                    r"setFocus|optionVar|panelHistory|outlinerEditor|playButton)")


def ordenes(texto, limite=MAX_ORDENES):
    """Las últimas órdenes MEL de ``texto`` (lo que muestra el Script Editor), la más reciente al final."""
    resultado = []
    for linea in (texto or "").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith(("//", "#", "# ", "Result:", "<", "import ")):
            continue
        if not linea.endswith(";") or _RUIDO.match(linea):
            continue
        if resultado and resultado[-1] == linea:
            continue  # la misma orden seguida (por ejemplo, arrastrar un deslizador)
        resultado.append(linea)
    return resultado[-limite:]


def boton(lineas, texto=""):
    """Un botón MEL con ``lineas`` (se deshacen de una vez con Ctrl+Z, como todos los de código)."""
    lineas = [linea for linea in lineas if linea.strip()]
    if not lineas:
        return None
    if not texto:
        texto = lineas[-1].split(" ")[0].split("(")[0].rstrip(";")[:20]
    return {"texto": texto, "detalle": "", "icono": "", "tipo": "mel", "accion": "\n".join(lineas)}


def registro_maya():
    """El texto de la parte de arriba del Script Editor ("" si no está abierto en ningún sitio)."""
    from maya import cmds
    for reporter in cmds.lsUI(type="cmdScrollFieldReporter") or []:
        try:
            texto = cmds.cmdScrollFieldReporter(reporter, query=True, text=True)
        except RuntimeError:
            continue
        if texto:
            return texto
    return ""


# --- Ventana -------------------------------------------------------------------------

def dialogo(lineas, huecos, destinos, padre=None):
    """Ventana para elegir las órdenes, el nombre, el menú y el hueco. Devuelve la ventana (sin abrir).

    ``huecos`` es ``{destino: [(indice, "1 · Duplicar"), ...]}`` y ``destinos`` ``[(clave, nombre)]``.
    Tras ``exec()``, ``ventana.resultado()`` da ``(boton, destino, indice)``.
    """
    from radial.i18n import t
    from radial.qt import QtCore, QtWidgets
    Qt = QtCore.Qt

    class DialogoGrabar(QtWidgets.QDialog):
        def __init__(self):
            super(DialogoGrabar, self).__init__(padre)
            self.setWindowTitle(t("grabar_titulo"))
            self.setObjectName("RadialGrabar")
            self.setMinimumWidth(520)
            capa = QtWidgets.QVBoxLayout(self)
            ayuda = QtWidgets.QLabel(t("grabar_ayuda"))
            ayuda.setWordWrap(True)
            capa.addWidget(ayuda)
            self.lista = QtWidgets.QListWidget()
            for i, linea in enumerate(lineas):
                item = QtWidgets.QListWidgetItem(linea)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if i >= len(lineas) - 1 else Qt.Unchecked)
                self.lista.addItem(item)
            self.lista.scrollToBottom()
            capa.addWidget(self.lista, 1)
            formulario = QtWidgets.QFormLayout()
            self.nombre = QtWidgets.QLineEdit()
            self.nombre.setPlaceholderText(t("grabar_nombre_pista"))
            formulario.addRow(t("config_texto"), self.nombre)
            self.destino = QtWidgets.QComboBox()
            for clave, nombre in destinos:
                self.destino.addItem(nombre, clave)
            formulario.addRow(t("grabar_menu"), self.destino)
            self.hueco = QtWidgets.QComboBox()
            formulario.addRow(t("grabar_hueco"), self.hueco)
            capa.addLayout(formulario)
            pie = QtWidgets.QHBoxLayout()
            pie.addStretch(1)
            cancelar = QtWidgets.QPushButton(t("boton_cancelar"))
            self.aceptar = QtWidgets.QPushButton(t("grabar_crear"))
            self.aceptar.setDefault(True)
            pie.addWidget(cancelar)
            pie.addWidget(self.aceptar)
            capa.addLayout(pie)
            cancelar.clicked.connect(self.reject)
            self.aceptar.clicked.connect(self.accept)
            self.destino.currentIndexChanged.connect(self._llenar_huecos)
            self.lista.itemChanged.connect(self._comprobar)
            self._llenar_huecos()
            self._comprobar()

        def _llenar_huecos(self, *_):
            self.hueco.clear()
            for indice, rotulo in huecos.get(self.destino.currentData(), []):
                self.hueco.addItem(rotulo, indice)

        def elegidas(self):
            return [self.lista.item(i).text() for i in range(self.lista.count())
                    if self.lista.item(i).checkState() == Qt.Checked]

        def _comprobar(self, *_):
            self.aceptar.setEnabled(bool(self.elegidas()))

        def resultado(self):
            return (boton(self.elegidas(), self.nombre.text().strip()), self.destino.currentData(),
                    self.hueco.currentData())

    return DialogoGrabar()
