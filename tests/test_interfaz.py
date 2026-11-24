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
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    QtWidgets = None

if QtWidgets is not None:
    # Se cargan antes de poner el Maya falso: al quitarlo, mock.patch.dict borra de
    # sys.modules lo importado mientras tanto, y borrar módulos de Qt rompe Python.
    for _modulo in ("biblioteca", "configurador", "filtro_teclado", "gestor_radiales",
                    "menu_pill", "menu_radial", "qt", "ventana_ajustes", "buscador", "busqueda", "arrastre",
                    "ayuda", "automatico", "interruptores", "menu_comun"):
        importlib.import_module("radial." + _modulo)


def _maya_falso(carpeta):
    cmds = mock.MagicMock(name="cmds")
    cmds.internalVar.return_value = carpeta + os.sep
    cmds.about.side_effect = lambda **k: False if k.get("batch") else "2027"
    cmds.getPanel.side_effect = lambda **k: "modelPanel4" if k.get("underPointer") else "modelPanel"
    cmds.runTimeCommand.side_effect = lambda *a, **k: [] if k.get("query") else True
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
        for nombre in ("interfaz_maya", "acciones", "fuentes_maya", "pill_extra"):
            sys.modules.pop("radial." + nombre, None)
            # «from radial import x» mira primero el atributo del paquete: también fuera.
            if hasattr(sys.modules["radial"], nombre):
                delattr(sys.modules["radial"], nombre)
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

    def test_opciones_desde_ajustes(self):
        ventana = self.im.abrir_ajustes()
        self.assertFalse(ventana.casillas["carpetas"].isChecked())
        ventana.casillas["carpetas"].setChecked(True)
        self.assertTrue(self.im.ajustes().carpetas)
        configurador = self.im.abrir_configurador()
        self.assertTrue(configurador.carpetas)
        ventana.casillas["aprendizaje"].setChecked(False)
        self.assertFalse(self.im.ajustes().aprendizaje)

    def test_radial_automatico(self):
        from radial import automatico
        contexto = {"valor": ("UV Editing", "objeto")}
        with mock.patch.object(automatico, "contexto_maya", lambda: contexto["valor"]):
            self.im.mostrar()
            self.assertEqual(self.im.biblioteca().origen, "pre:1_modelado")  # desactivado de serie
            self.im.cambiar_opcion("automatico", True)
            self.assertEqual(self.im.biblioteca().origen, "pre:2_uv_texturas")
            self.assertTrue(self.im._estado["reloj_automatico"].isActive())
            # Elegido a mano: se respeta mientras no cambie el contexto.
            self.im.usar_radial("pre:3_animacion")
            self.im._tic_automatico()
            self.assertEqual(self.im.biblioteca().origen, "pre:3_animacion")
            # Con cambios sin guardar no se cambia.
            radial = self.im.radial_activo()
            radial["botones"][0]["texto"] = "X"
            self.im.modificar_radial(radial)
            contexto["valor"] = ("Rendering", "objeto")
            self.im._tic_automatico()
            self.assertEqual(self.im.biblioteca().origen, "pre:3_animacion")
            self.im.biblioteca().restaurar()
            contexto["valor"] = ("Modeling - Standard", "objeto")
            self.im._tic_automatico()
            self.assertEqual(self.im.biblioteca().origen, "pre:1_modelado")
            self.assertEqual(self.im._menu_flotante(crear=False).anuncio, "Modelado")

    def test_modo_clase(self):
        clase = os.path.join(self.tmp.name, "clase")
        os.makedirs(clase)
        self.im.cambiar_opcion("carpeta_clase", clase)
        self.im.biblioteca().exportar(os.path.join(clase, "examen"), bloqueado=True)
        self.im.usar_radial("clase:examen")
        self.im._al_soltar(0, {"texto": "Extrude", "tipo": "comando", "accion": "PolyExtrude"})
        self.assertNotEqual(self.im.radial_activo()["botones"][0].get("accion"), "PolyExtrude")
        self.im._llenar_radiales()
        etiquetas = [c.kwargs.get("label") for c in self.cmds.menuItem.call_args_list]
        self.assertTrue(any(e and e.endswith("Modelado") and e.startswith("\U0001F512") for e in etiquetas))
        configurador = self.im.abrir_configurador()
        self.assertFalse(configurador.texto.isEnabled())

    def test_tarjeta_de_aprendizaje(self):
        self.im.mostrar()
        menu = self.im._menu_flotante(crear=False)
        self.im._buscador()._acciones = []
        self.im._al_sobre(menu.botones_visibles()[0])
        tarjeta = self.im._estado["tarjeta"]
        self.assertIsNotNone(tarjeta.datos)
        self.im._al_sobre(None)
        self.assertIsNone(tarjeta.datos)
        self.im.cambiar_opcion("aprendizaje", False)
        self.im._al_sobre(menu.botones_visibles()[0])
        self.assertIsNone(tarjeta.datos)

    def _extra(self):
        return importlib.import_module("radial.pill_extra")

    def test_pill_extra_independiente(self):
        self.im.cambiar_extra("activa", True)
        extra = self._extra()
        self.assertTrue(extra.visible())
        self.assertFalse(self.im.visible())  # el menú del doble Tab sigue a lo suyo
        self.im.alternar()
        self.assertTrue(self.im.visible() and extra.visible())
        self.im.alternar()
        self.assertTrue(extra.visible())
        # Su propio radial, sin tocar el del menú
        self.im.cambiar_extra("radial", "pre:3_animacion")
        self.assertEqual(extra.biblioteca().origen, "pre:3_animacion")
        self.assertEqual(self.im.biblioteca().origen, "pre:1_modelado")
        self.im.cambiar_extra("apariencia", {"pill_boton": 40, "opacidad": 0.5})
        self.assertEqual(extra.pill(crear=False).apariencia["pill_boton"], 40)
        self.assertNotEqual(self.im.radial_activo()["apariencia"]["opacidad"], 0.5)
        self.im.cambiar_extra("cantidad", 9)
        self.assertEqual(extra.pill(crear=False).num(), 9)
        self.assertEqual(len(self.im.radial_activo()["botones"]), 6)
        self.im.cambiar_extra("vertical", True)
        menu = extra.pill(crear=False)
        self.assertTrue(menu.vertical)
        self.assertGreater(menu.height(), menu.width())
        # Se recuerda
        self.assertTrue(self.im.ajustes().datos["extra"]["activa"])
        self.im.cambiar_extra("activa", False)
        self.assertFalse(extra.visible())

    def test_pill_extra_configurar_y_guardar(self):
        extra = self._extra()
        self.im.cambiar_extra("activa", True)
        configurador = extra.abrir_configurador()
        self.assertIn("Pill extra", configurador.cabecera.text())
        radial = extra.biblioteca().activo
        radial["botones"][0]["texto"] = "Extra"
        extra.modificar(radial)
        self.assertEqual(extra.pill(crear=False).radial["botones"][0]["texto"], "Extra")
        self.assertNotEqual(self.im.radial_activo()["botones"][0]["texto"], "Extra")
        self.cmds.promptDialog.side_effect = lambda *a, **k: "Mi pill" if k.get("query") else "Guardar"
        self.assertTrue(extra.guardar())
        self.assertTrue(extra.biblioteca().origen.startswith("mio:"))
        self.assertIn(extra.biblioteca().origen, [i for i, _ in self.im.biblioteca().mios()])

    def test_pill_extra_al_arrancar(self):
        self.im.cambiar_extra("activa", True)
        self.im.detener()
        self.im.iniciar()
        self.im._iniciar_extra()
        self.assertTrue(self._extra().visible())

    def test_ajustes_con_pill_extra(self):
        ventana = self.im.abrir_ajustes()
        self.assertFalse(ventana.extra_activa.isChecked())
        self.assertFalse(ventana.extra_controles.isEnabled())
        ventana.extra_activa.setChecked(True)
        self.assertTrue(self._extra().visible())

        indice = ventana.extra_radial.findData("pre:2_uv_texturas")
        ventana.extra_radial.setCurrentIndex(indice)
        ventana.extra_radial.activated.emit(indice)
        self.assertEqual(self._extra().biblioteca().origen, "pre:2_uv_texturas")
        ventana.extra_cantidad.setValue(4)
        self.assertEqual(self._extra().pill(crear=False).num(), 4)

    def test_icono_de_cada_herramienta(self):
        self.cmds.runTimeCommand.side_effect = lambda *a, **k: (
            "" if k.get("image") else ([] if k.get("query") else True))
        self.cmds.resourceManager.side_effect = lambda **k: (
            ["polyExtrudeFacet.png"] if k.get("nameFilter") == "polyExtrudeFacet.png" else [])
        self.assertEqual(self.im._icono_de_comando("PolyExtrude"), ":/polyExtrudeFacet.png")
        self.assertEqual(self.im._icono_de_comando("NoTieneIcono"), "")

    def test_gesto_ejecuta_y_cierra(self):
        filtro = self.im._estado["filtro"]
        filtro.manteniendo = True
        with mock.patch.object(QtGui.QCursor, "pos", staticmethod(lambda: QtCore.QPoint(-3000, -3000))):
            self.im._al_doble_tab()
            self.assertTrue(self.im.visible())
            self.assertIsNotNone(self.im._estado["gesto"])
        # Se mueve hacia abajo: botón 4 del radial (índice 3)
        with mock.patch.object(QtGui.QCursor, "pos", staticmethod(lambda: QtCore.QPoint(-3000, -2900))):
            self.im._seguir_gesto()
            self.assertEqual(self.im._menu_flotante(crear=False)._sobre, 3)
            filtro.manteniendo = False
            self.im._al_soltar_tab()
        esperado = self.im.radial_activo()["botones"][3]
        self.assertFalse(self.im.visible())
        self.assertTrue(self.cmds.method_calls or sys.modules["maya.mel"].eval.called, esperado)

    def test_gesto_sin_evento_de_soltar_no_se_queda_pegado(self):
        """Si el soltar de Tab no llega, el gesto no sigue al ratón para siempre."""
        from radial import filtro_teclado
        filtro = self.im._estado["filtro"]
        filtro.manteniendo = True
        with mock.patch.object(filtro_teclado, "tab_pulsado", lambda: None), \
                mock.patch.object(QtGui.QCursor, "pos", staticmethod(lambda: QtCore.QPoint(-3000, -3000))):
            self.im._al_doble_tab()
        menu = self.im._menu_flotante(crear=False)
        filtro.ultimo_tab = 0
        self.im._estado["gesto_ms"] -= self.im.GESTO_SIN_REPETICION_MS + 1
        with mock.patch.object(QtGui.QCursor, "pos", staticmethod(lambda: QtCore.QPoint(-3000, -2900))):
            self.im._seguir_gesto()
            self.assertFalse(filtro.manteniendo)
            self.assertIsNone(menu._sobre)
            self.im._seguir_gesto()
            self.assertIsNone(menu._sobre)
        self.assertTrue(self.im.visible())
        self.assertNotIn("gesto", self.im._estado)

    def test_gesto_termina_cuando_el_sistema_dice_que_se_solto(self):
        from radial import filtro_teclado
        filtro = self.im._estado["filtro"]
        filtro.manteniendo = True
        pulsado = [True]
        with mock.patch.object(filtro_teclado, "tab_pulsado", lambda: pulsado[0]):
            with mock.patch.object(QtGui.QCursor, "pos", staticmethod(lambda: QtCore.QPoint(-3000, -3000))):
                self.im._al_doble_tab()
            with mock.patch.object(QtGui.QCursor, "pos", staticmethod(lambda: QtCore.QPoint(-3000, -2900))):
                self.im._seguir_gesto()
                self.assertEqual(self.im._menu_flotante(crear=False)._sobre, 3)
                pulsado[0] = False
                self.im._seguir_gesto()
        self.assertFalse(filtro.manteniendo)
        self.assertFalse(self.im.visible())  # se ejecutó el botón y el menú se cerró

    def test_soltar_normal_aunque_el_reloj_pase_antes(self):
        filtro = self.im._estado["filtro"]
        filtro.manteniendo = True
        with mock.patch.object(QtGui.QCursor, "pos", staticmethod(lambda: QtCore.QPoint(-3000, -3000))):
            self.im._al_doble_tab()
        with mock.patch.object(QtGui.QCursor, "pos", staticmethod(lambda: QtCore.QPoint(-3000, -2900))):
            self.im._seguir_gesto()
            filtro.manteniendo = False  # llegó el soltar; su aviso va después del reloj
            self.im._seguir_gesto()
            self.im._al_soltar_tab()
        self.assertFalse(self.im.visible())

    def test_soltar_sin_moverse_deja_el_menu(self):
        filtro = self.im._estado["filtro"]
        filtro.manteniendo = True
        with mock.patch.object(QtGui.QCursor, "pos", staticmethod(lambda: QtCore.QPoint(-3000, -3000))):
            self.im._al_doble_tab()
            filtro.manteniendo = False
            self.im._al_soltar_tab()
        self.assertTrue(self.im.visible())

    def test_numero_de_botones_del_menu(self):
        self.im.mostrar()
        ventana = self.im.abrir_ajustes()
        ventana.cantidad.setValue(8)
        self.assertEqual(len(self.im.radial_activo()["botones"]), 8)
        self.assertEqual(self.im._menu_flotante(crear=False).num(), 8)
        self.assertTrue(self.im.biblioteca().sin_guardar)

    def test_atajo_de_teclado(self):
        self.cmds.hotkeySet.side_effect = lambda *a, **k: "Maya_Default" if k.get("current") and k.get("query") \
            else False
        self.cmds.hotkeyCheck.side_effect = lambda **k: "PolyExtrude" if k.get("keyString") == "e" else ""
        self.assertEqual(self.im.cambiar_atajo("Ctrl+Alt+R"), "")
        self.assertEqual(self.im.ajustes().atajo, "Ctrl+Alt+R")
        self.assertTrue(self.cmds.hotkey.called)
        self.cmds.hotkeySet.assert_any_call("Radial", source="Maya_Default", current=True)
        self.assertIn("PolyExtrude", self.im.cambiar_atajo("Ctrl+E"))  # no pisa los de Maya
        self.assertEqual(self.im.ajustes().atajo, "Ctrl+Alt+R")
        self.assertTrue(self.im.cambiar_atajo("R"))  # sin modificador no vale
        self.assertEqual(self.im.cambiar_atajo(""), "")
        self.assertEqual(self.im.ajustes().atajo, "")

    def test_boton_con_lo_ultimo_que_hice(self):
        from radial import grabar
        registro = "polyExtrudeFacet -ltz 0.5 pCube1.f[1];\npolyBevel3 -fraction 0.2 pCube1.e[4];\n"
        vistos = []

        def aceptar(dialogo):
            vistos.append(dialogo)
            self.assertEqual(dialogo.elegidas(), ["polyBevel3 -fraction 0.2 pCube1.e[4];"])
            dialogo.lista.item(0).setCheckState(QtCore.Qt.Checked)
            dialogo.nombre.setText("Extruir y biselar")
            return True

        vacios = [i for i, b in enumerate(self.im.radial_activo()["botones"]) if b["tipo"] == "vacio"]
        if not vacios:
            radial = self.im.radial_activo()
            radial["botones"][5] = {"tipo": "vacio"}
            self.im.modificar_radial(radial)
            vacios = [5]
        with mock.patch.object(grabar, "registro_maya", return_value=registro), \
                mock.patch.object(self.im, "_ejecutar_dialogo", side_effect=aceptar):
            self.assertTrue(self.im.crear_boton_de_lo_ultimo())
        self.assertEqual(vistos[0].hueco.currentData(), vacios[0])  # el primer hueco libre
        boton = self.im.radial_activo()["botones"][vacios[0]]
        self.assertEqual(boton["texto"], "Extruir y biselar")
        self.assertEqual(boton["accion"].splitlines(), registro.splitlines())
        self.assertTrue(self.im.biblioteca().sin_guardar)

    def test_boton_con_lo_ultimo_sin_ordenes(self):
        from radial import grabar
        with mock.patch.object(grabar, "registro_maya", return_value="// nada //"), \
                mock.patch.object(self.im, "_ejecutar_dialogo") as ejecutar:
            self.assertFalse(self.im.crear_boton_de_lo_ultimo())
        ejecutar.assert_not_called()
        self.assertTrue(self.cmds.confirmDialog.called)

    def test_menus_de_maya_en_el_buscador(self):
        from radial import fuentes_maya

        class Menus(object):
            """Un menú «Modify» con un submenú, un divisor, una caja de opciones y una orden en Python."""
            items = {
                "MayaWindow|mainModifyMenu": ["m1", "m2", "m3", "m4", "m5"],
                "MayaWindow|mainModifyMenu|m4": ["s1"],
            }
            datos = {
                "m1": dict(label="Centrar pivote", runTimeCommand="CenterPivot"),
                "m2": dict(divider=True),
                "m3": dict(label="", optionBox=True),
                "m4": dict(label="Pivot", subMenu=True),
                "m5": dict(label="Mi orden...", command="print('hola')", sourceType="python"),
                "s1": dict(label="Bake Pivot", command="BakeCustomToolPivot;"),
            }

            def window(self, nombre, **k):
                return ["mainModifyMenu"]

            def menu(self, nombre, **k):
                if k.get("label"):
                    return "&Modify"
                if k.get("itemArray"):
                    return []  # todavía sin crear: hay que llamar a su postMenuCommand
                if k.get("postMenuCommand"):
                    return "buildModifyMenu MayaWindow|mainModifyMenu"
                return None

            def menuItem(self, nombre, **k):
                if k.get("itemArray"):
                    return Menus.items.get(nombre, [])
                propio = Menus.datos[nombre.split("|")[-1]]
                for clave in k:
                    if clave != "query":
                        return propio.get(clave, "" if clave not in ("divider", "optionBox", "subMenu")
                                          else False)

        construidos = []
        falsos = Menus()
        original = falsos.menu

        def menu(nombre, **k):
            if k.get("itemArray") and construidos:
                return Menus.items[nombre]
            return original(nombre, **k)

        falsos.menu = menu
        mel = mock.MagicMock()
        mel.eval.side_effect = construidos.append
        with mock.patch.object(fuentes_maya, "cmds", falsos), mock.patch.object(fuentes_maya, "mel", mel):
            menus = fuentes_maya.FuentesMaya().menus()
        self.assertEqual(construidos, ["buildModifyMenu MayaWindow|mainModifyMenu"])
        self.assertEqual([(r, e, b["tipo"], b["accion"]) for r, e, b in menus], [
            (["Modify"], "Centrar pivote", "comando", "CenterPivot"),
            (["Modify", "Pivot"], "Bake Pivot", "mel", "BakeCustomToolPivot;"),
            (["Modify"], "Mi orden", "python", "print('hola')"),
        ])

    def test_scripts_propios_en_el_buscador(self):
        from radial import fuentes_maya
        for archivo in ("limpiar.py", "renombrar.mel", "userSetup.py", "notas.txt"):
            open(os.path.join(self.tmp.name, archivo), "w").close()
        rutas = fuentes_maya.FuentesMaya().scripts()
        self.assertEqual([os.path.basename(r) for r in rutas], ["limpiar.py", "renombrar.mel"])
        acciones = self.im._acciones_buscador()
        self.assertIn("Mis scripts", [a["categoria"] for a in acciones])

    def test_favoritas_se_guardan(self):
        from radial import busqueda
        accion = busqueda.accion_de_comando("CenterPivot")
        self.im._alternar_favorito(accion)
        self.assertEqual([a["nombre"] for a in self.im.ajustes().favoritos], ["CenterPivot"])
        self.im._alternar_favorito(accion)
        self.assertEqual(self.im.ajustes().favoritos, [])

    def test_paquete_de_clase(self):
        from radial import paquete, pill_extra
        ruta = os.path.join(self.tmp.name, "clase", "modelado.radialclase")
        self.im.cambiar_forma("pill", True)
        pill_extra.activar(True)
        pill_extra.cambiar_cantidad(3)
        self.cmds.confirmDialog.side_effect = lambda **k: k["button"][0]  # «Fijar opciones»
        self.cmds.fileDialog2.return_value = [ruta]
        self.assertEqual(self.im.exportar_paquete(), ruta)
        self.assertEqual(paquete.leer(ruta)["fijas"], list(paquete.OPCIONES))
        # Un alumno con otras opciones lo importa
        self.im.cambiar_forma("radial")
        pill_extra.activar(False)
        self.assertTrue(self.im.importar_paquete(ruta))
        self.assertEqual((self.im.ajustes().forma, self.im.ajustes().pill_vertical), ("pill", True))
        self.assertTrue(self.im.biblioteca().origen.startswith("mio:"))
        self.assertTrue(pill_extra.ajustes().activa)
        self.assertEqual(len(pill_extra.biblioteca().activo["botones"]), 3)
        # En la carpeta de clase, las opciones quedan fijadas y bloqueadas en Ajustes
        self.im.cambiar_forma("radial")
        self.im.cambiar_opcion("carpeta_clase", os.path.dirname(ruta))
        self.assertEqual(self.im.ajustes().forma, "pill")
        ventana = self.im.abrir_ajustes()
        self.assertFalse(ventana.forma_radial.isEnabled())
        self.assertFalse(ventana.velocidad.isEnabled())
        self.assertTrue(ventana.forma_pill.isChecked())
        self.assertFalse(ventana.nota_fijadas.isHidden())
        self.assertTrue(ventana.cantidad.isEnabled())  # lo demás sigue libre
        self.im.cambiar_opcion("carpeta_clase", "")
        self.assertEqual(self.im.ajustes().forma, "radial")
        self.assertTrue(ventana.forma_radial.isEnabled())

    def test_paquete_roto(self):
        ruta = os.path.join(self.tmp.name, "roto.radialclase")
        with open(ruta, "w") as f:
            f.write("{}")
        self.assertFalse(self.im.importar_paquete(ruta))
        self.assertTrue(self.cmds.warning.called)

    def test_usos_y_reto(self):
        from radial import acciones
        self.assertIn(self.im._al_usar, acciones.oyentes)
        self.im._estado["atajos"] = {"PolyExtrude": "Ctrl+E"}
        self.cmds.runTimeCommand.side_effect = lambda *a, **k: [] if k.get("query") else True
        boton = {"texto": "Extruir", "tipo": "comando", "accion": "PolyExtrude"}
        for _ in range(3):
            acciones.ejecutar(boton)
        self.assertEqual(self.im.ajustes().usos["PolyExtrude"], 3)
        self.assertTrue(self.cmds.inViewMessage.called)  # a la tercera recuerda el atajo
        with mock.patch.object(self.im, "_atajos", return_value={"PolyExtrude": "Ctrl+E"}):
            ventana = self.im.abrir_reto()
        self.assertEqual(ventana.lista, [("PolyExtrude", "Ctrl+E")])
        self.im.detener()
        self.assertNotIn(self.im._al_usar, acciones.oyentes)
        self.im.iniciar()

    def test_reto_sin_atajos(self):
        with mock.patch.object(self.im, "_atajos", return_value={}):
            self.assertIsNone(self.im.abrir_reto())
        self.assertTrue(self.cmds.confirmDialog.called)

    def test_aspecto(self):
        from radial import dibujo, i18n, tema
        self.addCleanup(tema.aplicar, "oscuro", "")
        self.addCleanup(i18n.usar_idioma, "es")
        self.im.mostrar()
        menu_antes = self.im._menu_flotante(crear=False)
        ventana = self.im.abrir_ajustes()
        ventana.tema_claro.setChecked(True)
        self.assertEqual(self.im.ajustes().tema, "claro")
        self.assertGreater(dibujo.COLOR_FONDO.lightness(), 200)
        menu = self.im._menu_flotante(crear=False)
        self.assertIsNot(menu, menu_antes)  # se rehace con los colores nuevos
        self.assertTrue(self.im.visible())
        ventana.muestras["#ff6b9a"].click()
        self.assertEqual(self.im.ajustes().acento, "#ff6b9a")
        self.assertTrue(ventana.muestras["#ff6b9a"].isChecked())
        self.assertEqual(dibujo.COLOR_ABIERTO.name(), "#ff6b9a")
        # Idioma: el menú de Maya se rehace en inglés y la ventana vuelve a abrirse
        ventana.idioma.setCurrentIndex(ventana.idioma.findData("en"))
        self.assertEqual(self.im.ajustes().idioma, "en")
        self.assertEqual(i18n.t("menu_ajustes"), "Settings...")
        self.cmds.menuItem.assert_any_call(label="Settings...", command=mock.ANY)
        self.app.processEvents()
        nueva = self.im._ventana("ventana_ajustes")
        self.assertIsNotNone(nueva)
        self.assertEqual(nueva.windowTitle(), "Radial · Settings")

    def test_iconos_de_radial_o_de_maya(self):
        from radial import iconos
        self.addCleanup(iconos.usar_iconos, "propios")
        boton = {"texto": "Extruir", "tipo": "comando", "accion": "PolyExtrude", "icono": ""}
        self.assertEqual(self.im.ajustes().iconos, "propios")  # por defecto, los del plugin
        self.assertEqual(iconos.de_boton(boton), "extruir")
        self.im.mostrar()
        ventana = self.im.abrir_ajustes()
        self.assertTrue(ventana.iconos_propios.isChecked())
        with mock.patch.object(self.im, "_icono_de_comando",
                               side_effect=lambda c: ":/polyExtrude.png" if c == "PolyExtrude" else ""):
            iconos.usar_iconos("propios", self.im._icono_de_comando)
            ventana.iconos_maya.setChecked(True)
            self.assertEqual(self.im.ajustes().iconos, "maya")
            self.assertEqual(iconos.de_boton(boton), ":/polyExtrude.png")
            # Sin icono de Maya, el del plugin; uno elegido a mano no se toca
            from radial import iconos_acciones
            self.assertEqual(iconos.de_boton(dict(boton, accion="CenterPivot")),
                             iconos_acciones.icono_de_comando("CenterPivot"))
            self.assertEqual(iconos.de_boton(dict(boton, icono="cubo")), "cubo")
            self.assertTrue(self.im.visible())
            ventana.iconos_propios.setChecked(True)
            self.assertEqual(iconos.de_boton(boton), "extruir")

    def test_volver_a_centrar(self):
        self.im._al_mover(QtCore.QPoint(10, 10))
        self.im.volver_a_centrar()
        self.assertIsNone(self.im.ajustes().posicion)


if __name__ == "__main__":
    unittest.main()
