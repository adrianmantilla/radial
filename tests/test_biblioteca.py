"""Pruebas sin Maya de la biblioteca de radiales y de la forma pill."""

import os
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

from radial import ajustes as aj  # noqa: E402
from radial import radiales as rd  # noqa: E402
from radial.biblioteca import MIO, PRE, Biblioteca  # noqa: E402


class PruebaBiblioteca(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.prefs = os.path.join(self.tmp.name, "prefs")
        self.mios = os.path.join(self.prefs, "radiales")

    def tearDown(self):
        self.tmp.cleanup()

    def nueva(self):
        return Biblioteca(aj.Ajustes(self.prefs), self.mios)

    def test_por_defecto_el_primer_preconfigurado(self):
        b = self.nueva()
        self.assertEqual(b.origen, PRE + "1_modelado")
        self.assertTrue(b.es_preconfigurado)
        self.assertEqual(b.activo["nombre"], "Modelado")
        self.assertFalse(b.sin_guardar)

    def test_cuatro_preconfigurados(self):
        nombres = [n for _, n in self.nueva().preconfigurados()]
        self.assertEqual(nombres, ["Modelado", "UV y texturas", "Animación", "Render con Arnold"])

    def test_cambios_sin_guardar_sobreviven_a_reiniciar(self):
        b = self.nueva()
        radial = b.activo
        radial["botones"][0]["texto"] = "Clonar"
        b.modificar(radial)
        otra = self.nueva()
        self.assertTrue(otra.sin_guardar)
        self.assertEqual(otra.activo["botones"][0]["texto"], "Clonar")

    def test_preconfigurado_no_se_sobrescribe(self):
        b = self.nueva()
        radial = b.activo
        radial["botones"][0]["texto"] = "Clonar"
        b.modificar(radial)
        self.assertFalse(b.guardar_cambios())
        _, ruta = rd.preconfigurados()[0]
        self.assertEqual(rd.leer(ruta)["botones"][0]["texto"], "Duplicar")

    def test_guardar_como_y_guardar_cambios(self):
        b = self.nueva()
        radial = b.activo
        radial["botones"][0]["texto"] = "Clonar"
        b.modificar(radial)
        b.guardar_como("Clase de lunes")
        self.assertEqual(b.origen, MIO + "clase_de_lunes")
        self.assertFalse(b.sin_guardar)
        self.assertEqual(b.mios(), [(MIO + "clase_de_lunes", "Clase de lunes")])

        radial = b.activo
        radial["apariencia"]["radio"] = 120
        b.modificar(radial)
        self.assertTrue(b.guardar_cambios())
        guardado = rd.leer(os.path.join(self.mios, "clase_de_lunes.radial"))
        self.assertEqual(guardado["apariencia"]["radio"], 120)
        self.assertEqual(guardado["botones"][0]["texto"], "Clonar")
        self.assertEqual(guardado["nombre"], "Clase de lunes")

    def test_nombres_repetidos(self):
        b = self.nueva()
        b.guardar_como("Mío")
        b.guardar_como("Mío")
        self.assertEqual(sorted(n for _, n in b.mios()), ["Mío", "Mío 2"])
        self.assertEqual(len(os.listdir(self.mios)), 2)

    def test_restaurar(self):
        b = self.nueva()
        radial = b.activo
        radial["botones"][2] = rd.boton_vacio()
        b.modificar(radial)
        b.restaurar()
        self.assertFalse(b.sin_guardar)
        self.assertEqual(b.activo["botones"][2]["accion"], "FreezeTransformations")

    def test_usar_descarta_cambios(self):
        b = self.nueva()
        radial = b.activo
        radial["nombre"] = "cambiado"
        b.modificar(radial)
        b.usar(PRE + "3_animacion")
        self.assertEqual(b.activo["nombre"], "Animación")
        self.assertFalse(b.sin_guardar)
        with self.assertRaises(rd.RadialNoValido):
            b.usar(MIO + "no_existe")

    def test_exportar_e_importar(self):
        b = self.nueva()
        b.usar(PRE + "2_uv_texturas")
        ruta = b.exportar(os.path.join(self.tmp.name, "para alumnos"))
        self.assertTrue(ruta.endswith(".radial"))
        otra = Biblioteca(aj.Ajustes(os.path.join(self.tmp.name, "alumno")),
                          os.path.join(self.tmp.name, "alumno", "radiales"))
        importado = otra.importar(ruta)
        self.assertEqual(importado["nombre"], "UV y texturas")
        self.assertTrue(otra.origen.startswith(MIO))
        self.assertFalse(otra.es_preconfigurado)

    def test_importar_archivo_roto(self):
        roto = os.path.join(self.tmp.name, "roto.radial")
        with open(roto, "w") as f:
            f.write("no")
        with self.assertRaises(rd.RadialNoValido):
            self.nueva().importar(roto)

    def test_renombrar_activo(self):
        b = self.nueva()
        b.guardar_como("Viejo")
        nuevo = b.renombrar(b.origen, "Nuevo nombre")
        self.assertEqual(nuevo, MIO + "nuevo_nombre")
        self.assertEqual(b.origen, nuevo)
        self.assertEqual(b.activo["nombre"], "Nuevo nombre")
        self.assertEqual(os.listdir(self.mios), ["nuevo_nombre.radial"])
        with self.assertRaises(rd.RadialNoValido):
            b.renombrar(PRE + "1_modelado", "x")

    def test_renombrar_solo_mayusculas(self):
        b = self.nueva()
        b.guardar_como("clase")
        b.renombrar(b.origen, "Clase")
        self.assertEqual(b.mios(), [(MIO + "clase", "Clase")])

    def test_duplicar_y_borrar(self):
        b = self.nueva()
        copia = b.duplicar(PRE + "4_render_arnold")
        self.assertEqual(b.nombre_de(copia), "Render con Arnold")
        b.usar(copia)
        b.borrar(copia)
        self.assertEqual(b.mios(), [])
        self.assertEqual(b.origen, PRE + "1_modelado")
        with self.assertRaises(rd.RadialNoValido):
            b.borrar(PRE + "1_modelado")

    def test_activo_borrado_por_fuera(self):
        b = self.nueva()
        b.guardar_como("Temporal")
        os.remove(os.path.join(self.mios, "temporal.radial"))
        otra = self.nueva()
        self.assertEqual(otra.origen, PRE + "1_modelado")
        self.assertEqual(otra.activo["nombre"], "Modelado")


class PruebaNombres(unittest.TestCase):
    def test_nombre_de_archivo(self):
        self.assertEqual(rd.nombre_de_archivo("Clase de Lunes · Árboles!"), "clase_de_lunes_arboles")
        self.assertEqual(rd.nombre_de_archivo("   "), "radial")
        self.assertEqual(rd.nombre_de_archivo("ñandú/../x"), "nandu_x")


class PruebaPill(unittest.TestCase):
    def test_geometria_horizontal(self):
        ap = rd.normalizar_apariencia({"pill_boton": 32})
        ancho, alto, agarre, botones = rd.geometria_pill(ap)
        self.assertEqual(alto, 42)
        self.assertEqual(len(botones), 6)
        self.assertEqual(ancho, botones[-1][0] + 32 + rd.PILL_MARGEN)
        self.assertLess(agarre[0] + agarre[2], botones[0][0])

    def test_vertical_es_la_horizontal_girada(self):
        ap = rd.normalizar_apariencia({})
        ancho, alto, _, botones = rd.geometria_pill(ap)
        ancho_v, alto_v, _, botones_v = rd.geometria_pill(ap, vertical=True)
        self.assertEqual((ancho, alto), (alto_v, ancho_v))
        self.assertEqual([(b[1], b[0]) for b in botones], [(b[0], b[1]) for b in botones_v])

    def test_que_hay_en_pill(self):
        ap = rd.normalizar_apariencia({})
        for vertical in (False, True):
            _, _, agarre, botones = rd.geometria_pill(ap, vertical)
            x, y, w, h = botones[3]
            self.assertEqual(rd.que_hay_en_pill(x + w / 2, y + h / 2, ap, vertical), 3)
            self.assertEqual(rd.que_hay_en_pill(agarre[0] + 2, agarre[1] + 2, ap, vertical), "centro")
            self.assertIsNone(rd.que_hay_en_pill(-10, -10, ap, vertical))


class PruebaAjustesForma(unittest.TestCase):
    def test_forma(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = aj.Ajustes(tmp)
            self.assertEqual(a.forma, "radial")
            self.assertFalse(a.pill_vertical)
            a.forma = "pill"
            a.pill_vertical = True
            a.guardar()
            b = aj.Ajustes(tmp)
            self.assertEqual((b.forma, b.pill_vertical), ("pill", True))
            b.forma = "triángulo"
            self.assertEqual(b.forma, "radial")


if __name__ == "__main__":
    unittest.main()
