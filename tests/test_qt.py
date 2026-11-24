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


if __name__ == "__main__":
    unittest.main()
