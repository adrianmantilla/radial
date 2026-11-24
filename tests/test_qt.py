"""Pruebas sin Maya del filtro de teclado y del menú, con Qt sin pantalla.

Necesitan PySide6 (``pip install PySide6-Essentials``); si no está, se saltan.
"""

import os
import sys
import unittest

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
    from radial.configurador import Configurador
    from radial.ventana_ajustes import VentanaAjustes
    from radial.buscador import Buscador
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
        self.menu = MenuRadial(al_ejecutar=self.ejecutados.append, al_mover=self.movidos.append,
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
        pill = MenuPill(al_ejecutar=self.ejecutados.append, al_mover=self.movidos.append,
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
        self.ventana.tipo.setCurrentIndex(2)  # Python
        self.ventana.codigo_python.setPlainText("print('hola')")
        boton = self.cambios[-1]["botones"][2]
        self.assertEqual((boton["tipo"], boton["accion"]), ("python", "print('hola')"))
        self.ventana.boton_probar.click()
        self.assertEqual(self.fuentes.probados[-1]["accion"], "print('hola')")

    def test_vaciar_hueco(self):
        self.ventana.huecos.setCurrentRow(5)
        self.ventana.tipo.setCurrentIndex(4)
        self.assertEqual(self.cambios[-1]["botones"][5]["tipo"], "vacio")

    def test_copiar_de_estante(self):
        self.ventana.huecos.setCurrentRow(3)
        self.ventana.tipo.setCurrentIndex(1)
        self.ventana._copiar_de_estante(self.ventana.lista_estante.item(0))
        boton = self.cambios[-1]["botones"][3]
        self.assertEqual((boton["texto"], boton["tipo"], boton["accion"]), ("Cubo", "mel", "polyCube;"))
        self.assertEqual(self.ventana.tipo.currentIndex(), 3)  # muestra la página MEL

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


if __name__ == "__main__":
    unittest.main()
