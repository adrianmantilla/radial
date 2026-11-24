"""Pruebas del controlador (interfaz_maya) con un Maya falso y Qt sin pantalla.

Comprueban que mostrar, ocultar, cambiar de forma, editar y guardar funcionan
juntos. Lo que depende de Maya de verdad se prueba con herramientas/prueba_maya.py.
"""

import importlib
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:  # pragma: no cover
    QtWidgets = None

if QtWidgets is not None:
    # Se cargan antes de poner el Maya falso: al quitarlo, mock.patch.dict borra de
    # sys.modules lo importado mientras tanto, y borrar módulos de Qt rompe Python.
    for _modulo in ("biblioteca", "configurador", "filtro_teclado", "gestor_radiales",
                    "menu_pill", "menu_radial", "qt", "ventana_ajustes", "buscador", "busqueda", "arrastre"):
        importlib.import_module("radial." + _modulo)


def _maya_falso(carpeta):
    cmds = mock.MagicMock(name="cmds")
    cmds.internalVar.return_value = carpeta + os.sep
    cmds.about.side_effect = lambda **k: False if k.get("batch") else "2027"
    cmds.getPanel.side_effect = lambda **k: "modelPanel4" if k.get("underPointer") else "modelPanel"
    cmds.runTimeCommand.return_value = True
    maya = types.ModuleType("maya")
    maya.cmds = cmds
    maya.mel = mock.MagicMock(name="mel")
    omui = mock.MagicMock(name="OpenMayaUI")
    omui.MQtUtil.mainWindow.return_value = 0
    maya.OpenMayaUI = omui
    return {"maya": maya, "maya.cmds": cmds, "maya.mel": maya.mel, "maya.OpenMayaUI": omui}


