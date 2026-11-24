"""Pruebas sin Maya de lo nuevo en 1.1: interruptores, carpetas, clase, radial automático y ayuda."""

import os
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

from radial import ajustes as aj  # noqa: E402
from radial import automatico, grabar, interruptores  # noqa: E402
from radial import radiales as rd  # noqa: E402
from radial.biblioteca import CLASE, MIO, Biblioteca  # noqa: E402
from radial.i18n import sinonimos  # noqa: E402


class PruebaAutomatico(unittest.TestCase):
    REGLAS = {"ws:Modeling - Standard": "pre:1_modelado", "sel:uv": "pre:2_uv_texturas"}

    def test_workspace(self):
        self.assertEqual(automatico.elegir(self.REGLAS, "Modeling - Standard", "objeto"), "pre:1_modelado")

    def test_el_modo_de_seleccion_manda(self):
        self.assertEqual(automatico.elegir(self.REGLAS, "Modeling - Standard", "uv"), "pre:2_uv_texturas")

    def test_sin_regla(self):
        self.assertIsNone(automatico.elegir(self.REGLAS, "Sculpting", "caras"))
        self.assertIsNone(automatico.elegir({}, None, None))

    def test_reglas_por_defecto_existen(self):
        pre = {"pre:" + n for n, _ in rd.preconfigurados()}
        self.assertTrue(set(aj.REGLAS_POR_DEFECTO.values()) <= pre)


class PruebaInterruptores(unittest.TestCase):
    def test_botones(self):
        for clave in interruptores.ORDEN:
            boton = rd.normalizar_boton(interruptores.boton(clave))
            self.assertEqual(boton["tipo"], "python")
            self.assertEqual(interruptores.clave_de(boton), clave)
            self.assertIn("alternar({!r})".format(clave), boton["accion"])

    def test_clave_de_otro_boton(self):
        self.assertIsNone(interruptores.clave_de({"estado": "cmds.grid(q=True, toggle=True)"}))
        self.assertIsNone(interruptores.clave_de({"estado": "radial:no_existe"}))
        self.assertIsNone(interruptores.clave_de(None))


class PruebaCarpetas(unittest.TestCase):
    def test_carpeta_con_seis_botones(self):
        boton = rd.normalizar_boton({"texto": "Más", "tipo": "carpeta",
                                     "botones": [{"texto": "A", "tipo": "comando", "accion": "A"}]})
        self.assertEqual(boton["tipo"], "carpeta")
        self.assertEqual(len(boton["botones"]), rd.NUM_BOTONES)
        self.assertEqual(boton["botones"][0]["accion"], "A")
        self.assertEqual(boton["botones"][5]["tipo"], "vacio")

    def test_sin_carpetas_dentro_de_carpetas(self):
        dentro = {"texto": "Otra", "tipo": "carpeta", "botones": []}
        boton = rd.normalizar_boton({"texto": "Más", "tipo": "carpeta", "botones": [dentro]})
        self.assertNotEqual(boton["botones"][0]["tipo"], "carpeta")

    def test_se_guarda_y_se_lee(self):
        radial = rd.por_defecto()
        radial["botones"][5] = {"texto": "Más", "tipo": "carpeta",
                                "botones": [{"texto": "B", "tipo": "mel", "accion": "polyCube;"}]}
        with tempfile.TemporaryDirectory() as tmp:
            ruta = rd.escribir(radial, os.path.join(tmp, "x" + rd.EXTENSION))
            leido = rd.leer(ruta)
        self.assertEqual(leido["botones"][5]["botones"][0]["accion"], "polyCube;")


