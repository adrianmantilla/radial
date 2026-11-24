"""Pruebas sin Maya: doble Tab, radiales, ajustes, textos e instalador.

    python3 -m unittest discover tests
"""

import json
import os
import re
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
sys.path.insert(0, RAIZ)

from radial import ajustes as aj  # noqa: E402
from radial import detector_tab as dt  # noqa: E402
from radial import i18n  # noqa: E402
from radial import iconos  # noqa: E402
from radial import radiales as rd  # noqa: E402
import instalar  # noqa: E402

# Textos de los deslizadores de Ajustes (el módulo importa Qt, así que se copian aquí)
DESLIZADORES_TEXTOS = (("radio", "ajustes_radio", 1, "px"), ("punto", "ajustes_punto", 2, "px"),
                       ("abierto", "ajustes_abierto", 1, "px"), ("pill_boton", "ajustes_pill_boton", 1, "px"),
                       ("opacidad", "ajustes_opacidad", 100, "%"))


class PruebaDetector(unittest.TestCase):
    def test_dos_tab_rapidos(self):
        d = dt.DetectorDobleTab(250)
        self.assertFalse(d.pulsar(1000))
        self.assertTrue(d.pulsar(1200))

    def test_justo_en_el_limite(self):
        d = dt.DetectorDobleTab(250)
        d.pulsar(0)
        self.assertTrue(d.pulsar(250))

    def test_dos_tab_lentos(self):
        d = dt.DetectorDobleTab(250)
        d.pulsar(0)
        self.assertFalse(d.pulsar(251))
        # el lento cuenta como un primer Tab nuevo
        self.assertTrue(d.pulsar(400))

    def test_tercer_tab_empieza_de_cero(self):
        d = dt.DetectorDobleTab(250)
        d.pulsar(0)
        self.assertTrue(d.pulsar(100))
        self.assertFalse(d.pulsar(200))
        self.assertTrue(d.pulsar(300))

    def test_tab_que_no_cuenta_rompe_la_secuencia(self):
        d = dt.DetectorDobleTab(250)
        d.pulsar(0)
        self.assertFalse(d.pulsar(100, cuenta=False))
        self.assertFalse(d.pulsar(150))

    def test_otra_tecla_en_medio(self):
        d = dt.DetectorDobleTab(250)
        d.pulsar(0)
        d.olvidar()
        self.assertFalse(d.pulsar(100))

    def test_esperando(self):
        d = dt.DetectorDobleTab(200)
        self.assertFalse(d.esperando(0))
        d.pulsar(0)
        self.assertTrue(d.esperando(150))
        self.assertFalse(d.esperando(201))

    def test_reloj_hacia_atras_no_cuenta(self):
        d = dt.DetectorDobleTab(250)
        d.pulsar(1000)
        self.assertFalse(d.pulsar(900))

    def test_limites_de_ventana(self):
        self.assertEqual(dt.limitar_ventana(10), dt.VENTANA_MINIMA_MS)
        self.assertEqual(dt.limitar_ventana(9999), dt.VENTANA_MAXIMA_MS)
        self.assertEqual(dt.limitar_ventana("raro"), dt.VENTANA_POR_DEFECTO_MS)
        self.assertEqual(dt.limitar_ventana(None), dt.VENTANA_POR_DEFECTO_MS)


