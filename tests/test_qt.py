"""Pruebas sin Maya del filtro de teclado y del menú, con Qt sin pantalla.

Necesitan PySide6 (``pip install PySide6-Essentials``); si no está, se saltan.
"""

import os
import sys
import unittest
import unittest.mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    QtWidgets = None

if QtWidgets is not None:
    from radial import radiales as rd
    from radial.filtro_teclado import FiltroTeclado
    from radial.menu_radial import MenuRadial
    from radial.menu_pill import MenuPill
    from radial.configurador import TIPOS_PAGINA, Configurador
    from radial.ventana_ajustes import DialogoReglas, VentanaAjustes
    from radial import ayuda, interruptores
    from radial.buscador import Buscador, ListaResultados as ListaResultadosPrueba
    from radial import arrastre, busqueda

    Qt = QtCore.Qt
    QEvent = QtCore.QEvent
    APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _tecla(destino, momento, tecla=None, modificadores=None, repetida=False):
    """Envía una pulsación como lo hace Qt: ShortcutOverride y luego KeyPress.

    Devuelve el conjunto de tipos de evento que llegaron al destino.
    """
    tecla = Qt.Key_Tab if tecla is None else tecla
    modificadores = Qt.NoModifier if modificadores is None else modificadores
    llegados = set()
    for tipo in (QEvent.ShortcutOverride, QEvent.KeyPress):
        evento = QtGui.QKeyEvent(tipo, tecla, modificadores, "\t", repetida)
        evento.setTimestamp(momento)
        destino.recibidos = []
        APP.sendEvent(destino, evento)
        llegados.update(destino.recibidos)
    return llegados


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaFiltro(unittest.TestCase):
    def setUp(self):
        class Destino(QtWidgets.QWidget):
            def event(self, evento):
                if evento.type() in (QEvent.ShortcutOverride, QEvent.KeyPress):
                    self.recibidos.append(evento.type())
                return super(Destino, self).event(evento)

        self.destino = Destino()
        self.destino.recibidos = []
        self.avisos = []
        self.contexto = {"cuenta": True}
        self.filtro = FiltroTeclado(lambda es_segundo: self.contexto["cuenta"] or es_segundo,
                                    lambda: self.avisos.append(1), 250)
        self.filtro.instalar()

    def tearDown(self):
        self.filtro.quitar()

    def _procesar(self):
        APP.processEvents()

    def test_doble_tab_rapido_se_queda_el_segundo(self):
        self.assertEqual(len(_tecla(self.destino, 1000)), 2)   # el primero llega entero
        self.assertEqual(_tecla(self.destino, 1180), set())        # el segundo no llega
        self._procesar()
        self.assertEqual(self.avisos, [1])

    def test_mantener_el_segundo_tab_es_un_gesto(self):
        soltados = []
        self.filtro._al_soltar_tab = lambda: soltados.append(1)
        _tecla(self.destino, 1000)
        self.assertEqual(_tecla(self.destino, 1180), set())
        self.assertTrue(self.filtro.manteniendo)
        # La auto-repetición y el soltar de ese Tab no llegan a Maya
        self.assertEqual(_tecla(self.destino, 1700, repetida=True), set())
        for repetida in (True, False):
            evento = QtGui.QKeyEvent(QEvent.KeyRelease, Qt.Key_Tab, Qt.NoModifier, "\t", repetida)
            self.assertTrue(self.filtro.eventFilter(self.destino, evento))
        self._procesar()
        self.assertFalse(self.filtro.manteniendo)
        self.assertEqual(soltados, [1])
        # Después, mantener Tab vuelve a ser de Maya
        self.assertEqual(len(_tecla(self.destino, 5000)), 2)
        self.assertEqual(len(_tecla(self.destino, 5400, repetida=True)), 2)
        evento = QtGui.QKeyEvent(QEvent.KeyRelease, Qt.Key_Tab, Qt.NoModifier, "\t", False)
        self.assertFalse(self.filtro.eventFilter(self.destino, evento))

    def test_dos_tab_lentos_llegan_los_dos(self):
        self.assertEqual(len(_tecla(self.destino, 1000)), 2)
        self.assertEqual(len(_tecla(self.destino, 1400)), 2)
        self._procesar()
        self.assertEqual(self.avisos, [])

    def test_con_modificador_no_cuenta(self):
        _tecla(self.destino, 1000)
        llegados = _tecla(self.destino, 1100, modificadores=Qt.ControlModifier)
        self.assertEqual(len(llegados), 2)
        self._procesar()
        self.assertEqual(self.avisos, [])

    def test_tab_mantenido_no_cuenta(self):
        _tecla(self.destino, 1000)
        _tecla(self.destino, 1030, repetida=True)
        self._procesar()
        self.assertEqual(self.avisos, [])

    def test_otra_tecla_en_medio(self):
        _tecla(self.destino, 1000)
        _tecla(self.destino, 1050, tecla=Qt.Key_A)
        self.assertEqual(len(_tecla(self.destino, 1100)), 2)
        self._procesar()
        self.assertEqual(self.avisos, [])

    def test_mayusculas_en_medio_no_rompe(self):
        _tecla(self.destino, 1000)
        _tecla(self.destino, 1050, tecla=Qt.Key_Shift)
        self.assertEqual(_tecla(self.destino, 1100), set())

    def test_fuera_del_visor_no_hace_nada(self):
        self.contexto["cuenta"] = False
        self.assertEqual(len(_tecla(self.destino, 1000)), 2)
        self.assertEqual(len(_tecla(self.destino, 1100)), 2)
        self._procesar()
        self.assertEqual(self.avisos, [])

    def test_un_error_no_bloquea_el_teclado(self):
        def roto(_):
            raise RuntimeError("fallo a propósito")
        self.filtro._puede_contar = roto
        self.assertEqual(len(_tecla(self.destino, 1000)), 2)


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaMenu(unittest.TestCase):
    def setUp(self):
        self.ejecutados, self.movidos, self.configurar = [], [], []
        self.menu = MenuRadial(al_ejecutar=lambda i, opciones=False: self.ejecutados.append((i, opciones) if opciones else i), al_mover=self.movidos.append,
                               al_configurar=lambda: self.configurar.append(1))
        self.menu.usar_radial(rd.por_defecto())
        self.menu.colocar(QtCore.QPoint(400, 300))
        self.menu.show()
        APP.processEvents()

    def tearDown(self):
        self.menu.close()
        self.menu.deleteLater()

    def _punto_boton(self, i):
        x, y = rd.posiciones(self.menu.apariencia["radio"])[i]
        return QtCore.QPoint(int(self.menu.width() / 2 + x), int(self.menu.height() / 2 + y))

    def _centro(self):
        return QtCore.QPoint(self.menu.width() // 2, self.menu.height() // 2)

    def _raton(self, tipo, punto, boton=Qt.LeftButton):
        botones = Qt.NoButton if tipo == QEvent.MouseMove else boton
        evento = QtGui.QMouseEvent(tipo, QtCore.QPointF(punto),
                                   QtCore.QPointF(self.menu.mapToGlobal(punto)),
                                   boton if tipo != QEvent.MouseMove else Qt.NoButton, botones,
                                   Qt.NoModifier)
        APP.sendEvent(self.menu, evento)

    def test_no_acepta_el_foco(self):
        self.assertTrue(self.menu.windowFlags() & Qt.WindowDoesNotAcceptFocus)
        self.assertEqual(self.menu.focusPolicy(), Qt.NoFocus)

    def test_clic_en_un_boton(self):
        p = self._punto_boton(1)
        self._raton(QEvent.MouseMove, p)
        self._raton(QEvent.MouseButtonPress, p)
        self._raton(QEvent.MouseButtonRelease, p)
        self.assertEqual(self.ejecutados, [1])

    def test_clic_en_boton_vacio_no_ejecuta(self):
        radial = rd.por_defecto()
        radial["botones"][3] = rd.boton_vacio()
        self.menu.usar_radial(radial)
        p = self._punto_boton(3)
        self._raton(QEvent.MouseButtonPress, p)
        self._raton(QEvent.MouseButtonRelease, p)
        self.assertEqual(self.ejecutados, [])

    def test_arrastrar_desde_el_centro(self):
        antes = self.menu.centro_global()
        c = self._centro()
        self._raton(QEvent.MouseButtonPress, c)
        movido = c + QtCore.QPoint(120, 40)
        evento = QtGui.QMouseEvent(QEvent.MouseMove, QtCore.QPointF(movido),
                                   QtCore.QPointF(self.menu.mapToGlobal(movido)),
                                   Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        APP.sendEvent(self.menu, evento)
        destino = self.menu.mapFromGlobal(self.menu.mapToGlobal(movido))
        self._raton(QEvent.MouseButtonRelease, destino)
        self.assertEqual(self.menu.centro_global() - antes, QtCore.QPoint(120, 40))
        self.assertEqual(self.movidos, [self.menu.centro_global()])
        self.assertEqual(self.ejecutados, [])

    def test_gesto_por_direccion(self):
        inicio = QtCore.QPoint(0, 0)
        self.assertIsNone(self.menu._direccion(5, 5))  # sin moverse no hay botón
        self.assertEqual(self.menu._direccion(0, -80), 0)   # arriba
        self.assertEqual(self.menu._direccion(0, 80), 3)    # abajo
        self.assertEqual(self.menu._direccion(70, -40), 1)  # arriba a la derecha
        lejos = self.menu.mapToGlobal(QtCore.QPoint(-500, -500))
        self.assertIsNone(self.menu.boton_en_gesto(lejos, lejos))
        punto = self.menu.mapToGlobal(self._punto_boton(4))
        self.assertEqual(self.menu.boton_en_gesto(inicio, punto), 4)  # el que está bajo el ratón
        self.menu.marcar_gesto(4)
        self.assertEqual(self.menu._sobre, 4)

    def test_clic_derecho_en_el_centro_configura(self):
        self._raton(QEvent.MouseButtonPress, self._centro(), Qt.RightButton)
        self.assertEqual(self.configurar, [1])

    def test_mascara_deja_pasar_los_huecos(self):
        mascara = self.menu.mask()
        self.assertTrue(mascara.contains(self._punto_boton(0)))
        self.assertTrue(mascara.contains(self._centro()))
        hueco = self._centro() + QtCore.QPoint(0, 55)  # entre el centro y el botón de abajo
        self.assertFalse(mascara.contains(hueco))
        self.assertFalse(mascara.contains(QtCore.QPoint(2, 2)))

    def test_cambiar_tamano_conserva_el_centro(self):
        antes = self.menu.centro_global()
        radial = rd.por_defecto()
        radial["apariencia"]["radio"] = 130
        self.menu.usar_radial(radial)
        self.assertEqual(self.menu.width(), rd.lado_ventana(self.menu.apariencia))
        self.assertLessEqual((self.menu.centro_global() - antes).manhattanLength(), 1)

    def test_dibuja_sin_errores(self):
        self._raton(QEvent.MouseMove, self._punto_boton(0))
        for _ in range(10):
            self.menu._animar()
        imagen = self.menu.grab()
        self.assertFalse(imagen.isNull())



class FuentesFalsas(object):
    """Lo mínimo que el configurador pide a Maya."""

    def __init__(self):
        self.probados = []

    def comandos(self):
        return [("CenterPivot", "Menu items.Modify", "Center the pivot"),
                ("DuplicateSpecialOptions", "Menu items.Edit", "Duplicate special"),
                ("PolyExtrude", "Menu items.Mesh", "Extrude faces")]

    def estantes(self):
        return [("Poly", [{"texto": "Cubo", "detalle": "", "icono": "", "tipo": "mel",
                           "accion": "polyCube;", "descripcion": "Crea un cubo"}])]

    def iconos_maya(self, filtro="", limite=400):
        return []

    def probar(self, boton):
        self.probados.append(boton)
        return True


def _clic(widget, punto, boton=None):
    boton = Qt.LeftButton if boton is None else boton
    for tipo in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
        evento = QtGui.QMouseEvent(tipo, QtCore.QPointF(punto), QtCore.QPointF(widget.mapToGlobal(punto)),
                                   Qt.NoButton if tipo == QEvent.MouseMove else boton,
                                   Qt.NoButton if tipo == QEvent.MouseMove else boton, Qt.NoModifier)
        APP.sendEvent(widget, evento)


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaPill(unittest.TestCase):
    def setUp(self):
        self.ejecutados, self.movidos, self.configurar = [], [], []

    def _pill(self, vertical):
        pill = MenuPill(al_ejecutar=lambda i, opciones=False: self.ejecutados.append((i, opciones) if opciones else i), al_mover=self.movidos.append,
                        al_configurar=lambda: self.configurar.append(1), vertical=vertical)
        pill.usar_radial(rd.por_defecto())
        pill.colocar(QtCore.QPoint(500, 400))
        pill.show()
        self.addCleanup(pill.close)
        return pill

    def _centro_boton(self, pill, i):
        x, y, w, h = rd.geometria_pill(pill.apariencia, pill.vertical)[3][i]
        return QtCore.QPoint(int(1 + x + w / 2), int(1 + y + h / 2))

    def test_clic_y_etiqueta(self):
        for vertical in (False, True):
            pill = self._pill(vertical)
            punto = self._centro_boton(pill, 4)
            _clic(pill, punto)
            self.assertEqual(self.ejecutados[-1], 4)
            self.assertTrue(pill.etiqueta.isVisible())
            self.assertEqual(pill.etiqueta.texto, "Hypershade")
            pill.hide()
            self.assertFalse(pill.etiqueta.isVisible())

    def test_tamano_segun_orientacion(self):
        h = self._pill(False)
        v = self._pill(True)
        self.assertGreater(h.width(), h.height())
        self.assertEqual((h.width(), h.height()), (v.height(), v.width()))

    def test_clic_derecho_en_agarre(self):
        pill = self._pill(False)
        _clic(pill, QtCore.QPoint(10, pill.height() // 2), Qt.RightButton)
        self.assertEqual(self.configurar, [1])

    def test_dibuja(self):
        pill = self._pill(False)
        pill._sobre = 0
        for _ in range(6):
            pill._animar()
        self.assertFalse(pill.grab().isNull())


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaConfigurador(unittest.TestCase):
    def setUp(self):
        self.cambios, self.guardados = [], []
        self.fuentes = FuentesFalsas()
        self.ventana = Configurador(rd.por_defecto(), self.fuentes, al_cambiar=self.cambios.append,
                                    al_guardar=lambda: self.guardados.append(1))
        self.addCleanup(self.ventana.close)

    def test_muestra_el_primer_hueco(self):
        self.assertEqual(self.ventana.texto.text(), "Duplicar")
        self.assertEqual(self.ventana.huecos.count(), 6)

    def test_editar_texto_avisa(self):
        self.ventana.texto.setText("Clonar")
        self.ventana.texto.textEdited.emit("Clonar")
        self.assertEqual(self.cambios[-1]["botones"][0]["texto"], "Clonar")

    def test_elegir_comando(self):
        self.ventana.huecos.setCurrentRow(1)
        self.ventana.buscar_comando.setText("extrude")
        self.ventana._filtrar_comandos()
        self.assertEqual(self.ventana.lista_comandos.topLevelItemCount(), 1)
        self.ventana.lista_comandos.setCurrentItem(self.ventana.lista_comandos.topLevelItem(0))
        boton = self.cambios[-1]["botones"][1]
        self.assertEqual((boton["tipo"], boton["accion"]), ("comando", "PolyExtrude"))

    def test_codigo_python(self):
        self.ventana.huecos.setCurrentRow(2)
        self.ventana.tipo.setCurrentIndex(TIPOS_PAGINA.index("python"))
        self.ventana.codigo_python.setPlainText("print('hola')")
        boton = self.cambios[-1]["botones"][2]
        self.assertEqual((boton["tipo"], boton["accion"]), ("python", "print('hola')"))
        self.ventana.boton_probar.click()
        self.assertEqual(self.fuentes.probados[-1]["accion"], "print('hola')")

    def test_vaciar_hueco(self):
        self.ventana.huecos.setCurrentRow(5)
        self.ventana.tipo.setCurrentIndex(TIPOS_PAGINA.index("vacio"))
        self.assertEqual(self.cambios[-1]["botones"][5]["tipo"], "vacio")

    def test_copiar_de_estante(self):
        self.ventana.huecos.setCurrentRow(3)
        self.ventana.tipo.setCurrentIndex(TIPOS_PAGINA.index("estante"))
        self.ventana._copiar_de_estante(self.ventana.lista_estante.item(0))
        boton = self.cambios[-1]["botones"][3]
        self.assertEqual((boton["texto"], boton["tipo"], boton["accion"]), ("Cubo", "mel", "polyCube;"))
        self.assertEqual(self.ventana.tipo.currentIndex(), TIPOS_PAGINA.index("mel"))

    def test_icono(self):
        self.ventana._cambiar(icono="estrella")
        self.assertEqual(self.cambios[-1]["botones"][0]["icono"], "estrella")

    def test_guardar(self):
        self.ventana.boton_guardar.click()
        self.assertEqual(self.guardados, [1])


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaBuscador(unittest.TestCase):
    def setUp(self):
        self.ejecutadas, self.terminados, self.recientes = [], [], []
        acciones = [busqueda.accion_de_comando(*c) for c in FuentesFalsas().comandos()]
        self.buscador = Buscador(lambda: acciones, self.ejecutadas.append, recientes=lambda: self.recientes,
                                 al_terminar=lambda: self.terminados.append(1))
        self.menu = MenuRadial()
        self.menu.usar_radial(rd.por_defecto())
        self.menu.colocar(QtCore.QPoint(500, 400))
        self.buscador.acompanar(self.menu)
        self.addCleanup(self.buscador.close)
        self.addCleanup(self.menu.close)

    def _escribir(self, texto):
        self.buscador.campo.setText(texto)
        self.buscador.campo.textEdited.emit(texto)

    def _tecla(self, tecla):
        evento = QtGui.QKeyEvent(QEvent.KeyPress, tecla, Qt.NoModifier)
        APP.sendEvent(self.buscador.campo, evento)

    def test_la_lista_nunca_tapa_la_barra(self):
        self.menu.show()
        APP.processEvents()
        zona = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        for y in (200, zona.bottom() - 330, zona.bottom() - 200):
            self.menu.colocar(QtCore.QPoint(500, y))
            self.buscador.colocar()
            self._escribir("e")
            APP.processEvents()
            barra = self.buscador.geometry()
            lista = self.buscador.lista.geometry()
            self.assertFalse(barra.intersects(lista), (y, barra, lista))
            self.assertLessEqual(lista.bottom(), zona.bottom())
        # Moverse con la lista abierta la lleva con la barra
        self.buscador.move(self.buscador.pos() + QtCore.QPoint(0, -40))
        self.assertFalse(self.buscador.geometry().intersects(self.buscador.lista.geometry()))

    def test_sigue_al_menu(self):
        self.assertFalse(self.buscador.isVisible())
        self.menu.show()
        APP.processEvents()
        self.assertTrue(self.buscador.isVisible())
        self.assertGreater(self.buscador.y(), self.menu.y() + self.menu.height() - 1)
        self.assertEqual(self.buscador.geometry().center().x() // 4, self.menu.geometry().center().x() // 4)
        self.menu.hide()
        self.assertFalse(self.buscador.isVisible())

    def test_al_aparecer_no_roba_el_teclado(self):
        self.menu.show()
        APP.processEvents()
        self.buscador.activateWindow()  # aunque el sistema lo active al mostrarlo
        self.buscador.campo.setFocus(Qt.ActiveWindowFocusReason)
        APP.processEvents()
        self.assertFalse(self.buscador.campo.hasFocus())
        self.assertFalse(self.buscador.lista.isVisible())
        self.assertTrue(self.terminados)
        self.assertTrue(self.buscador.testAttribute(Qt.WA_ShowWithoutActivating))
        self.assertEqual(self.buscador.campo.focusPolicy(), Qt.ClickFocus)

    def test_clic_en_el_campo_si_escribe(self):
        self.menu.show()
        APP.processEvents()
        _clic(self.buscador.campo, QtCore.QPoint(20, 10))
        APP.processEvents()
        self.assertTrue(self.buscador._editando)

    def test_desactivado_no_se_ve(self):
        self.buscador.activo = False
        self.menu.show()
        APP.processEvents()
        self.assertFalse(self.buscador.isVisible())

    def test_ancho_de_la_pill(self):
        pill = MenuPill()
        pill.usar_radial(rd.por_defecto())
        self.addCleanup(pill.close)
        self.buscador.acompanar(pill)
        pill.show()
        APP.processEvents()
        self.assertEqual(self.buscador.width(), max(200, pill.width()))

    def test_escribir_y_ejecutar_con_intro(self):
        self.menu.show()
        self._escribir("extr")
        self.assertTrue(self.buscador.lista.isVisible())
        self.assertEqual(self.buscador.lista.acciones[0]["nombre"], "PolyExtrude")
        self._tecla(Qt.Key_Return)
        self.assertEqual(self.ejecutadas[0]["nombre"], "PolyExtrude")
        self.assertEqual(self.buscador.campo.text(), "")
        self.assertFalse(self.buscador.lista.isVisible())
        self.assertEqual(self.terminados, [1])

    def test_flechas_y_esc(self):
        self._escribir("e")
        primera = self.buscador.lista.accion_elegida()
        self._tecla(Qt.Key_Down)
        self.assertIsNot(self.buscador.lista.accion_elegida(), primera)
        self._tecla(Qt.Key_Escape)
        self.assertEqual(self.ejecutadas, [])
        self.assertEqual(self.buscador.campo.text(), "")
        self.assertEqual(self.terminados, [1])

    def test_sin_resultados_y_recientes(self):
        self._escribir("zzz")
        self.assertEqual(self.buscador.lista.acciones, [])
        self.recientes.append(busqueda.accion_de_comando("CenterPivot"))
        self._escribir("")
        self.assertEqual(self.buscador.lista.titulo, "Usadas hace poco")

    def test_estrella_de_favoritas(self):
        favoritos = []
        acciones = [busqueda.accion_de_comando(*c) for c in FuentesFalsas().comandos()]
        buscador = Buscador(lambda: acciones, self.ejecutadas.append, recientes=lambda: self.recientes,
                            favoritos=lambda: favoritos,
                            al_favorito=lambda a: favoritos.__setitem__(
                                slice(None), busqueda.alternar_favorito(favoritos, a)))
        self.addCleanup(buscador.close)
        buscador.campo.setText("pivot")
        buscador.campo.textEdited.emit("pivot")
        lista = buscador.lista
        lista.setFixedWidth(360)
        estrella = lista.zona_estrella(0).center().toPoint()
        _clic(lista, estrella)
        self.assertEqual(self.ejecutadas, [])  # la estrella no ejecuta
        self.assertEqual([a["nombre"] for a in favoritos], ["CenterPivot"])
        self.assertTrue(lista.es_favorita(lista.acciones[0]))
        lista.grab()
        # Sin texto salen primero las favoritas
        self.recientes.append(busqueda.accion_de_comando("PolyExtrude"))
        buscador.campo.setText("")
        buscador.campo.textEdited.emit("")
        self.assertEqual([a["nombre"] for a in lista.acciones], ["CenterPivot", "PolyExtrude"])
        self.assertEqual(lista.titulo, "Favoritas · Usadas hace poco")
        _clic(lista, lista.zona_estrella(0).center().toPoint())
        self.assertEqual(favoritos, [])
        self.assertEqual(lista.titulo, "Usadas hace poco")

    def test_clic_en_resultado(self):
        self._escribir("pivot")
        lista = self.buscador.lista
        _clic(lista, QtCore.QPoint(50, 5 + 19))
        self.assertEqual(self.ejecutadas[0]["nombre"], "CenterPivot")

    def test_dibuja(self):
        self._escribir("e")
        self.buscador.lista.grab()
        self.buscador.grab()

    def test_una_lista_rota_no_rompe(self):
        buscador = Buscador(lambda: 1 / 0, self.ejecutadas.append)
        self.addCleanup(buscador.close)
        buscador.campo.textEdited.emit("x")
        self.assertEqual(buscador.lista.acciones, [])


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaSoltar(unittest.TestCase):
    def test_soltar_en_un_boton(self):
        soltados = []
        menu = MenuRadial()
        menu.usar_radial(rd.por_defecto())
        menu.al_soltar = lambda i, b: soltados.append((i, b))
        self.addCleanup(menu.close)
        boton = {"texto": "Extrude", "tipo": "comando", "accion": "PolyExtrude"}
        x, y = rd.posiciones(menu.apariencia["radio"])[2]
        punto = QtCore.QPointF(menu.width() / 2 + x, menu.height() / 2 + y)
        datos = arrastre.datos_mime(boton)
        for tipo in (QEvent.DragEnter, QEvent.DragMove):
            evento = QtGui.QDragMoveEvent(punto.toPoint(), Qt.CopyAction, datos, Qt.LeftButton, Qt.NoModifier,
                                          tipo)
            APP.sendEvent(menu, evento)
        self.assertEqual(menu._sobre, 2)
        APP.sendEvent(menu, QtGui.QDropEvent(punto, Qt.CopyAction, datos, Qt.LeftButton, Qt.NoModifier))
        self.assertEqual(soltados, [(2, boton)])

    def test_mime_raro_no_se_acepta(self):
        datos = QtCore.QMimeData()
        datos.setText("hola")
        self.assertIsNone(arrastre.boton_de(datos))

    def test_codigo_de_un_estante(self):
        mel = QtCore.QMimeData()
        mel.setText("polyCube -w 2;")
        self.assertEqual(arrastre.boton_de(mel)["tipo"], "mel")
        self.assertEqual(arrastre.boton_de(mel)["texto"], "polyCube")
        maya = QtCore.QMimeData()
        maya.setData("application/x-maya-data", QtCore.QByteArray(b"import maya.cmds as cmds\ncmds.polySphere()"))
        boton = arrastre.boton_de(maya)
        self.assertEqual(boton["tipo"], "python")

    def test_arrastrar_un_boton_del_menu(self):
        menu = MenuRadial(al_ejecutar=lambda i, opciones=False: None, al_mover=lambda c: None,
                          al_configurar=lambda: None)
        menu.usar_radial(rd.por_defecto())
        menu.show()
        self.addCleanup(menu.close)
        lanzados = []
        with unittest.mock.patch.object(QtGui.QDrag, "exec", lambda d, *a: lanzados.append(d.mimeData())):
            menu._pulsado, menu._inicio_pulsado = 0, QtCore.QPoint(10, 10)
            evento = QtGui.QMouseEvent(QEvent.MouseMove, QtCore.QPointF(60, 60), QtCore.QPointF(60, 60),
                                       Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
            self.assertTrue(menu._arrastrar_boton(evento))
        self.assertEqual(arrastre.boton_de(lanzados[0])["texto"], rd.por_defecto()["botones"][0]["texto"])


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaVentanaAjustes(unittest.TestCase):
    def test_cambios_en_vivo(self):
        apariencias, formas, velocidades = [], [], []
        ventana = VentanaAjustes(rd.normalizar_apariencia({}), "radial", False, 250,
                                 al_apariencia=apariencias.append,
                                 al_forma=lambda f, v: formas.append((f, v)),
                                 al_velocidad=velocidades.append)
        self.addCleanup(ventana.close)
        ventana.deslizadores["radio"].barra.setValue(120)
        self.assertEqual(apariencias[-1]["radio"], 120)
        ventana.deslizadores["opacidad"].barra.setValue(55)
        self.assertAlmostEqual(apariencias[-1]["opacidad"], 0.55)
        ventana.deslizadores["punto"].barra.setValue(13)
        self.assertEqual(apariencias[-1]["punto"], 6.5)
        self.assertFalse(ventana.deslizadores["pill_boton"].isEnabled())
        ventana.forma_pill.setChecked(True)
        self.assertEqual(formas[-1], ("pill", False))
        self.assertTrue(ventana.deslizadores["pill_boton"].isEnabled())
        ventana.vertical.setChecked(True)
        self.assertEqual(formas[-1], ("pill", True))
        ventana.velocidad.barra.setValue(320)
        self.assertEqual(velocidades[-1], 320)
        ventana._restaurar()
        self.assertEqual(apariencias[-1]["radio"], 84)
        self.assertEqual(velocidades[-1], 250)


def _radial_con_carpeta():
    radial = rd.por_defecto()
    radial["botones"][5] = rd.normalizar_boton({
        "texto": "Más", "tipo": "carpeta",
        "botones": [{"texto": "Cubo", "tipo": "mel", "accion": "polyCube;"}, interruptores.boton("xray")]})
    return rd.normalizar(radial)


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaCarpetasYEstados(unittest.TestCase):
    def setUp(self):
        self.ejecutados, self.carpetas, self.sobre = [], [], []
        self.menu = MenuRadial(al_ejecutar=lambda i, opciones=False: self.ejecutados.append((i, opciones)),
                               al_mover=lambda c: None, al_configurar=lambda: None)
        self.menu.al_carpeta = self.carpetas.append
        self.menu.al_sobre = self.sobre.append
        self.menu.usar_radial(_radial_con_carpeta())
        self.menu.colocar(QtCore.QPoint(400, 300))
        self.menu.show()
        self.addCleanup(self.menu.close)

    def _punto(self, i):
        x, y = rd.posiciones(self.menu.apariencia["radio"])[i]
        return QtCore.QPoint(int(self.menu.width() / 2 + x), int(self.menu.height() / 2 + y))

    def test_abrir_y_cerrar_carpeta(self):
        _clic(self.menu, self._punto(5))
        self.assertEqual(self.menu.carpeta, 5)
        self.assertEqual(self.carpetas, [5])
        self.assertEqual(self.menu.botones_visibles()[0]["texto"], "Cubo")
        self.assertEqual(self.ejecutados, [])
        _clic(self.menu, self._punto(0))
        self.assertEqual(self.ejecutados, [(0, False)])
        _clic(self.menu, QtCore.QPoint(self.menu.width() // 2, self.menu.height() // 2))
        self.assertIsNone(self.menu.carpeta)
        self.assertEqual(self.menu.botones_visibles()[0]["texto"], "Duplicar")

    def test_al_ocultar_sale_de_la_carpeta(self):
        self.menu.abrir_carpeta(5)
        self.menu.hide()
        self.assertIsNone(self.menu.carpeta)
        self.assertIsNone(self.sobre[-1])

    def test_estados_y_anuncio_se_dibujan(self):
        self.menu.fijar_estados([True, False, None])
        self.assertEqual(self.menu.estados[:3], [True, False, None])
        self.assertEqual(len(self.menu.estados), rd.NUM_BOTONES)
        self.menu.anunciar("UV y texturas")
        self.assertFalse(self.menu.grab().isNull())
        self.menu._quitar_anuncio()
        self.assertEqual(self.menu.anuncio, "")

    def test_al_sobre(self):
        _clic(self.menu, self._punto(1))
        self.assertEqual(self.sobre[0]["texto"], self.menu.botones_visibles()[1]["texto"])

    def test_pill_con_nueve_botones(self):
        pill = MenuPill(al_ejecutar=lambda i, opciones=False: self.ejecutados.append((i, opciones)),
                        al_mover=lambda c: None, al_configurar=lambda: None, vertical=False)
        self.addCleanup(pill.close)
        seis = pill.width()
        radial = rd.cambiar_cantidad(_radial_con_carpeta(), 9)
        radial["botones"][8] = {"texto": "Nueve", "tipo": "mel", "accion": "polyCube;"}
        pill.usar_radial(radial)
        pill.show()
        self.assertEqual(pill.num(), 9)
        self.assertGreater(pill.width(), seis)
        x, y, w, h = rd.geometria_pill(pill.apariencia, False, 9)[3][8]
        _clic(pill, QtCore.QPoint(int(1 + x + w / 2), int(1 + y + h / 2)))
        self.assertEqual(self.ejecutados[-1], (8, False))
        pill.fijar_estados([True] * 9)
        pill.abrir_carpeta(5)
        self.assertEqual(len(pill.botones_visibles()), 9)  # la carpeta rellena con huecos vacíos
        self.assertFalse(pill.grab().isNull())
        pill.usar_radial(rd.cambiar_cantidad(radial, 3))
        self.assertEqual(len(pill.estados), 3)

    def test_pill_con_carpeta(self):
        pill = MenuPill(al_ejecutar=lambda i, opciones=False: None, al_mover=lambda c: None,
                        al_configurar=lambda: None, vertical=False)
        self.addCleanup(pill.close)
        pill.usar_radial(_radial_con_carpeta())
        pill.show()
        pill.abrir_carpeta(5)
        pill.anunciar("Modelado")
        self.assertFalse(pill.grab().isNull())
        pill.cerrar_carpeta()
        self.assertIsNone(pill.carpeta)


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaConfiguradorV11(unittest.TestCase):
    def nueva(self, radial=None, carpetas=False):
        self.cambios = []
        ventana = Configurador(radial or rd.por_defecto(), FuentesFalsas(), al_cambiar=self.cambios.append,
                               carpetas=carpetas)
        self.addCleanup(ventana.close)
        return ventana

    def test_carpeta_solo_si_esta_activada(self):
        indice = TIPOS_PAGINA.index("carpeta")
        self.assertTrue(self.nueva().tipo.view().isRowHidden(indice))
        self.assertFalse(self.nueva(carpetas=True).tipo.view().isRowHidden(indice))

    def test_editar_dentro_de_una_carpeta(self):
        ventana = self.nueva(_radial_con_carpeta(), carpetas=True)
        ventana.huecos.setCurrentRow(5)
        ventana.entrar_carpeta(5)
        self.assertEqual(ventana.botones_nivel()[0]["texto"], "Cubo")
        ventana.huecos.setCurrentRow(2)
        ventana.tipo.setCurrentIndex(TIPOS_PAGINA.index("python"))
        ventana.codigo_python.setPlainText("print(1)")
        self.assertEqual(self.cambios[-1]["botones"][5]["botones"][2]["accion"], "print(1)")
        ventana.salir_carpeta()
        self.assertIsNone(ventana.carpeta)

    def test_interruptor(self):
        ventana = self.nueva()
        ventana.huecos.setCurrentRow(1)
        ventana.tipo.setCurrentIndex(TIPOS_PAGINA.index("interruptor"))
        ventana._interruptor_elegido(ventana.lista_interruptores.item(1))
        boton = self.cambios[-1]["botones"][1]
        self.assertEqual(interruptores.clave_de(boton), interruptores.ORDEN[1])
        self.assertEqual(ventana.tipo.currentIndex(), TIPOS_PAGINA.index("interruptor"))

    def test_bloqueado(self):
        radial = rd.por_defecto()
        radial["bloqueado"] = True
        ventana = self.nueva(radial)
        ventana.fijar_cabecera("Examen", False)
        self.assertFalse(ventana.texto.isEnabled())
        self.assertFalse(ventana.tipo.isEnabled())
        self.assertTrue(ventana.boton_guardar.isEnabled())
        self.assertIn("profesor", ventana.cabecera.text())


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaOpcionesAjustes(unittest.TestCase):
    def test_opciones(self):
        cambios, reglas = [], []
        ventana = VentanaAjustes(rd.normalizar_apariencia({}), "radial", False, 250,
                                 opciones={"carpetas": False, "automatico": False, "aprendizaje": True,
                                           "carpeta_clase": ""},
                                 al_opcion=lambda c, v: cambios.append((c, v)), al_reglas=lambda: reglas.append(1))
        self.addCleanup(ventana.close)
        self.assertFalse(ventana.casillas["carpetas"].isChecked())
        self.assertTrue(ventana.casillas["aprendizaje"].isChecked())
        self.assertFalse(ventana.boton_reglas.isEnabled())
        ventana.casillas["automatico"].setChecked(True)
        self.assertEqual(cambios[-1], ("automatico", True))
        self.assertTrue(ventana.boton_reglas.isEnabled())
        ventana.boton_reglas.click()
        self.assertEqual(reglas, [1])
        ventana.fijar_clase("/red/clase", avisar=True)
        self.assertEqual(cambios[-1], ("carpeta_clase", "/red/clase"))
        ventana.quitar_clase.click()
        self.assertEqual(cambios[-1], ("carpeta_clase", ""))
        self.assertFalse(ventana.quitar_clase.isEnabled())

    def test_reglas(self):
        dialogo = DialogoReglas({"ws:Animation": "pre:3_animacion"}, ["Modeling - Standard"],
                                [("pre:1_modelado", "Modelado"), ("pre:3_animacion", "Animación")])
        self.addCleanup(dialogo.close)
        self.assertIn("ws:Animation", dialogo.combos)  # aunque Maya no lo liste
        self.assertIn("sel:uv", dialogo.combos)
        combo = dialogo.combos["sel:caras"]
        combo.setCurrentIndex(combo.findData("pre:1_modelado"))
        self.assertEqual(dialogo.reglas(), {"ws:Animation": "pre:3_animacion", "sel:caras": "pre:1_modelado"})


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaTema(unittest.TestCase):
    def tearDown(self):
        from radial import tema
        tema.aplicar("oscuro", "")

    def test_claro_y_acento(self):
        from radial import buscador, dibujo, menu_pill, tema
        oscuro_fondo = dibujo.COLOR_FONDO.getRgb()
        self.assertTrue(tema.aplicar("claro", ""))
        self.assertGreater(dibujo.COLOR_FONDO.lightness(), 200)
        self.assertLess(dibujo.COLOR_TEXTO.lightness(), 60)
        self.assertEqual(menu_pill.COLOR_ICONO_CLARO, "#1c1c1f")  # iconos oscuros sobre la pill clara
        self.assertFalse(tema.aplicar("claro", ""))  # nada cambia
        tema.aplicar("claro", "#FF9F43")
        self.assertEqual(dibujo.COLOR_ABIERTO.name(), "#ff9f43")
        self.assertEqual(buscador.COLOR_ELEGIDO.name(), "#ff9f43")
        self.assertEqual(dibujo.COLOR_ICONO_OSCURO, "#141414")  # sobre naranja, icono oscuro
        tema.aplicar("oscuro", "#4c3cff")
        self.assertEqual(dibujo.COLOR_ICONO_OSCURO, "#f4f4f4")  # sobre un azul oscuro, icono claro
        tema.aplicar("oscuro", "no es un color")
        self.assertEqual(dibujo.COLOR_FONDO.getRgb(), oscuro_fondo)
        self.assertEqual(dibujo.COLOR_ABIERTO.name(), "#f4f4f4")
        # Se dibuja con los dos temas
        for nombre in tema.TEMAS:
            tema.aplicar(nombre, "#36c28a")
            for clase in (MenuRadial, MenuPill):
                menu = clase()
                menu.usar_radial(rd.por_defecto())
                self.addCleanup(menu.close)
                self.assertFalse(menu.grab().isNull())

    def test_valores(self):
        from radial import tema
        self.assertEqual(tema.normalizar_tema("rosa"), "oscuro")
        self.assertEqual(tema.normalizar_acento("#ABCDEF"), "#abcdef")
        self.assertEqual(tema.normalizar_acento("#abc"), "")
        self.assertEqual(tema.texto_sobre("#ffffff"), "#141414")
        self.assertEqual(tema.texto_sobre("#101010"), "#f4f4f4")


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaAyuda(unittest.TestCase):
    def test_contenido_de_comando(self):
        info = busqueda.accion_de_comando("CenterPivot", "Menu items.Modify", "", "Centrar pivote",
                                          "Pone el pivote en el centro.", "Ctrl+E")
        datos = ayuda.contenido({"texto": "Pivote", "tipo": "comando", "accion": "CenterPivot"}, info,
                                opciones=True)
        self.assertEqual(datos["titulo"], "Centrar pivote")
        self.assertIn("CenterPivot", datos["subtitulo"])
        self.assertEqual(datos["descripcion"], "Pone el pivote en el centro.")
        self.assertEqual(len(datos["lineas"]), 2)

    def test_tarjeta_con_icono_y_menu(self):
        info = dict(busqueda.accion_de_comando("PolyExtrude", "Menu items.Edit Mesh", "", "Extruir"),
                    menu="Edit Mesh › Extrude")
        datos = ayuda.contenido({"texto": "Extruir", "tipo": "comando", "accion": "PolyExtrude"}, info,
                                icono="malla")
        self.assertEqual(datos["icono"], "malla")
        self.assertIn("En Maya: Edit Mesh › Extrude", datos["lineas"])
        self.assertNotIn("Edit Mesh", datos["subtitulo"])  # el menú ya sale abajo
        menu = MenuRadial()
        menu.usar_radial(rd.por_defecto())
        menu.colocar(QtCore.QPoint(400, 300))
        menu.show()
        self.addCleanup(menu.close)
        tarjeta = ayuda.TarjetaAyuda()
        self.addCleanup(tarjeta.close)
        tarjeta.mostrar(datos, menu)
        self.assertFalse(tarjeta.icono.isHidden())
        self.assertFalse(tarjeta.icono.pixmap().isNull())
        tarjeta.mostrar(ayuda.contenido({"texto": "Hola", "tipo": "python", "accion": "print(1)"}), menu)
        self.assertTrue(tarjeta.icono.isHidden())

    def test_reto(self):
        from radial import reto
        lista = [("PolyExtrude", "Ctrl+E"), ("Duplicate", "Ctrl+D"), ("MoveTool", "W")]
        dialogo = reto.dialogo(lista, lambda c: {"PolyExtrude": "Extruir"}.get(c, c))
        self.addCleanup(dialogo.close)
        self.assertIn("Extruir", dialogo.pregunta.text())
        self.assertFalse(dialogo.responder("Ctrl+R"))
        self.assertTrue(dialogo.responder("Ctrl+E"))
        self.assertIsNone(dialogo.responder("Ctrl+E"))  # ya contestada: hay que pulsar Siguiente
        dialogo.siguiente.click()
        dialogo.saltar.click()
        dialogo.siguiente.click()
        # Con el teclado de verdad: la secuencia de Qt se traduce a como lo escribe Maya
        dialogo.teclas.setKeySequence(QtGui.QKeySequence("W"))
        dialogo._comprobar()
        dialogo.siguiente.click()
        self.assertEqual(dialogo.aciertos, 2)
        self.assertIn("2 de 3", dialogo.pregunta.text())
        self.assertIn("Duplicate (Ctrl+D)", dialogo.resultado.text())
        dialogo.grab()

    def test_vacio_e_interruptor(self):
        self.assertIsNone(ayuda.contenido(rd.boton_vacio()))
        datos = ayuda.contenido(interruptores.boton("xray"), encendido=True)
        self.assertTrue(any("encendido" in linea for linea in datos["lineas"]))

    def test_tarjeta_junto_al_menu(self):
        menu = MenuRadial(al_ejecutar=lambda i, opciones=False: None, al_mover=lambda c: None,
                          al_configurar=lambda: None)
        menu.usar_radial(rd.por_defecto())
        menu.colocar(QtCore.QPoint(400, 300))
        menu.show()
        self.addCleanup(menu.close)
        tarjeta = ayuda.TarjetaAyuda()
        self.addCleanup(tarjeta.close)
        self.assertTrue(tarjeta.testAttribute(Qt.WA_TransparentForMouseEvents))
        tarjeta.mostrar(ayuda.contenido(menu.botones_visibles()[0]), menu)
        tarjeta._aparecer()
        self.assertTrue(tarjeta.isVisible())
        self.assertFalse(tarjeta.geometry().intersects(menu.geometry()))
        self.assertFalse(tarjeta.grab().isNull())
        tarjeta.ocultar()
        self.assertFalse(tarjeta.isVisible())



@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaIconosBuscador(unittest.TestCase):
    def test_icono_de_la_herramienta(self):
        pedidos = []
        lista = ListaResultadosPrueba(lambda accion: None)
        lista.buscar_icono = lambda nombre: pedidos.append(nombre) or ":/noExiste.png"
        self.addCleanup(lista.close)
        acciones = [busqueda.accion_de_comando("PolyExtrude"), busqueda.accion_de_comando("SelectAll"),
                    busqueda.accion_de_comando("ZzRaroSinPalabras")]
        lista.fijar(acciones, "poly")
        lista.setFixedWidth(360)
        lista.show()
        self.assertFalse(lista.grab().isNull())
        # Los comandos conocidos usan el icono de línea del plugin, sin preguntar a Maya
        self.assertEqual(lista.icono_de(acciones[0]), "extruir")
        self.assertEqual(lista.icono_de(acciones[1]), "seleccionar_todo")
        self.assertNotIn("PolyExtrude", pedidos)
        # Solo un comando que no se reconoce prueba el icono de Maya
        self.assertEqual(lista.icono_de(acciones[2]), ":/noExiste.png")
        self.assertIn("ZzRaroSinPalabras", pedidos)
        estante = busqueda.accion_de_estante("Poly", {"texto": "Cubo", "icono": "cubo", "tipo": "mel",
                                                      "accion": "polyCube;"})
        self.assertEqual(lista.icono_de(estante), "cubo")


class PruebaIconosAcciones(unittest.TestCase):
    def test_todos_los_iconos_se_dibujan(self):
        from radial import iconos
        from radial.dibujo import pixmap_icono
        for nombre in iconos.TRAZOS:
            mapa = pixmap_icono(nombre, 24, 1.0, "#ececec")
            self.assertIsNotNone(mapa, nombre)
            imagen = mapa.toImage()
            pintados = sum(1 for x in range(0, 24, 2) for y in range(0, 24, 2) if imagen.pixelColor(x, y).alpha() > 40)
            self.assertGreater(pintados, 3, nombre)

    def test_botones_sin_icono_en_radial_y_pill(self):
        radial = rd.por_defecto()
        radial["botones"][0] = {"texto": "Extruir", "detalle": "", "icono": "", "tipo": "comando",
                                "accion": "PolyExtrude"}
        radial["botones"][1] = {"texto": "Mi script", "detalle": "", "icono": "", "tipo": "python",
                                "accion": "print(1)"}
        for clase in (MenuRadial, MenuPill):
            menu = clase()
            self.addCleanup(menu.close)
            menu.usar_radial(rd.normalizar(radial))
            menu.colocar(QtCore.QPoint(300, 300))
            menu.show()
            self.assertFalse(menu.grab().isNull())

if __name__ == "__main__":
    unittest.main()