class PruebaClase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.prefs = os.path.join(self.tmp.name, "prefs")
        self.clase = os.path.join(self.tmp.name, "clase")
        os.makedirs(self.clase)

    def nueva(self):
        ajustes = aj.Ajustes(self.prefs)
        ajustes.carpeta_clase = self.clase
        return Biblioteca(ajustes, os.path.join(self.prefs, "radiales"))

    def test_exportar_bloqueado_y_usar_de_clase(self):
        b = self.nueva()
        b.exportar(os.path.join(self.clase, "examen"), bloqueado=True)
        self.assertEqual(b.de_clase(), [(CLASE + "examen", "Modelado", True)])
        b.usar(CLASE + "examen")
        self.assertTrue(b.es_de_clase)
        self.assertTrue(b.es_preconfigurado)  # no se sobrescribe
        self.assertFalse(b.guardar_cambios())

    def test_la_copia_mia_no_esta_bloqueada(self):
        b = self.nueva()
        b.exportar(os.path.join(self.clase, "examen"), bloqueado=True)
        b.usar(CLASE + "examen")
        b.guardar_como("Mi examen")
        self.assertTrue(b.origen.startswith(MIO))
        self.assertFalse(b.activo.get("bloqueado"))
        self.assertFalse(b.es_preconfigurado)

    def test_el_profesor_cambia_el_radial(self):
        b = self.nueva()
        ruta = b.exportar(os.path.join(self.clase, "examen"))
        b.usar(CLASE + "examen")
        radial = rd.leer(ruta)
        radial["botones"][0]["texto"] = "Nuevo"
        rd.escribir(radial, ruta)
        self.assertTrue(b.refrescar_clase())
        self.assertEqual(b.activo["botones"][0]["texto"], "Nuevo")
        self.assertFalse(b.refrescar_clase())

    def test_carpeta_de_clase_por_variable(self):
        anterior = os.environ.get("RADIAL_CLASE")
        os.environ["RADIAL_CLASE"] = self.clase
        self.addCleanup(lambda: os.environ.pop("RADIAL_CLASE") if anterior is None
                        else os.environ.__setitem__("RADIAL_CLASE", anterior))
        self.assertEqual(aj.Ajustes(self.prefs).carpeta_clase, self.clase)