class PruebaRadiales(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_preconfigurados_validos(self):
        lista = rd.preconfigurados()
        self.assertTrue(lista)
        for _, ruta in lista:
            radial = rd.leer(ruta)
            self.assertEqual(len(radial["botones"]), rd.NUM_BOTONES)
            for boton in radial["botones"]:
                self.assertIn(boton["tipo"], rd.TIPOS)
                if boton["icono"] and not iconos.es_imagen(boton["icono"]):
                    self.assertIn(boton["icono"], iconos.TRAZOS)

    def test_por_defecto_es_modelado(self):
        radial = rd.por_defecto()
        self.assertEqual(radial["nombre"], "Modelado")
        self.assertEqual(radial["botones"][0]["accion"], "DuplicateSpecialOptions")

    def test_completa_y_recorta_botones(self):
        pocos = rd.normalizar({"botones": [{"tipo": "mel", "accion": "polyCube"}]})
        self.assertEqual(len(pocos["botones"]), 6)
        self.assertEqual(pocos["botones"][5]["tipo"], "vacio")
        muchos = rd.normalizar({"botones": [{"tipo": "mel", "accion": "ls"}] * 9})
        self.assertEqual(len(muchos["botones"]), 6)

    def test_corrige_valores_raros(self):
        radial = rd.normalizar({"nombre": "  ", "botones": [
            {"tipo": "nuclear", "accion": "x"}, {"tipo": "python", "accion": "   "}, "texto suelto"],
            "apariencia": {"radio": 9999, "punto": "a", "opacidad": 0}})
        self.assertEqual(radial["nombre"], "Radial")
        self.assertEqual([b["tipo"] for b in radial["botones"][:3]], ["vacio"] * 3)
        self.assertEqual(radial["apariencia"]["radio"], 140)
        self.assertEqual(radial["apariencia"]["punto"], 5.0)
        self.assertEqual(radial["apariencia"]["opacidad"], 0.4)

    def test_rechaza_lo_que_no_es_radial(self):
        for datos in (None, [], {"nombre": "x"}, {"botones": "no"}, {"formato": 99, "botones": []}):
            with self.assertRaises(rd.RadialNoValido):
                rd.normalizar(datos)
        roto = os.path.join(self.tmp.name, "roto.radial")
        with open(roto, "w") as f:
            f.write("{no es json")
        with self.assertRaises(rd.RadialNoValido):
            rd.leer(roto)

    def test_escribir_y_leer_con_acentos(self):
        ruta = os.path.join(self.tmp.name, "Mis radiales", "Clase de lunes.radial")
        original = rd.normalizar({"nombre": "Clase de lunes · Árboles", "botones": [
            {"texto": "Añadir", "tipo": "python", "accion": "print('ñ')"}]})
        rd.escribir(original, ruta)
        self.assertEqual(rd.leer(ruta), original)

    def test_posiciones_empiezan_arriba_y_siguen_el_reloj(self):
        p = rd.posiciones(100)
        self.assertAlmostEqual(p[0][0], 0, places=6)
        self.assertAlmostEqual(p[0][1], -100, places=6)
        self.assertGreater(p[1][0], 0)        # el 2 está a la derecha
        self.assertAlmostEqual(p[3][1], 100)  # el 4 está abajo
        self.assertLess(p[5][0], 0)           # el 6 a la izquierda

    def test_que_hay_en(self):
        ap = rd.normalizar_apariencia({})
        x, y = rd.posiciones(ap["radio"])[2]
        self.assertEqual(rd.que_hay_en(x + 5, y - 5, ap), 2)
        self.assertEqual(rd.que_hay_en(0, 0, ap), "centro")
        self.assertIsNone(rd.que_hay_en(0, 40, ap))
        self.assertIsNone(rd.que_hay_en(500, 0, ap))

    def test_la_ventana_contiene_los_botones_abiertos(self):
        for radio in (50, 84, 140):
            ap = rd.normalizar_apariencia({"radio": radio, "abierto": 30})
            self.assertGreaterEqual(rd.lado_ventana(ap) / 2.0, radio + 30 + 3)


class PruebaAjustes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.prefs = os.path.join(self.tmp.name, "prefs", "radial")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valores_por_defecto(self):
        a = aj.Ajustes(self.prefs)
        self.assertEqual(a.ventana_ms, 250)
        self.assertIsNone(a.posicion)
        self.assertIsNone(a.radial_activo)

    def test_se_recuerdan(self):
        a = aj.Ajustes(self.prefs)
        a.ventana_ms = 1000
        a.posicion = (640.7, -20)
        a.radial_activo = "pre:1_modelado"
        a.guardar()
        b = aj.Ajustes(self.prefs)
        self.assertEqual(b.ventana_ms, 400)
        self.assertEqual(b.posicion, (640, -20))
        self.assertEqual(b.radial_activo, "pre:1_modelado")
        b.posicion = None
        b.guardar()
        self.assertIsNone(aj.Ajustes(self.prefs).posicion)

    def test_archivo_roto(self):
        os.makedirs(self.prefs)
        with open(os.path.join(self.prefs, "ajustes.json"), "w") as f:
            f.write('{"posicion": [1, "dos"], "ventana_ms": "rápido"')
        a = aj.Ajustes(self.prefs)
        self.assertIsNone(a.posicion)
        self.assertEqual(a.ventana_ms, 250)

    def test_posicion_mal_formada(self):
        a = aj.Ajustes(self.prefs)
        for valor in ([1, "dos"], [1], "10,20", [True, 3]):
            a.datos["posicion"] = valor
            self.assertIsNone(a.posicion)


class PruebaTextos(unittest.TestCase):
    def test_todas_las_claves_usadas_existen(self):
        usadas = set()
        for carpeta, _, archivos in os.walk(RAIZ):
            for nombre in archivos:
                if nombre.endswith(".py") and "tests" not in carpeta:
                    with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
                        usadas |= set(re.findall(r'\bt\("([a-z0-9_]+)"\s*[,)]', f.read()))
                        f.seek(0)
                        usadas |= set(re.findall(r'_proximamente\("([a-z0-9_]+)"', f.read()))
        # Claves que se montan con una variable
        usadas |= {"tipo_" + tipo for tipo in ("comando", "estante", "python", "mel", "vacio")}
        usadas |= {"forma_" + forma for forma in aj.FORMAS}
        usadas |= {"forma_pill_horizontal", "forma_pill_vertical", "comando_anotacion",
                   "comando_configurar_anotacion"}
        usadas |= {texto for _, texto, _, _ in DESLIZADORES_TEXTOS}
        faltan = usadas - i18n.claves()
        self.assertFalse(faltan, "faltan textos: {}".format(sorted(faltan)))

    def test_es_json_valido(self):
        with open(os.path.join(RAIZ, "scripts", "radial", "i18n", "es.json"), encoding="utf-8") as f:
            self.assertTrue(json.load(f))


class PruebaInstalador(unittest.TestCase):
    def test_modulo(self):
        texto = instalar.contenido_mod("C:\\Users\\Ana\\Plugins\\Radial", "1.0.0")
        self.assertTrue(texto.startswith("+ Radial 1.0.0 C:/Users/Ana/Plugins/Radial\n"))
        self.assertIn("scripts: scripts", texto)
        self.assertIn("plug-ins: plug-ins", texto)

    def test_version(self):
        import radial
        self.assertEqual(instalar._version(RAIZ), radial.__version__)


if __name__ == "__main__":
    unittest.main()
