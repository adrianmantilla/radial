"""Pruebas de la búsqueda de acciones (sin Maya ni Qt)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from radial import busqueda as bq  # noqa: E402

ACCIONES = [bq.accion_de_comando(*c) for c in (
    ("CenterPivot", "Menu items.Modify.Pivot", "Center the pivot of the selected objects"),
    ("PolyExtrude", "Menu items.Edit Mesh", "Extrude faces, edges or vertices"),
    ("ExtractFace", "Menu items.Edit Mesh", "Extract the selected faces"),
    ("UVEditor", "Menu items.Windows", "Open the UV Editor"),
    ("FreezeTransformations", "Menu items.Modify", "Freeze transformations"),
)] + [bq.accion_de_estante("Poly", {"texto": "Cubo", "icono": ":/polyCube.png", "tipo": "mel",
                                    "accion": "polyCube;", "descripcion": "Crea un cubo"})]


class PruebaBusqueda(unittest.TestCase):
    def test_texto_de_comando(self):
        self.assertEqual(bq.texto_de_comando("CenterPivot"), "Center Pivot")
        self.assertEqual(bq.texto_de_comando("UVEditor"), "UV Editor")
        self.assertEqual(bq.categoria_legible("Menu items.Modify.Pivot"), "Modify › Pivot")

    def test_accion_de_comando(self):
        accion = ACCIONES[0]
        self.assertEqual(accion["boton"], {"texto": "Center Pivot", "detalle": "", "icono": "",
                                           "tipo": "comando", "accion": "CenterPivot"})

    def test_buscar_por_principio(self):
        self.assertEqual(bq.buscar(ACCIONES, "extr")[0]["nombre"], "ExtractFace")
        nombres = [a["nombre"] for a in bq.buscar(ACCIONES, "extr")]
        self.assertEqual(set(nombres), {"PolyExtrude", "ExtractFace"})

    def test_palabras_en_cualquier_orden_y_sin_acentos(self):
        self.assertEqual(bq.buscar(ACCIONES, "editor uv")[0]["nombre"], "UVEditor")
        self.assertEqual(bq.buscar(ACCIONES, "CÚBO")[0]["texto"], "Cubo")
        self.assertEqual(bq.buscar(ACCIONES, "pivot center")[0]["nombre"], "CenterPivot")

    def test_busca_en_descripcion_y_categoria(self):
        self.assertEqual(bq.buscar(ACCIONES, "selected faces")[0]["boton"]["accion"], "ExtractFace")
        self.assertTrue(bq.buscar(ACCIONES, "modify"))

    def test_sin_resultados_y_vacio(self):
        self.assertEqual(bq.buscar(ACCIONES, "zzz"), [])
        self.assertEqual(bq.buscar(ACCIONES, "   "), [])

    def test_limite(self):
        self.assertEqual(len(bq.buscar(ACCIONES * 3, "e", limite=4)), 4)

    def test_no_repite(self):
        self.assertEqual(len(bq.buscar(ACCIONES + ACCIONES, "center")), 1)

    def test_recientes_suben(self):
        extrude = ACCIONES[1]
        self.assertEqual(bq.buscar(ACCIONES, "extr", [bq.clave(extrude)])[0]["nombre"], "PolyExtrude")

    def test_anadir_reciente(self):
        recientes = []
        for accion in (ACCIONES[0], ACCIONES[1], ACCIONES[0]):
            recientes = bq.anadir_reciente(recientes, accion)
        self.assertEqual([a["nombre"] for a in recientes], ["CenterPivot", "PolyExtrude"])
        for accion in ACCIONES:
            recientes = bq.anadir_reciente(recientes, accion, limite=3)
        self.assertEqual(len(recientes), 3)

    def test_partes_resaltadas(self):
        self.assertEqual(bq.partes_resaltadas("Center Pivot", "piv"),
                         [("Center ", False), ("Piv", True), ("ot", False)])
        self.assertEqual(bq.partes_resaltadas("Cubo", ""), [("Cubo", False)])


if __name__ == "__main__":
    unittest.main()