class PruebaOpciones(unittest.TestCase):
    def test_valores_por_defecto(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = aj.Ajustes(tmp)
            self.assertFalse(a.carpetas)
            self.assertFalse(a.automatico)
            self.assertTrue(a.aprendizaje)
            self.assertEqual(a.reglas, aj.REGLAS_POR_DEFECTO)
            a.carpetas, a.automatico, a.aprendizaje = True, True, False
            a.reglas = {"sel:uv": "pre:2_uv_texturas"}
            a.guardar()
            b = aj.Ajustes(tmp)
            self.assertEqual((b.carpetas, b.automatico, b.aprendizaje), (True, True, False))
            self.assertEqual(b.reglas, {"sel:uv": "pre:2_uv_texturas"})


class PruebaAjustesExtra(unittest.TestCase):
    def test_radial_propio_e_independiente(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = aj.Ajustes(tmp)
            extra = aj.AjustesExtra(base)
            self.assertFalse(extra.activa)
            principal = Biblioteca(base, os.path.join(tmp, "radiales"))
            otra = Biblioteca(extra, os.path.join(tmp, "radiales"))
            otra.usar("pre:3_animacion")
            extra.activa, extra.vertical, extra.posicion = True, True, (10, 20)
            radial = otra.activo
            radial["botones"][0]["texto"] = "Solo en la extra"
            otra.modificar(radial)
            self.assertEqual(principal.origen, "pre:1_modelado")
            self.assertFalse(principal.sin_guardar)
            nueva = aj.AjustesExtra(aj.Ajustes(tmp))
            self.assertEqual((nueva.activa, nueva.vertical, nueva.posicion), (True, True, (10, 20)))
            self.assertEqual(Biblioteca(nueva, os.path.join(tmp, "radiales")).activo["botones"][0]["texto"],
                             "Solo en la extra")


class PruebaCantidad(unittest.TestCase):
    def test_por_defecto_seis_y_limites(self):
        self.assertEqual(len(rd.por_defecto()["botones"]), 6)
        self.assertNotIn("cantidad", rd.por_defecto())
        for pedida, esperada in ((9, 9), (1, rd.MIN_BOTONES), (40, rd.MAX_BOTONES), ("x", 6), (True, 6)):
            radial = rd.normalizar({"botones": [], "cantidad": pedida})
            self.assertEqual(len(radial["botones"]), esperada, pedida)

    def test_cambiar_cantidad_conserva_lo_que_cabe(self):
        radial = rd.cambiar_cantidad(rd.por_defecto(), 8)
        self.assertEqual(len(radial["botones"]), 8)
        self.assertEqual(radial["botones"][0], rd.por_defecto()["botones"][0])
        self.assertEqual(radial["botones"][7]["tipo"], "vacio")
        menos = rd.cambiar_cantidad(radial, 3)
        self.assertEqual(len(menos["botones"]), 3)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(len(rd.leer(rd.escribir(radial, os.path.join(tmp, "a.radial")))["botones"]), 8)

    def test_geometria_de_la_pill(self):
        ap = rd.normalizar_apariencia({})
        ancho6 = rd.geometria_pill(ap)[0]
        ancho9, _, _, botones = rd.geometria_pill(ap, n=9)
        self.assertEqual(len(botones), 9)
        self.assertGreater(ancho9, ancho6)
        x, y, w, h = botones[8]
        self.assertEqual(rd.que_hay_en_pill(x + w / 2, y + h / 2, ap, n=9), 8)
        self.assertEqual(len(rd.posiciones(80, 9)), 9)


class PruebaAtajo(unittest.TestCase):
    def test_partes(self):
        from radial import atajo
        windows = atajo.partes("Ctrl+Alt+R", mac=False)
        self.assertEqual(windows, {"keyShortcut": "r", "ctrlModifier": True, "altModifier": True,
                                   "commandModifier": False})
        mac = atajo.partes("Ctrl+Shift+R", mac=True)
        self.assertEqual((mac["keyShortcut"], mac["commandModifier"], mac["ctrlModifier"]), ("R", True, False))
        self.assertTrue(atajo.partes("Meta+F5", mac=True)["ctrlModifier"])
        self.assertEqual(atajo.partes("Alt+Space", mac=False)["keyShortcut"], "Space")
        for malo in ("R", "Shift+R", "", "Ctrl+", "Hyper+R", "Ctrl+Raro"):
            with self.assertRaises(atajo.AtajoNoValido):
                atajo.partes(malo, mac=False)


class PruebaGrabar(unittest.TestCase):
    REGISTRO = """// Result: pCube1
select -r pCube1 ;
polyExtrudeFacet -constructionHistory 1 -keepFacesTogether 1 pCube1.f[1];
// Result: polyExtrudeFace1 //
setAttr "polyExtrudeFace1.localTranslate" -type double3 0 0 0.5 ;
setAttr "polyExtrudeFace1.localTranslate" -type double3 0 0 0.5 ;
setToolTo moveSuperContext;
# Warning: algo #
polyBevel3 -fraction 0.2 pCube1.e[4];
sin punto y coma
"""

    def test_solo_ordenes_utiles(self):
        self.assertEqual(grabar.ordenes(self.REGISTRO), [
            "polyExtrudeFacet -constructionHistory 1 -keepFacesTogether 1 pCube1.f[1];",
            'setAttr "polyExtrudeFace1.localTranslate" -type double3 0 0 0.5 ;',
            "polyBevel3 -fraction 0.2 pCube1.e[4];"])
        self.assertEqual(len(grabar.ordenes(self.REGISTRO, limite=1)), 1)
        self.assertEqual(grabar.ordenes(None), [])

    def test_boton(self):
        boton = grabar.boton(["polyBevel3 -fraction 0.2;", "  "])
        self.assertEqual(boton["tipo"], "mel")
        self.assertEqual(boton["texto"], "polyBevel3")
        self.assertEqual(boton["accion"], "polyBevel3 -fraction 0.2;")
        self.assertEqual(grabar.boton(["a;", "b;"], "Mío")["accion"], "a;\nb;")
        self.assertIsNone(grabar.boton([]))
        rd.normalizar_boton(boton)  # es un botón válido


class PruebaGlosario(unittest.TestCase):
    def test_formato(self):
        from radial.busqueda import sin_acentos
        from radial.i18n import glosario
        datos = glosario("es")
        self.assertGreater(len(datos), 200)
        for clave, valor in datos.items():
            self.assertEqual(clave, sin_acentos(clave))
            self.assertTrue(valor)


class PruebaSinonimos(unittest.TestCase):
    def test_formato(self):
        datos = sinonimos("es")
        self.assertGreater(len(datos), 150)
        for nombre, extra in datos.items():
            self.assertTrue(extra.get("es"), nombre)


if __name__ == "__main__":
    unittest.main()
