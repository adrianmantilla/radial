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


class PruebaIdiomas(unittest.TestCase):
    ACCIONES = [
        bq.accion_de_comando("PolyExtrude", "Menu items.Edit Mesh", "Extrude faces", "Extruir", "Saca caras."),
        bq.accion_de_comando("SelectAll", "Menu items.Select", "Select all objects"),
        bq.accion_de_comando("BevelPolygon", "Menu items.Edit Mesh", "Bevel edges", "Biselar", ""),
        bq.accion_de_comando("UVEditor", "Menu items.UV", "Open the UV editor"),
    ]

    def nombres(self, consulta):
        return [a["nombre"] for a in bq.buscar(self.ACCIONES, consulta)]

    def test_ingles_y_espanol(self):
        self.assertEqual(self.nombres("extrude")[0], "PolyExtrude")
        self.assertEqual(self.nombres("extruir")[0], "PolyExtrude")
        self.assertEqual(self.nombres("bevel")[0], "BevelPolygon")
        self.assertEqual(self.nombres("biselar")[0], "BevelPolygon")

    def test_glosario_para_lo_que_no_esta_traducido(self):
        self.assertEqual(self.nombres("seleccionar todo"), ["SelectAll"])
        self.assertEqual(self.nombres("editor uv")[0], "UVEditor")
        self.assertIn("SelectAll", self.nombres("selecc"))  # a medio escribir

    def test_se_busca_en_la_ayuda_inglesa_aunque_haya_traduccion(self):
        self.assertIn("PolyExtrude", self.nombres("faces"))
        self.assertIn("PolyExtrude", self.nombres("caras"))

    def test_alternativas(self):
        self.assertEqual(bq.alternativas("extruir", {"extruir": "extrude"}), ["extruir", "extrude"])
        self.assertEqual(bq.alternativas("xyz", {"extruir": "extrude"}), ["xyz"])

    def test_candidatos_icono(self):
        self.assertEqual(bq.candidatos_icono("CenterPivot")[0], "centerPivot.png")
        self.assertIn("polyExtrudeFacet.png", bq.candidatos_icono("PolyExtrude"))
        self.assertEqual(bq.candidatos_icono("PolyBevelOptions")[0], "polyBevel.png")
        self.assertEqual(bq.candidatos_icono(""), [])


class PruebaMenusScriptsFavoritos(unittest.TestCase):
    def _acciones(self):
        return [dict(a, boton=dict(a["boton"])) for a in ACCIONES]

    def test_menus_de_maya(self):
        acciones = bq.unir_menus(self._acciones(), [
            (["Modify", "Pivot"], "Centrar pivote", {"tipo": "comando", "accion": "CenterPivot"}),
            (["Mesh"], "Smooth Proxy", {"tipo": "mel", "accion": "performSmoothProxy 0;"}),
            (["Mesh"], "", {"tipo": "mel", "accion": "nada;"}),
            (["Mesh"], "Vacío", {"tipo": "mel", "accion": "  "}),
        ])
        self.assertEqual(len(acciones), len(ACCIONES) + 1)
        centro = [a for a in acciones if a["nombre"] == "CenterPivot"][0]
        self.assertEqual(centro["menu"], "Modify › Pivot › Centrar pivote")
        self.assertEqual(centro["etiqueta"], "Centrar pivote")
        # Se encuentra por la etiqueta del menú (Maya en español) y por el menú
        self.assertEqual(bq.buscar(acciones, "centrar pivote", glosario={})[0]["nombre"], "CenterPivot")
        nuevo = acciones[-1]
        self.assertEqual(nuevo["texto"], "Smooth Proxy")
        self.assertEqual(nuevo["categoria"], "Mesh")
        self.assertEqual(nuevo["boton"]["accion"], "performSmoothProxy 0;")
        self.assertEqual(bq.buscar(acciones, "smooth proxy", glosario={})[0]["texto"], "Smooth Proxy")

    def test_scripts_propios(self):
        self.assertTrue(bq.es_script("limpiar_escena.py"))
        self.assertTrue(bq.es_script("Renombrar.MEL"))
        for archivo in ("userSetup.py", "userSetup.mel", "__init__.py", "_privado.py", "notas.txt"):
            self.assertFalse(bq.es_script(archivo), archivo)
        py = bq.accion_de_script("/u/scripts/limpiarEscena.py", "Mis scripts")
        self.assertEqual(py["texto"], "limpiar Escena")
        self.assertEqual(py["boton"]["tipo"], "python")
        self.assertIn("runpy.run_path('/u/scripts/limpiarEscena.py'", py["boton"]["accion"])
        compile(py["boton"]["accion"], "<prueba>", "exec")
        mel = bq.accion_de_script("C:\\scripts\\renombrar.mel", "Mis scripts")
        self.assertEqual(mel["boton"], dict(mel["boton"], tipo="mel", accion='source "C:/scripts/renombrar.mel";'))
        self.assertEqual(bq.buscar([py, mel], "renombrar", glosario={})[0]["nombre"], "renombrar.mel")

    def test_favoritas(self):
        acciones = self._acciones()
        favoritos = bq.alternar_favorito([], acciones[1])
        self.assertTrue(bq.es_favorita(favoritos, acciones[1]))
        self.assertFalse(bq.es_favorita(favoritos, acciones[2]))
        # Suben en los resultados
        normal = bq.buscar(acciones, "extr", glosario={})
        con = bq.buscar(acciones, "extr", glosario={}, favoritos=[bq.clave(a) for a in favoritos])
        self.assertEqual(normal[0]["nombre"], "ExtractFace")
        self.assertEqual(con[0]["nombre"], "PolyExtrude")
        # Otra vez: se quita
        self.assertEqual(bq.alternar_favorito(favoritos, acciones[1]), [])


if __name__ == "__main__":
    unittest.main()
