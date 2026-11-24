"""Pruebas sin Maya ni Qt de los iconos de las acciones."""

import json
import os
import re
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

from radial import iconos, iconos_acciones as ia  # noqa: E402

CARPETA = os.path.join(RAIZ, "scripts", "radial")


class PruebaIconosAcciones(unittest.TestCase):
    def test_trazos_validos(self):
        for nombre, trazo in iconos.TRAZOS.items():
            self.assertTrue(trazo.startswith("M"), nombre)
            self.assertIsNone(re.search(r"[^MmLlHhVvCcSsQqTtAaZz0-9.,\s-]", trazo), nombre)
            self.assertIn(b"<path", iconos.svg(nombre))

    def test_iconos_por_defecto_no_cambian(self):
        self.assertEqual(iconos.TRAZOS["duplicar"], "M8.5 8.5h11v11h-11z M5 15.5V4.5h11")

    def test_todo_lo_que_se_usa_existe(self):
        usados = set(ia.POR_COMANDO.values()) | {i for _, i in ia.REGLAS} | {i for _, i in ia.POR_CATEGORIA}
        self.assertFalse(usados - set(iconos.TRAZOS))

    def test_todos_los_comandos_del_buscador_tienen_icono(self):
        with open(os.path.join(CARPETA, "i18n", "sinonimos_es.json"), encoding="utf-8") as archivo:
            comandos = json.load(archivo)
        sin_icono = [c for c in comandos if not ia.icono_de_comando(c)]
        self.assertEqual(sin_icono, [])
        # Y casi todos con uno de la tabla, no por palabras sueltas
        self.assertGreater(sum(1 for c in comandos if c in ia.POR_COMANDO), len(comandos) * 0.95)

    def test_preconfigurados_coinciden(self):
        for nombre in os.listdir(os.path.join(CARPETA, "preconfigurados")):
            with open(os.path.join(CARPETA, "preconfigurados", nombre), encoding="utf-8") as archivo:
                datos = json.load(archivo)
            for boton in datos["botones"]:
                if boton["tipo"] == "comando":
                    automatico = ia.icono_de_comando(boton["accion"])
                    self.assertTrue(automatico, boton["accion"])

    def test_palabras(self):
        self.assertEqual(ia.palabras("PolyExtrudeFacet"), ["poly", "extrude", "facet"])
        self.assertEqual(ia.palabras("dR_quadDrawTool"), ["quad", "draw", "tool"])
        self.assertEqual(ia.palabras("CreateNURBSCircle"), ["create", "nurbs", "circle"])
        self.assertEqual(ia.palabras("UVUnfold"), ["uv", "unfold"])

    def test_reglas_y_categorias(self):
        self.assertEqual(ia.icono_de_comando("PolyExtrudeEdgeOptions"), "extruir")
        self.assertEqual(ia.icono_de_comando("CreatePolygonHelix"), "crear")
        self.assertEqual(ia.icono_de_comando("CreateSpotLightOptions"), "foco")
        self.assertEqual(ia.icono_de_comando("ZzRaro", "Menu items.Rendering"), "render")
        self.assertEqual(ia.icono_de_comando("ZzRaro", "Edit Mesh › Components"), "extruir")
        self.assertEqual(ia.icono_de_comando("ZzRaro"), "")

    def test_codigo(self):
        self.assertEqual(ia.icono_de_codigo("polyAutoProjection;"), "proyeccion_auto")
        self.assertEqual(ia.icono_de_codigo("import maya.cmds as cmds\ncmds.polyBevel3(offset=0.1)"), "biselar")
        self.assertEqual(ia.icono_de_codigo("mel.eval('CenterPivot')"), "pivote")
        self.assertEqual(ia.icono_de_codigo("print('hola')"), "")

    def test_de_boton(self):
        self.assertEqual(iconos.de_boton({"icono": "luz", "tipo": "comando", "accion": "PolyExtrude"}), "luz")
        self.assertEqual(iconos.de_boton({"icono": "", "tipo": "comando", "accion": "PolyExtrude"}), "extruir")
        self.assertEqual(iconos.de_boton({"icono": "", "tipo": "comando", "accion": "ZzRaro"}), "orden")
        self.assertEqual(iconos.de_boton({"icono": "", "tipo": "python", "accion": "print(1)"}), "")
        self.assertEqual(iconos.de_boton({"icono": "", "tipo": "carpeta", "accion": ""}), "carpeta")
        self.assertEqual(iconos.de_boton({"icono": "", "tipo": "vacio", "accion": ""}), "")

    def test_estante_con_imagen_de_maya(self):
        boton = {"icono": ":/polyBevel.png", "tipo": "mel", "accion": "polyBevel3 -offset 0.2;"}
        self.assertEqual(iconos.de_imagen_maya(boton), "biselar")


if __name__ == "__main__":
    unittest.main()