@unittest.skipIf(QtWidgets is None, "PySide6 no está instalado")
class PruebaInterfaz(unittest.TestCase):
    def setUp(self):
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        self.tmp = tempfile.TemporaryDirectory()
        self.modulos = mock.patch.dict(sys.modules, _maya_falso(self.tmp.name))
        self.modulos.start()
        for nombre in [m for m in sys.modules if m in ("radial.interfaz_maya", "radial.acciones",
                                                       "radial.fuentes_maya")]:
            del sys.modules[nombre]
        # import_module y no «from radial import ...»: este reutilizaría el módulo de la prueba anterior.
        self.im = importlib.import_module("radial.interfaz_maya")
        self.cmds = sys.modules["maya.cmds"]
        self.im.iniciar()
        # Maya falso sin ventana principal: se pone una para que se instale el filtro.
        self.principal = QtWidgets.QWidget()
        self.principal.winId()
        self.im.ventana_maya = lambda: self.principal
        self.im._instalar_filtro()

    def tearDown(self):
        self.im.detener()
        sys.modules["radial.qt"].destruir(self.principal)
        self.modulos.stop()
        self.tmp.cleanup()

    def test_alternar(self):
        self.assertFalse(self.im.visible())
        self.im.alternar()
        self.assertTrue(self.im.visible())
        self.im.alternar()
        self.assertFalse(self.im.visible())

    def test_doble_tab_desde_el_filtro(self):
        filtro = self.im._estado["filtro"]
        self.assertIsNotNone(filtro)
        self.assertTrue(filtro.detector.pulsar(0, self.im._puede_contar(False)) is False)
        self.assertTrue(self.im._puede_contar(True))

    def test_filtro_en_la_ventana_y_no_en_la_aplicacion(self):
        filtro = self.im._estado["filtro"]
        self.assertEqual(filtro._objetivos, [self.principal.windowHandle()])
        self.im.detener()
        self.assertEqual(filtro._objetivos, [])

    def test_sin_ventana_no_rompe(self):
        self.im._quitar_filtro()
        self.im.ventana_maya = lambda: None
        self.im._instalar_filtro(intentos=0)
        self.assertIsNone(self.im._estado["filtro"])

    def test_fuera_del_visor_no_cuenta(self):
        self.cmds.getPanel.side_effect = lambda **k: "nodeEditorPanel1" if k.get("underPointer") \
            else "scriptedPanel"
        self.assertFalse(self.im._puede_contar(False))
        self.im.mostrar()
        self.assertTrue(self.im._puede_contar(False))  # con el menú a la vista, sí

    def test_cambiar_forma_conserva_visibilidad_y_sitio(self):
        centro = QtCore.QPoint(400, 300)
        self.im._al_mover(centro)
        self.im.mostrar()
        self.im.cambiar_forma("pill", True)
        menu = self.im._menu_flotante(crear=False)
        self.assertEqual(type(menu).__name__, "MenuPill")
        self.assertTrue(menu.vertical)
        self.assertTrue(menu.isVisible())
        self.assertLessEqual((menu.centro_global() - centro).manhattanLength(), 2)
        self.assertEqual(self.im.ajustes().forma, "pill")

    def test_editar_guardar_como_y_cambiar(self):
        radial = self.im.radial_activo()
        radial["botones"][0]["texto"] = "Clonar"
        self.im.modificar_radial(radial)
        self.assertTrue(self.im.biblioteca().sin_guardar)
        self.cmds.promptDialog.side_effect = lambda *a, **k: "Mi clase" if k.get("query") else "Guardar"
        self.assertTrue(self.im.guardar())  # preconfigurado: pide nombre
        self.assertEqual(self.im._nombre_activo(), "Mi clase")
        self.assertFalse(self.im.biblioteca().sin_guardar)
        self.im.usar_radial("pre:3_animacion")
        self.assertEqual(self.im._nombre_activo(), "Animación")

    def test_usar_con_cambios_pregunta(self):
        radial = self.im.radial_activo()
        radial["nombre"] = "x"
        self.im.modificar_radial(radial)
        self.cmds.confirmDialog.return_value = "Cancelar"
        self.im.usar_radial("pre:2_uv_texturas")
        self.assertEqual(self.im.biblioteca().origen, "pre:1_modelado")
        self.cmds.confirmDialog.return_value = "Descartar cambios"
        self.im.usar_radial("pre:2_uv_texturas")
        self.assertEqual(self.im.biblioteca().origen, "pre:2_uv_texturas")

    def test_ventanas_se_abren_y_actualizan(self):
        self.im.abrir_ajustes()
        self.assertTrue(self.im.visible())
        ventana = self.im._ventana("ventana_ajustes")
        ventana.deslizadores["radio"].barra.setValue(110)
        self.assertEqual(self.im._menu_flotante().apariencia["radio"], 110)
        self.im._velocidad_cambiada(330)
        self.assertEqual(self.im._estado["filtro"].detector.ventana_ms, 330)
        gestor = self.im.abrir_gestor()
        self.assertGreater(gestor.lista.count(), 4)

    def test_menu_de_la_barra_se_llena(self):
        self.im._llenar_radiales()
        self.im._llenar_forma()
        etiquetas = [c.kwargs.get("label") for c in self.cmds.menuItem.call_args_list]
        self.assertIn("Modelado", etiquetas)
        self.assertIn("Pill vertical", etiquetas)

    def test_ejecutar_boton(self):
        self.im._al_ejecutar(1)
        sys.modules["maya.mel"].eval.assert_called_with("CenterPivot")

    def test_buscador_bajo_el_menu(self):
        self.im.mostrar()
        QtWidgets.QApplication.processEvents()
        buscador = self.im._estado["buscador"]
        self.assertTrue(buscador.isVisible())
        self.im.cambiar_buscador(False)
        self.assertFalse(buscador.isVisible())
        self.assertFalse(self.im.ajustes().buscador)
        self.im.cambiar_forma("pill", False)
        self.assertIs(self.im._estado["buscador"]._menu, self.im._menu_flotante(crear=False))

    def test_ejecutar_desde_el_buscador_guarda_reciente(self):
        from radial import busqueda
        self.im._al_buscar(busqueda.accion_de_comando("FreezeTransformations"))
        sys.modules["maya.mel"].eval.assert_called_with("FreezeTransformations")
        self.assertEqual(self.im.ajustes().recientes[0]["nombre"], "FreezeTransformations")

    def test_soltar_asigna_el_boton(self):
        self.im._al_soltar(3, {"texto": "Extrude", "tipo": "comando", "accion": "PolyExtrude"})
        self.assertEqual(self.im.radial_activo()["botones"][3]["accion"], "PolyExtrude")
        self.assertTrue(self.im.biblioteca().sin_guardar)

    def test_volver_a_centrar(self):
        self.im._al_mover(QtCore.QPoint(10, 10))
        self.im.volver_a_centrar()
        self.assertIsNone(self.im.ajustes().posicion)


if __name__ == "__main__":
    unittest.main()
