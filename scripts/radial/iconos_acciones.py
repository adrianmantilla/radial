"""Iconos de línea para las acciones de Maya que se pueden poner en un botón.

Mismo estilo que los iconos por defecto del plugin (``iconos.py``): 24 x 24,
trazo fino de 1.5 sin relleno, puntas y esquinas redondeadas.

- ``TRAZOS_ACCIONES``: los glifos nuevos (se suman a ``iconos.TRAZOS``).
- ``icono_de_comando(nombre, categoria)``: el icono de un comando de Maya
  (``"PolyExtrude"`` -> ``"extruir"``). Primero busca el comando en una tabla,
  luego por las palabras de su nombre y luego por la categoría del menú de
  Maya. Devuelve "" si no sabe cuál poner (se dibuja la inicial).
- ``icono_de_boton(boton)``: el icono que se ve en un botón sin icono propio,
  también para botones de Python o MEL que llaman a un comando conocido.

No necesita Maya ni Qt.
"""

import re


# --- Ayudas para escribir trazos ------------------------------------------------

def _n(v):
    texto = ("%.2f" % v).rstrip("0").rstrip(".")
    return "0" if texto in ("-0", "") else texto


def _c(cx, cy, r):
    """Círculo."""
    return "M{} {}a{} {} 0 1 0 {} 0a{} {} 0 1 0 {} 0".format(
        _n(cx - r), _n(cy), _n(r), _n(r), _n(2 * r), _n(r), _n(r), _n(-2 * r))


def _e(cx, cy, rx, ry):
    """Elipse."""
    return "M{} {}a{} {} 0 1 0 {} 0a{} {} 0 1 0 {} 0".format(
        _n(cx - rx), _n(cy), _n(rx), _n(ry), _n(2 * rx), _n(rx), _n(ry), _n(-2 * rx))


def _r(x, y, w, h):
    """Rectángulo."""
    return "M{} {}h{}v{}h{}z".format(_n(x), _n(y), _n(w), _n(h), _n(-w))


def _p(*puntos, **kw):
    """Polilínea (``cerrada=True`` para cerrarla)."""
    texto = "M" + " L".join("{} {}".format(_n(x), _n(y)) for x, y in puntos)
    return texto + ("z" if kw.get("cerrada") else "")


def _punto(x, y):
    """Un punto (círculo muy pequeño)."""
    return _c(x, y, 0.9)


def _j(*trazos):
    return " ".join(trazos)


# Piezas que se repiten
_ROMBO = _p((12, 4), (20, 12), (12, 20), (4, 12), cerrada=True)
_ROMBO_P = _p((7, 3), (11, 7), (7, 11), (3, 7), cerrada=True)
_CUBO = "M12 3l8 4.5v9L12 21l-8-4.5v-9z M4 7.5l8 4.5 8-4.5 M12 12v9"
_CUBO_P = "M15 9l5 2.8v5.6L15 20.2l-5-2.8v-5.6z M10 11.8l5 2.8 5-2.8 M15 14.6v5.6"
_ESQUINAS = "M4 8V4h4 M16 4h4v4 M20 16v4h-4 M8 20H4v-4"
_VENTANA = "M3 5h18v14H3z M3 9h18"
_CILINDRO = _j(_e(12, 6, 7, 2.5), "M5 6v12 M19 6v12 M5 18a7 2.5 0 0 0 14 0")
_FLECHA_ARRIBA = "M12 15V5 M8.5 8.5L12 5l3.5 3.5"
_CURSOR = "M6 3.5l11 6.2-4.6 1.5-1.8 4.6z"


TRAZOS_ACCIONES = {
    # --- Transformar y pivote ---------------------------------------------------
    "restablecer": _j("M5 12a7 7 0 1 0 2.1-5", "M5 4v4h4", _c(12, 12, 1.6)),
    "igualar": _j(_r(3, 5, 7, 7), "M14 12h7v7h-7z", "M10 8.5h3.5v3.5", "M12 10.5l1.5 1.5 1.5-1.5"),
    "iman": "M6 4v8a6 6 0 0 0 12 0V4 M6 4h3v8a3 3 0 0 0 6 0V4h3 M6 8h3 M15 8h3",
    "ejes": "M5 19V5 M5 19h14 M5 19l9-9 M3 7l2-2 2 2 M17 17l2 2-2 2 M10.5 10h3.5v3.5",
    "localizador": "M12 3v18 M3 12h18 M6.5 17.5l11-11",
    "rejilla": "M4 4h16v16H4z M4 9.3h16 M4 14.7h16 M9.3 4v16 M14.7 4v16",
    # --- Jerarquía y selección -----------------------------------------------------
    "grupo": _j(_ESQUINAS, _r(8, 8, 3.5, 3.5), _r(12.5, 12.5, 3.5, 3.5)),
    "desagrupar": _j(_r(4, 4, 6, 6), _r(14, 14, 6, 6), "M13 7h4v4 M11 17H7v-4"),
    "grupo_vacio": _j(_ESQUINAS, _punto(12, 12)),
    "emparentar": _j(_c(12, 5.5, 2.5), _c(6, 18.5, 2.5), _c(18, 18.5, 2.5), "M12 8v3 M6 16v-2.5h12V16 M12 11v2.5"),
    "desemparentar": _j(_c(12, 5.5, 2.5), _c(6, 18.5, 2.5), _c(18, 18.5, 2.5), "M12 8v2 M6 16v-2.5h3.5 M14.5 13.5H18V16 M10 11l4 4"),
    "jerarquia": _j(_r(3, 3, 6, 5), _r(11, 10.5, 6, 4), _r(11, 17, 6, 4), "M6 8v11h5 M6 12.5h5"),
    "seleccionar": _CURSOR,
    "seleccionar_todo": "M4 4h2.5 M9.5 4h5 M17.5 4H20v2.5 M20 9.5v5 M20 17.5V20h-2.5 M14.5 20h-5 M6.5 20H4v-2.5 M4 14.5v-5 M4 6.5V4 M9 9h6v6H9z",
    "invertir_seleccion": _j(_c(12, 12, 8), "M12 4v16", "M12 7l4-2.5 M12 11l7.2-4 M12 15l7.8-4.3 M12 19l6.6-3.7"),
    "ocultar": "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z M9 12a3 3 0 0 0 3 3 M4 20L20 4",
    "mostrar_todo": _j("M2 13s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 13 2 13z", _c(12, 13, 2.6), "M12 3v1.5 M5 4.5l1 1.2 M19 4.5l-1 1.2"),
    "mostrar_ultimo": _j("M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z", "M10 10.5a2.6 2.6 0 1 1 .2 3", "M9 9v2h2"),
    "ampliar_seleccion": _j(_r(9, 9, 6, 6), "M3 3l4 4 M3 7V3h4 M21 3l-4 4 M21 7V3h-4 M3 21l4-4 M3 17v4h4 M21 21l-4-4 M21 17v4h-4"),
    "reducir_seleccion": _j(_r(9, 9, 6, 6), "M3 3l4 4 M7 3v4H3 M21 3l-4 4 M17 3v4h4 M3 21l4-4 M7 21v-4H3 M21 21l-4-4 M17 21v-4h4"),
    "bucle": _j(_e(12, 12, 8, 3), "M4 5.5v13 M20 5.5v13"),
    "anillo": _j("M4 5.5v13 M20 5.5v13 M4 5.5h16 M4 18.5h16", "M8 5.5v13 M12 5.5v13 M16 5.5v13"),
    "a_caras": _j(_r(4, 4, 16, 16), _r(8, 8, 8, 8), "M8 12h8 M12 8v8"),
    "a_aristas": _j("M4 4h16v16H4z", _c(12, 4, 1.5), _c(20, 12, 1.5), _c(12, 20, 1.5), _c(4, 12, 1.5)),
    "a_vertices": _j(_p((7, 7), (17, 7), (17, 17), (7, 17), cerrada=True), _c(7, 7, 2), _c(17, 7, 2), _c(17, 17, 2), _c(7, 17, 2)),
    "a_uv": _j(_r(4, 4, 16, 16), "M9 9v4.5a3 3 0 0 0 6 0V9"),
    "a_isla": "M5 9c0-4 4-5 7-4s6-1 7 3-2 5-1 8-3 4-7 3-7 0-6-4 1-6 0-6z M9.5 10.5h5v4h-5z",
    "objeto_componente": _j(_CUBO, _punto(12, 3), _punto(20, 7.5), _punto(4, 7.5), _punto(20, 16.5), _punto(4, 16.5), _punto(12, 21)),
    # --- Crear --------------------------------------------------------------------
    "esfera": _j(_c(12, 12, 8.5), _e(12, 12, 8.5, 3), _e(12, 12, 3.5, 8.5)),
    "cilindro": _CILINDRO,
    "plano_malla": "M2.5 15l9.5-5.5 9.5 5.5-9.5 5.5z M7.25 12.25l9.5 5.5 M7.25 17.75l9.5-5.5",
    "toroide": _j(_e(12, 12, 9, 5.5), "M7.5 11c2.5 2.8 6.5 2.8 9 0 M8.7 12.3c2-1.6 4.6-1.6 6.6 0"),
    "cono": _j("M12 3.5L4.5 17.5 M12 3.5l7.5 14", _e(12, 17.5, 7.5, 2.5)),
    "tubo": _j(_e(12, 6, 7, 2.5), _e(12, 6, 3.5, 1.2), "M5 6v12 M19 6v12 M5 18a7 2.5 0 0 0 14 0"),
    "disco": _j(_e(12, 12, 9, 4), _e(12, 12, 3, 1.3), "M3 12v2 M21 12v2 M3 14a9 4 0 0 0 18 0"),
    "circulo_nurbs": _j(_c(12, 12, 7.5), _r(10.5, 3, 3, 3), _r(18, 10.5, 3, 3), _r(10.5, 18, 3, 3), _r(3, 10.5, 3, 3)),
    "cuadrado_nurbs": _j("M5 5h14v14H5z", _r(3.5, 3.5, 3, 3), _r(17.5, 3.5, 3, 3), _r(17.5, 17.5, 3, 3), _r(3.5, 17.5, 3, 3)),
    "crear": _j(_c(12, 12, 8.5), "M12 8v8 M8 12h8"),
    "texto_3d": "M5 5h14 M12 5v14 M9 19h6",
    "curva": "M4 19C4 9 9 5 13 9s7 1 7-4 M4 19h0 M20 5h0",
    "curva_ep": _j("M4 19c3-9 6-12 9-9s5 2 7-5", _c(4, 19, 1.4), _c(13, 10, 1.4), _c(20, 5, 1.4)),
    "lapiz_curva": "M4 20c4-1 5-5 8-6 M13 13l7-7-2-2-7 7z",
    "superficie": "M3 16c3-3 6-3 9-1s6 2 9-1 M3 16V8c3-3 6-3 9-1s6 2 9-1v8 M8 6v8.5 M14 7.6v8.5",
    "anclaje": _j(_c(12, 5.5, 2.2), "M12 7.7V20 M7 11h10 M5 15a7 7 0 0 0 14 0 M5 15l-1.5 1.5 M19 15l1.5 1.5"),
    # --- Modelado de polígonos ---------------------------------------------------
    "extruir": "M4 19l4-3h12l-4 3z M4 12l4-3h12l-4 3z M4 12v7 M16 12v7 M20 9v7 M12 7V2.5 M10 4.5l2-2 2 2",
    "biselar": _j("M4 20V10l6-6h10v16z", "M7 20v-9l4-4h9"),
    "puente": "M4 5v14 M20 5v14 M4 9h16 M4 15h16 M9 9v6 M15 9v6",
    "unir": _j(_c(5, 5.5, 2), _c(19, 5.5, 2), _c(12, 18, 2.8), "M6.3 7.5l3.9 7 M17.7 7.5l-3.9 7 M7.5 13.5l2.7 1 .6-2.9 M16.5 13.5l-2.7 1-.6-2.9"),
    "unir_centro": _j(_r(3, 3, 18, 18), _punto(12, 12), "M6 6l4 4 M18 6l-4 4 M6 18l4-4 M18 18l-4-4"),
    "colapsar": _j(_r(3, 3, 18, 18), _punto(12, 12), "M6 6l3.5 3.5 M9.5 6.5v3h-3 M18 6l-3.5 3.5 M14.5 6.5v3h3 M6 18l3.5-3.5 M9.5 17.5v-3h-3 M18 18l-3.5-3.5 M14.5 17.5v-3h3"),
    "extraer": _j("M3 10h11v11H3z", "M10 3h11v11", "M10 3v4 M21 14h-4 M14 10l4-4 M16 6h2v2"),
    "separar_componentes": _j("M3 4h8v8H3z M13 12h8v8h-8z", "M14 4h7v5 M3 15v5h7"),
    "anadir_poligono": _j(_p((4, 18), (7, 5), (16, 4), (13, 14), cerrada=True), "M18 14v6 M15 17h6"),
    "rellenar": "M4 9l4-5h8l4 5-2 9H6z M9 9h6 M8 12.5h8 M9 16h6",
    "booleana_union": "M12 6.8A6 6 0 1 0 12 17.2A6 6 0 1 0 12 6.8z",
    "booleana_diferencia": "M12 6.8A6 6 0 1 0 12 17.2A6 6 0 0 1 12 6.8z M15 6.8a6 6 0 0 1 0 10.4 M17.5 8.4a6 6 0 0 1 0 7.2",
    "booleana_interseccion": "M12 6.8A6 6 0 0 1 12 17.2A6 6 0 0 1 12 6.8z M9 6a6 6 0 0 0-4.5 3.4 M9 18a6 6 0 0 1-4.5-3.4 M15 6a6 6 0 0 1 4.5 3.4 M15 18a6 6 0 0 0 4.5-3.4",
    "combinar": _j("M3 6h8v8H3z M13 10h8v8h-8z", "M11 10h2 M11 14h2"),
    "separar": _j("M3 7h6v10H3z M15 7h6v10h-6z", "M11 12h2 M11.5 10.5L10 12l1.5 1.5 M12.5 10.5L14 12l-1.5 1.5"),
    "suavizar": "M5 12c0-5 2-7 7-7s7 2 7 7-2 7-7 7-7-2-7-7z M5.5 12c4 2 9 2 13 0 M12 5.5c-2 4-2 9 0 13",
    "reducir": _j(_p((4, 18), (12, 5), (20, 18), cerrada=True), "M8 18l4-6.5 4 6.5 M15 3h6"),
    "triangular": "M4 4h16v16H4z M4 20L20 4 M4 12l8-8 M12 20l8-8",
    "cuadrangular": "M4 4h16v16H4z M4 12h16 M12 4v16",
    "simetria_malla": "M12 3v2 M12 8v2 M12 13v2 M12 18v3 M9.5 6L3 18h6.5z M14.5 6L21 18h-6.5z",
    "limpiar": "M14 3l-3 7 M7 10h8l3 11H4z M8 15l-1 6 M11 15v6 M14 15l1 6",
    "insertar_bucle": _j(_r(4, 5, 16, 14), "M12 5v14", "M10 2.5h4 M10 21.5h4"),
    "corte_multiple": "M3 21l8-8 M11 13l9-9 1.5 1.5-8.5 9.5z M5.5 8.5h2 M9.5 8.5h2 M15.5 16.5h2 M19.5 16.5h1",
    "conectar": _j(_r(4, 4, 16, 16), _c(4, 9, 1.4), _c(20, 15, 1.4), "M5.4 9.6l13.2 5.4"),
    "dibujo_quads": _j("M3 12h9v9H3z M3 16.5h9 M7.5 12v9", "M13 11l6-6 2 2-6 6-3 1z"),
    "soldar": _j(_c(5, 18, 1.6), _c(18, 6, 3), "M6.2 16.8l9.6-8.6 M11.5 8.5h4.3v4.3"),
    "desplazar_bucle": _j(_r(3, 4, 18, 16), "M9 4v16 M15 4v16", "M7 12H4 M17 12h3"),
    "deslizar": "M4 20L20 4 M9 4h-5v5 M15 20h5v-5 M4 4l5 5 M20 20l-5-5",
    "borrar_arista": _j("M4 4h16v16H4z", "M9 9l6 6 M15 9l-6 6"),
    "borrar_vertice": _j("M4 20V9 M4 20h11", _c(17.5, 6.5, 3), "M15.4 4.4l4.2 4.2 M19.6 4.4l-4.2 4.2"),
    "circularizar": _j(_c(12, 12, 7.5), _punto(12, 4.5), _punto(19.5, 12), _punto(12, 19.5), _punto(4.5, 12), _punto(17.3, 6.7), _punto(6.7, 6.7), _punto(17.3, 17.3), _punto(6.7, 17.3)),
    "achaflanar": _j("M4 20V4h9 M20 11v9H4 M13 4l7 7", _punto(13, 4), _punto(20, 11)),
    "pinchar": _j(_r(4, 4, 16, 16), "M4 4l16 16 M20 4L4 20", _c(12, 12, 1.5)),
    "cuna": "M4 20h16 M4 20L18 9 M4 20L11 5 M15 20a11 11 0 0 0-1.5-8",
    "subdividir": "M4 4h16v16H4z M4 12h16 M12 4v16 M4 8h16 M4 16h16 M8 4v16 M16 4v16",
    "promediar": "M3 9c3-5 6 5 9 0s6 5 9 0 M3 17h18 M12 12v2.5 M10.5 13l1.5 1.5 1.5-1.5",
    "invertir_normales": "M3 13c4-3 14-3 18 0 M8 10.8V5 M6 7l2-2 2 2 M16 10.8v8 M14 17l2 2 2-2",
    "unificar_normales": "M3 16c4-3 14-3 18 0 M7 13.6V6 M5 8l2-2 2 2 M12 12.7V4 M10 6l2-2 2 2 M17 13.6V6 M15 8l2-2 2 2",
    "normales": "M3 18c4-4 14-4 18 0 M12 15V5 M10 7l2-2 2 2 M6 16.2l-2.5-5 M3 13.7l.5-2.5 2.3 1.2 M18 16.2l2.5-5 M21 13.7l-.5-2.5-2.3 1.2",
    "aristas_suaves": "M4 20V12a8 8 0 0 1 8-8h8",
    "aristas_duras": "M4 20V4h16 M8 20V8h12",
    "suavizar_endurecer": "M4 20V4h8 M12 20v-4a8 8 0 0 1 8-8",
    "esculpir": "M3 18c3-4 6-6 9-6s6 2 9 6 M12 12V9 M9.5 3.5h5l-1 5.5h-3z",
    "agarrar": "M3 19c4 0 6-6 9-6s5 6 9 6 M12 10V3 M9.5 5.5L12 3l2.5 2.5",
    "mod_suave": _j(_e(12, 15, 9, 3.5), _e(12, 15, 4.5, 1.7), "M12 15V4 M9.5 6.5L12 4l2.5 2.5"),
    "lattice": "M5 5h14v14H5z M5 9.7h14 M5 14.3h14 M9.7 5v14 M14.3 5v14",
    "doblar": "M5 20c0-8 6-14 14-14 M9 20c0-5.5 4.5-10 10-10 M5 20h4 M19 6v4",
    "torcer": "M6 4c6 3 6 5 0 8s6 5 0 8 M18 4c-6 3-6 5 0 8s-6 5 0 8",
    "deformador": "M4 18C9 18 8 6 12 6s3 12 8 12 M4 18v2 M20 18v2",
    # --- UV ----------------------------------------------------------------------
    "proyeccion_auto": _j(_CUBO_P, "M3 4v4 M3 4h4 M3 4l5 5", "M21 4v4 M21 4h-4"),
    "proyeccion_plana": _j("M3 14l9-4 9 4-9 4z", "M12 3v4 M10 5l2 2 2-2 M6 4v4 M4 6l2 2 2-2 M18 4v4 M16 6l2 2 2-2"),
    "proyeccion_cilindrica": _j(_e(12, 6, 6, 2), "M6 6v12 M18 6v12 M6 18a6 2 0 0 0 12 0", "M2 12h2 M20 12h2"),
    "proyeccion_esferica": _j(_c(12, 12, 6.5), _e(12, 12, 6.5, 2.4), "M12 2v2 M12 20v2 M2 12h2 M20 12h2"),
    "proyeccion_camara": _j("M3 8h9v8H3z M12 10.5l4-2.5v8l-4-2.5", "M18 7l3-1.5 M18 12h3 M18 17l3 1.5"),
    "cortar_uv": _j(_c(6, 17, 2.8), _c(6, 7, 2.8), "M8.4 8.6L20 18 M8.4 15.4L20 6"),
    "coser_uv": "M4 4v16 M20 4v16 M4 7l16 3 M20 10L4 13 M4 13l16 3 M20 16L4 19",
    "enderezar": "M4 8c3-3 5 3 8 0s5 3 8 0 M4 16h16 M12 10.5v3 M10.5 12.5L12 14l1.5-1.5",
    "orientar": _j(_p((12, 4), (20, 12), (12, 20), (4, 12), cerrada=True), "M8 8h8v8H8z"),
    "juntar": _j("M3 5h7v7H3z M14 12h7v7h-7z", "M10 12l4 0 M12.5 10.5L14 12l-1.5 1.5"),
    "patron_comprobacion": "M4 4h16v16H4z M4 9.3h16 M4 14.7h16 M9.3 4v16 M14.7 4v16 M4 9.3l5.3-5.3 M14.7 9.3L20 4 M9.3 14.7l5.4-5.4 M4 20l5.3-5.3 M14.7 20l5.3-5.3",
    "textura": _j("M3 5h18v14H3z", _c(8.5, 9.5, 1.8), "M3 17l5-4.5 4 3 4-5 5 5.5"),
    # --- Ventanas y editores --------------------------------------------------------
    "ventana": _j(_VENTANA, _punto(5.5, 7), _punto(8, 7)),
    "nodos": "M3 4h7v5H3z M14 15h7v5h-7z M10 6.5c5 0 0 11 4 11 M3 15h7v5H3z M10 17.5h4",
    "outliner": _j(_VENTANA, "M6 12.5h4 M8 15.5h6 M8 18h8 M6 12.5v5.5", "M6 15.5h2"),
    "atributos": _j(_VENTANA, "M6 13h4 M13 12h5v2h-5z M6 17h4 M13 16h5v2h-5z"),
    "canales": _j("M4 4h16v16H4z", "M4 9h16 M4 14h16 M12 4v16", "M7 6.5h2 M15 6.5h2 M7 11.5h2 M15 11.5h2 M7 16.5h2 M15 16.5h2"),
    "script": _j(_VENTANA, "M6.5 12.5l2.5 2-2.5 2 M11 17h5"),
    "atajos": _j("M2 6h20v12H2z", "M5 9h1 M8 9h1 M11 9h1 M14 9h1 M17 9h2 M5 12h1 M8 12h1 M11 12h1 M14 12h1 M17 12h2 M7 15h10"),
    "plugin": "M9 3v5 M15 3v5 M6 8h12v4a6 6 0 0 1-12 0z M12 18v3",
    "render_interactivo": _j("M3 8h18v11H3z M8 8l1.5-3h5L16 8", "M10.5 11v5l4-2.5z"),
    "ajustes_render": _j("M3 8h12v9H3z M7 8l1-2.5h3L12 8", _c(18.5, 15.5, 2), "M18.5 11.5v1.5 M18.5 18v1.5 M14.5 15.5H16 M21 15.5h1.5"),
    "material": _j(_c(12, 12, 8.5), "M7 9a5.5 5.5 0 0 1 4-3 M17 12a5 5 0 0 1-5 5 M3.5 12c3 3 14 3 17 0"),
    "material_nuevo": _j(_c(11, 13, 7.5), "M6.5 11a4.5 4.5 0 0 1 3-3 M18 3v6 M15 6h6"),
    "luz_direccional": _j(_c(6.5, 6.5, 2.5), "M10 10l9 9 M10 14l6 6 M14 10l6 6 M19 15v4h-4"),
    "luz_puntual": _j(_c(12, 12, 3), "M12 3v3 M12 18v3 M3 12h3 M18 12h3 M5.6 5.6l2.1 2.1 M16.3 16.3l2.1 2.1 M5.6 18.4l2.1-2.1 M16.3 7.7l2.1-2.1"),
    "foco": _j("M8 3h8l-1.5 6h-5z", "M9.5 9L5 20 M14.5 9L19 20", "M5 20a7 1.5 0 0 0 14 0"),
    "luz_area": "M5 4h14v8H5z M7 14l-2 6 M12 14v6 M17 14l2 6",
    "proyecto": "M3 6h6l2 2h10v11H3z M9.5 13.5l2 2 4-4",
    # --- Animación ------------------------------------------------------------------
    "clave": _ROMBO,
    "clave_mover": _j(_ROMBO_P, "M16 9v12 M10 15h12 M14.5 10.5L16 9l1.5 1.5 M20.5 13.5L22 15l-1.5 1.5"),
    "clave_rotar": _j(_ROMBO_P, "M21 15a5 5 0 1 1-1.5-3.6 M21 9.5v2.5h-2.5"),
    "clave_escalar": _j(_ROMBO_P, "M11 21h5v-5h-5z M16 16l5-5 M18 11h3v3"),
    "parar": "M6 6h12v12H6z",
    "final": "M18 5v14 M6 5l9 7-9 7z",
    "clave_siguiente": _j(_p((5, 8), (9, 12), (5, 16), (1, 12), cerrada=True), "M12 6l6 6-6 6 M18 6v12"),
    "clave_anterior": _j(_p((19, 8), (23, 12), (19, 16), (15, 12), cerrada=True), "M12 6l-6 6 6 6 M6 6v12"),
    "fotograma_siguiente": "M7 6l6 6-6 6 M17 6v12",
    "fotograma_anterior": "M17 6l-6 6 6 6 M7 6v12",
    "editor_tiempo": "M3 5h18 M3 19h18 M5 9h8v3H5z M10 14h9v3h-9z M15 3v18",
    "playblast": _j("M3 5h18v14H3z M7 5v14 M17 5v14", "M10 9.5v5l4-2.5z"),
    "papel_cebolla": _j(_c(7, 12, 3.5), _c(12, 12, 3.5), _c(17, 12, 3.5)),
    "trayectoria": _j("M3 19c2 0 3-1 4-2.5 M9 13c1-2 2-4 4-5 M15.5 6.8c1.5-.6 3-.8 5.5-.8", _c(19, 6, 2.2)),
    "animar_ruta": _j("M3 18C6 6 14 18 21 6", "M14.5 10.5l3.5-.5.5 3.5"),
    "restriccion": "M10 14a4 4 0 0 1 0-5.7l2.3-2.3a4 4 0 0 1 5.7 5.7l-1.5 1.5 M14 10a4 4 0 0 1 0 5.7l-2.3 2.3a4 4 0 0 1-5.7-5.7l1.5-1.5",
    "restriccion_padre": _j(_c(12, 5, 2.5), _c(12, 19, 2.5), "M12 7.5v3 M12 13.5v3", "M10.5 12h3"),
    "restriccion_punto": _j(_c(12, 12, 2), "M12 3v5 M12 16v5 M3 12h5 M16 12h5"),
    "restriccion_orientar": _j(_c(12, 12, 8), "M12 12l5-5 M14 7h3v3", _punto(12, 12)),
    "apuntar": _j(_c(14, 10, 7), _c(14, 10, 3), "M3 21l9-9 M3 17v4h4"),
    "hueso": _j(_c(6, 18, 2.5), _c(18, 6, 2.5), "M7.8 16.2L16.2 7.8"),
    "esqueleto": _j(_c(12, 4.5, 1.8), _c(12, 12, 1.8), _c(7, 19.5, 1.8), _c(17, 19.5, 1.8), "M12 6.3v3.9 M10.9 13.4L8 17.9 M13.1 13.4L16 17.9"),
    "vincular_piel": _j(_c(9, 15, 2), _c(15, 9, 2), "M10.4 13.6l3.2-3.2", "M4 13c0-5 4-9 9-9h3 M20 11c0 5-4 9-9 9H8"),
    "pintar_pesos": "M3 21c2 0 5-1 5-4a2 2 0 0 0-4 0c0 2-1 3-1 4z M9 15l11-11 M7.5 13.5L19 2",
    "pose": _j(_c(12, 4.5, 2), "M12 6.5V14 M6 9h12 M12 14l-4 7 M12 14l4 7"),
    "simulacion": _j("M4 12a8 8 0 0 1 14-5.3 M18 3v4h-4 M20 12a8 8 0 0 1-14 5.3 M6 21v-4h4", _c(12, 12, 2)),
    "animacion": _j("M3 20c2-10 5-10 7 0 M10 20c1.5-6 3.5-6 5 0", _c(18.5, 8, 2.5)),
    # --- Vista --------------------------------------------------------------------
    "encuadrar": _j(_ESQUINAS, _r(9, 9, 6, 6)),
    "encuadrar_todo": _j(_ESQUINAS, _r(7.5, 7.5, 4, 4), _r(12.5, 12.5, 4, 4), _r(12.5, 7.5, 4, 4), _r(7.5, 12.5, 4, 4)),
    "aislar": _j(_ESQUINAS, "M6.5 12s2.2-4 5.5-4 5.5 4 5.5 4-2.2 4-5.5 4-5.5-4-5.5-4z", _c(12, 12, 1.5)),
    "malla_sombreado": _j(_CUBO, "M8 5.2v9 M16 5.2v9 M4 12h16"),
    "rayos_x": "M12 3l8 4.5v9L12 21l-8-4.5v-9z M4 7.5l8 4.5 8-4.5 M12 12v9 M4 16.5l2-1.1 M8.5 14l1.5-.9 M12 3v2 M12 7.5v2 M14 13l2 1.1",
    "ver_sombreado": _j(_c(12, 12, 8.5), "M12 3.5v17 M14.5 4v16 M17 5.3v13.4 M19.2 7.5v9"),
    "ver_texturas": _j(_c(12, 12, 8.5), "M3.5 12h17 M12 3.5v17 M6 6l12 12 M18 6L6 18"),
    "ver_luces": _j("M9 18h6 M10 21h4 M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z", "M2 8h2 M20 8h2 M4 2.5l1.5 1.5 M20 2.5L18.5 4"),
    "vista_suavizada": _j("M3 7h6v6H3z", "M10.5 10h2.5 M12 8.5L13.5 10 12 11.5", _c(18, 10, 3.5), "M3 20h18"),
    "contar_poligonos": "M8 4L6 20 M16 4l-2 16 M4 9h16 M3 15h16",
    "informacion": _j(_r(3, 4, 18, 14), "M6 7h4 M6 10h3 M15 15h3 M9 21h6 M12 18v3"),
    "simetria": "M12 3v2 M12 7.5v2 M12 14.5v2 M12 19v2 M9.5 6a6 6 0 0 0 0 12 M14.5 6a6 6 0 0 1 0 12",
    "visor": _j("M3 5h18v14H3z", "M12 9l4 2v4l-4 2-4-2v-4z M8 11l4 2 4-2 M12 13v4"),
    "panel": "M3 4h18v16H3z M12 4v16 M3 12h18",
    # --- Archivo y edición ----------------------------------------------------------
    "guardar": "M5 4h11l3 3v13H5z M8 4v5h7V4 M8 20v-6h8v6",
    "guardar_como": "M4 4h10l3 3v5 M4 4v16h7 M7 4v4h6V4 M14 21l6-6 2 2-6 6z".replace(" M14 21l6-6 2 2-6 6z", " M13 20l6-6 2 2-6 6h-2z"),
    "importar": "M4 14v6h16v-6 M12 3v12 M8 11l4 4 4-4",
    "exportar": "M4 14v6h16v-6 M12 15V3 M8 7l4-4 4 4",
    "abrir": "M3 6h6l2 2h8v3 M3 6v13h15l3-8H7l-4 8",
    "nueva": "M6 3h8l4 4v6 M6 3v18h7 M14 3v4h4 M18 16v6 M15 19h6",
    "deshacer": "M9 14L4 9l5-5 M4 9h10a6 6 0 0 1 0 12h-3",
    "rehacer": "M15 14l5-5-5-5 M20 9H10a6 6 0 0 0 0 12h3",
    "repetir": "M4 12a8 8 0 0 1 14-5.3 M18 3v4h-4 M20 12a8 8 0 0 1-14 5.3 M6 21v-4h4",
    "copiar": "M8.5 8.5h11v11h-11z M5 15.5V4.5h11",
    "pegar": "M8 4h-3v17h14V4h-3 M8 2.5h8v3H8z M8 11h8 M8 15h6",
    "cortar": _j(_c(6, 18, 2.6), _c(18, 18, 2.6), "M7.8 16L17 3 M16.2 16L7 3"),
    "referencia": _j("M10 13.5a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10.5a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"),
    "herramienta": "M13 4l7 7-3 3-7-7z M11.5 8.5L4 16l4 4 7.5-7.5 M15 2l2 2",
    "editar": "M4 20l1-5L16 4l4 4L9 19z M14 6l4 4",
    "medir": "M3 17L17 3l4 4L7 21z M7 13l2 2 M10 10l2 2 M13 7l2 2",
    "ayuda": _j(_c(12, 12, 9), "M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6", _punto(12, 17)),
    "orden": _j("M3 5h18v14H3z", "M7 10l3 2-3 2 M12 15h5"),
    # --- Dinámica, efectos y otros módulos ----------------------------------------------
    "particulas": _j(_punto(6, 6), _punto(12, 4), _punto(18, 7), _punto(4, 12), _punto(10, 11), _punto(16, 13), _punto(20, 17), _punto(7, 18), _punto(13, 19), _punto(15, 8)),
    "tela": "M4 5c3 2 5-2 8 0s5-2 8 0v14c-3-2-5 2-8 0s-5 2-8 0z M4 12c3 2 5-2 8 0s5-2 8 0",
    "viento": "M3 8h10a3 3 0 1 0-3-3 M3 12h15a3 3 0 1 1-3 3 M3 16h7",
    "fluido": "M12 3c3 5 6 8 6 12a6 6 0 0 1-12 0c0-4 3-7 6-12z M9 15a3 3 0 0 0 3 3",
    "pelo": "M4 20c1-6 1-10 3-16 M9 20c0-6 1-10 4-16 M14 20c0-5 2-10 6-15 M19 20c0-3 0-5 1-7",
    "mash": _j(_r(4, 4, 4, 4), _r(10, 4, 4, 4), _r(16, 4, 4, 4), _r(4, 10, 4, 4), _r(10, 10, 4, 4), _r(16, 10, 4, 4), _r(4, 16, 4, 4), _r(10, 16, 4, 4), _r(16, 16, 4, 4)),
    "cache": _j(_e(12, 5.5, 7, 2.5), "M5 5.5v13a7 2.5 0 0 0 14 0v-13 M5 12a7 2.5 0 0 0 14 0"),
    "efectos": "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z M18 15l.8 2.2L21 18l-2.2.8L18 21l-.8-2.2L15 18l2.2-.8z",
    "pintar": "M18 3l3 3-9 9-3-3z M9 12c-3 0-4 2-4 4 0 2-1 3-2 4 3 0 8 0 8-5",
    "capas": "M12 3l9 4.5-9 4.5-9-4.5z M3 12l9 4.5 9-4.5 M3 16.5L12 21l9-4.5",
    "lista": "M8 6h12 M8 12h12 M8 18h12 M4 6h0 M4 12h0 M4 18h0",
}

# Las formas ``"M4 6h0"`` (un punto) solo se ven con puntas redondeadas: las
# cambiamos por puntos reales para que se vean igual con cualquier render.
for _clave, _trazo in list(TRAZOS_ACCIONES.items()):
    _puntos = re.findall(r"M(\d+(?:\.\d+)?) (\d+(?:\.\d+)?)h0", _trazo)
    for _x, _y in _puntos:
        _trazo = _trazo.replace("M{} {}h0".format(_x, _y), _punto(float(_x), float(_y)))
    TRAZOS_ACCIONES[_clave] = _trazo


# --- Comando -> icono ---------------------------------------------------------------

# Iconos de ``iconos.py`` que también se usan aquí: duplicar, pivote, congelar,
# historial, hypershade, render, cubo, mover, rotar, escalar, camara, luz, uv,
# llave, codigo, grafica, fotogramas, play, inicio, hornear, engranaje, cielo,
# plano, desplegar, organizar, ojo, estrella, malla, lapiz, carpeta, papelera,
# rayo, estante, lupa.

POR_COMANDO = {
    # Transformar y pivote
    "CenterPivot": "pivote", "BakeCustomPivot": "hornear", "FreezeTransformations": "congelar",
    "ResetTransformations": "restablecer", "DeleteHistory": "historial", "DeleteAllHistory": "historial",
    "DeleteHistoryOptions": "historial", "DuplicateSpecialOptions": "duplicar", "DuplicateSpecial": "duplicar",
    "DuplicateWithTransform": "duplicar", "Duplicate": "duplicar", "InstanceOptions": "duplicar",
    "Group": "grupo", "GroupOptions": "grupo", "Ungroup": "desagrupar", "Parent": "emparentar",
    "Unparent": "desemparentar", "SelectHierarchy": "jerarquia", "InvertSelection": "invertir_seleccion",
    "SelectAll": "seleccionar_todo", "SelectAllGeometry": "seleccionar_todo", "SelectTool": "seleccionar",
    "HideSelectedObjects": "ocultar", "HideSelectedItems": "ocultar", "ShowAll": "mostrar_todo",
    "ShowLastHidden": "mostrar_ultimo", "ShowSelectedObjects": "ojo", "MatchTransform": "igualar",
    "MatchTranslation": "igualar", "MatchRotation": "igualar", "MatchScaling": "igualar", "MatchPivots": "igualar",
    "SnapToGrid": "iman", "ToggleLocalRotationAxes": "ejes", "CreateLocator": "localizador",
    "CreateEmptyGroup": "grupo_vacio", "MoveTool": "mover", "RotateTool": "rotar", "ScaleTool": "escalar",
    "UniversalManip": "mover", "ShowManipulators": "mover", "EnterEditMode": "pivote", "TogglePivot": "pivote",
    # Crear
    "CreatePolygonCube": "cubo", "CreatePolygonSphere": "esfera", "CreatePolygonCylinder": "cilindro",
    "CreatePolygonPlane": "plano_malla", "CreatePolygonTorus": "toroide", "CreatePolygonCone": "cono",
    "CreatePolygonPipe": "tubo", "CreatePolygonDisc": "disco", "CreateNURBSCircle": "circulo_nurbs",
    "CreateNURBSSquare": "cuadrado_nurbs", "CreateCameraOnly": "camara", "CreateCamera": "camara",
    "CreatePolygonType": "texto_3d", "CreateTextOptions": "texto_3d", "CreateNURBSSphere": "esfera",
    "CreateNURBSCube": "cubo", "CreateNURBSCylinder": "cilindro", "CreateNURBSPlane": "plano_malla",
    "CreateNURBSTorus": "toroide", "CreateNURBSCone": "cono", "CreateEPCurveTool": "curva_ep",
    "CreateEPCurveToolOptions": "curva_ep", "CVCurveTool": "curva_ep", "EPCurveTool": "curva_ep",
    "PencilCurveTool": "lapiz_curva", "CreateBezierCurveTool": "curva", "BezierCurveTool": "curva",
    # Modelado
    "PolyExtrude": "extruir", "PolyExtrudeOptions": "extruir", "PolyExtrudeFacets": "extruir",
    "PolyExtrudeEdges": "extruir", "PolyExtrudeVertices": "extruir", "BevelPolygon": "biselar",
    "BevelPolygonOptions": "biselar", "BridgeEdge": "puente", "BridgeEdgeOptions": "puente",
    "PolyMerge": "unir", "PolyMergeOptions": "unir", "MergeVertexTool": "unir", "PolyMergeVertex": "unir",
    "MergeVertices": "unir", "MergeToCenter": "unir_centro", "CollapseFace": "colapsar",
    "PolygonCollapse": "colapsar", "ExtractFace": "extraer", "DuplicateFace": "duplicar",
    "DetachComponent": "separar_componentes", "PolyAppendTool": "anadir_poligono", "AppendToPolygonTool": "anadir_poligono",
    "CreatePolygonTool": "anadir_poligono", "FillHole": "rellenar",
    "PolygonBooleanUnion": "booleana_union", "PolygonBooleanDifference": "booleana_diferencia",
    "PolygonBooleanIntersection": "booleana_interseccion", "CombinePolygons": "combinar",
    "SeparatePolygon": "separar", "PolygonCombine": "combinar", "PolygonSeparate": "separar",
    "SmoothPolygon": "suavizar", "SmoothPolygonOptions": "suavizar", "ReducePolygon": "reducir",
    "ReducePolygonOptions": "reducir", "Triangulate": "triangular", "Quadrangulate": "cuadrangular",
    "MirrorPolygonGeometry": "simetria_malla", "PolyMirror": "simetria_malla", "MirrorPolygonGeometryOptions": "simetria_malla",
    "CleanupPolygon": "limpiar", "CleanupPolygonOptions": "limpiar", "InsertEdgeLoopTool": "insertar_bucle",
    "SplitEdgeRingTool": "insertar_bucle", "MultiCutTool": "corte_multiple", "dR_multiCutTool": "corte_multiple",
    "dR_connectTool": "conectar", "ConnectComponents": "conectar", "dR_quadDrawTool": "dibujo_quads", "dR_targetWeldTool": "soldar",
    "OffsetEdgeLoopTool": "desplazar_bucle", "PolySlideEdge": "deslizar", "SlideEdgeTool": "deslizar",
    "DeleteEdge": "borrar_arista", "DeleteVertex": "borrar_vertice", "PolyCircularize": "circularizar",
    "ChamferVertex": "achaflanar", "PokePolygon": "pinchar", "WedgePolygon": "cuna",
    "SubdivideFace": "subdividir", "SubdividePolygon": "subdividir", "PolyAverageVertex": "promediar", "AverageVertex": "promediar",
    "ReversePolygonNormals": "invertir_normales", "ConformPolygonNormals": "unificar_normales",
    "SoftPolyEdgeElements": "aristas_suaves", "HardPolyEdgeElements": "aristas_duras",
    "PolygonSoftenEdge": "aristas_suaves", "PolygonHardenEdge": "aristas_duras",
    "PolygonSoftenHarden": "suavizar_endurecer", "SetToFaceNormals": "normales",
    "ToggleFaceNormalDisplay": "normales", "ToggleVertexNormalDisplay": "normales",
    # Selección de componentes
    "ConvertSelectionToFaces": "a_caras", "ConvertSelectionToEdges": "a_aristas",
    "ConvertSelectionToVertices": "a_vertices", "ConvertSelectionToUVs": "a_uv",
    "ConvertSelectionToShell": "a_isla", "SelectEdgeLoopSp": "bucle", "SelectEdgeLoop": "bucle",
    "SelectEdgeRingSp": "anillo", "SelectEdgeRing": "anillo", "GrowPolygonSelectionRegion": "ampliar_seleccion",
    "ShrinkPolygonSelectionRegion": "reducir_seleccion", "SelectToggleMode": "objeto_componente",
    "SelectVertexMask": "a_vertices", "SelectEdgeMask": "a_aristas", "SelectFacetMask": "a_caras",
    "SelectMeshUVShell": "a_isla", "SelectUVMask": "a_uv",
    # Esculpir y deformar
    "SculptGeometryTool": "esculpir", "SetMeshSculptTool": "esculpir", "SetMeshSmoothTool": "suavizar",
    "SetMeshGrabTool": "agarrar", "SetMeshRelaxTool": "promediar", "SetMeshFlattenTool": "enderezar",
    "SoftModTool": "mod_suave", "SoftModDeformer": "mod_suave", "LatticeDeformer": "lattice",
    "CreateLattice": "lattice", "Bend": "doblar", "Twist": "torcer", "Flare": "deformador", "Sine": "deformador",
    "Squash": "deformador", "Wave": "deformador", "CreateCluster": "localizador", "CreateWrap": "malla",
    "CreateBlendShape": "deformador", "ShapeEditor": "deformador",
    # UV
    "TextureViewWindow": "uv", "UVEditor": "uv", "UVAutomaticProjection": "proyeccion_auto",
    "UVPlanarProjection": "proyeccion_plana", "UVCylindricProjection": "proyeccion_cilindrica",
    "UVSphericalProjection": "proyeccion_esferica", "UVCameraBasedProjection": "proyeccion_camara",
    "UVUnfold": "desplegar", "UnfoldUV": "desplegar", "UVLayout": "organizar", "LayoutUV": "organizar",
    "CutUVs": "cortar_uv", "CutPolygon": "cortar_uv", "SewUVs": "coser_uv", "polySewUV": "coser_uv",
    "UVStraighten": "enderezar", "UVOrientShells": "orientar", "UVSnapTogether": "juntar",
    "ToggleUVTextureImage": "textura", "UVCheckerMap": "patron_comprobacion",
    # Ventanas y editores
    "HypershadeWindow": "hypershade", "NodeEditorWindow": "nodos", "OutlinerWindow": "outliner",
    "AttributeEditor": "atributos", "ToggleAttributeEditor": "atributos", "ToggleChannelsLayers": "canales",
    "ToggleChannelBox": "canales", "ChannelBoxWindow": "canales", "ScriptEditor": "script",
    "HotkeyPreferencesWindow": "atajos", "PreferencesWindow": "engranaje", "PluginManager": "plugin",
    "ShelfPreferencesWindow": "estante", "ComponentEditor": "atributos", "ConnectionEditor": "nodos",
    "NamespaceEditor": "outliner", "DisplayLayerEditorWindow": "capas", "ToolSettingsWindow": "engranaje",
    "ContentBrowserWindow": "carpeta", "FileBrowserWindow": "carpeta", "ReferenceEditor": "referencia",
    "HypergraphHierarchyWindow": "jerarquia", "HypergraphDGWindow": "nodos", "VisorWindow": "carpeta",
    "ShapeEditorWindow": "deformador", "ExpressionEditor": "codigo",
    # Render y luces
    "RenderViewWindow": "render", "RenderGlobalsWindow": "ajustes_render", "RenderIntoNewWindow": "render",
    "RenderSetupWindow": "capas", "RenderLayerEditorWindow": "capas", "IPRRenderIntoNewWindow": "render_interactivo",
    "RedoPreviousRender": "render", "CreateDirectionalLight": "luz_direccional", "CreatePointLight": "luz_puntual",
    "CreateSpotLight": "foco", "CreateAreaLight": "luz_area", "CreateAmbientLight": "luz",
    "CreateVolumeLight": "luz", "AssignNewMaterial": "material_nuevo", "AssignNewPBSMaterial": "material_nuevo",
    "AssignOfflineFile": "carpeta", "LightCentricLightLinkingEditor": "luz", "LightEditorWindow": "luz",
    "ProjectWindow": "proyecto", "SetProject": "proyecto",
    # Animación
    "SetKey": "llave", "SetKeyOptions": "llave", "SetKeyTranslate": "clave_mover", "SetKeyRotate": "clave_rotar",
    "SetKeyScale": "clave_escalar", "SetKeyAnimated": "clave", "SetBreakdown": "clave",
    "GraphEditor": "grafica", "DopeSheetEditor": "fotogramas", "TimeEditorWindow": "editor_tiempo",
    "TraxEditorWindow": "editor_tiempo", "PlaybackToggle": "play", "PlaybackForward": "play",
    "PlaybackBackward": "play", "PlaybackStop": "parar", "GoToMinFrame": "inicio", "GoToMaxFrame": "final",
    "NextKey": "clave_siguiente", "PreviousKey": "clave_anterior", "NextFrame": "fotograma_siguiente",
    "PreviousFrame": "fotograma_anterior", "BakeSimulationOptions": "hornear", "BakeSimulation": "hornear",
    "PlayblastOptions": "playblast", "Playblast": "playblast", "GhostingOptions": "papel_cebolla",
    "GhostSelected": "papel_cebolla", "MotionTrail": "trayectoria", "CreateMotionTrail": "trayectoria",
    "AttachToPath": "animar_ruta", "ParentConstraint": "restriccion_padre", "ParentConstraintOptions": "restriccion_padre",
    "PointConstraint": "restriccion_punto", "PointConstraintOptions": "restriccion_punto",
    "OrientConstraint": "restriccion_orientar", "OrientConstraintOptions": "restriccion_orientar",
    "AimConstraint": "apuntar", "AimConstraintOptions": "apuntar", "ScaleConstraint": "escalar",
    "JointTool": "hueso", "IKHandleTool": "hueso", "MirrorJoint": "simetria", "SmoothBindSkin": "vincular_piel",
    "SmoothBindSkinOptions": "vincular_piel", "DetachSkin": "desemparentar",
    "ArtPaintSkinWeightsTool": "pintar_pesos", "ArtPaintSkinWeightsToolOptions": "pintar_pesos",
    "GoToBindPose": "pose", "HumanIKWindow": "esqueleto", "QuickRigWindow": "esqueleto",
    # Vista
    "FrameSelected": "encuadrar", "FrameAll": "encuadrar_todo", "FrameSelectedWithoutChildren": "encuadrar",
    "FrameAllInAllViews": "encuadrar_todo", "FrameSelectedInAllViews": "encuadrar",
    "ToggleIsolateSelect": "aislar", "ToggleWireframeOnShaded": "malla_sombreado", "ToggleXRay": "rayos_x",
    "ToggleGrid": "rejilla", "DisplayWireframe": "cubo", "DisplayShaded": "ver_sombreado",
    "DisplayShadedAndTextured": "ver_texturas", "DisplayLight": "ver_luces", "SmoothProxy": "vista_suavizada",
    "TogglePolyCount": "contar_poligonos", "ToggleHeadsUpDisplay": "informacion",
    "SnapToGridPress": "iman", "SnapToPointPress": "iman", "SnapToCurvePress": "iman",
    "ToggleSymmetryDisplay": "simetria", "ToggleBackfaceGeometry": "a_caras", "ToggleBorderEdges": "a_aristas",
    "SingleViewArrangement": "visor", "FourViewLayout": "panel", "TogglePanelMenubar": "panel",
    "PanePop": "visor", "ToggleViewCube": "cubo", "DisplaySmoothShaded": "ver_sombreado",
    "DisplayTextures": "ver_texturas", "ToggleDisplayGradient": "ver_sombreado",
    # Archivo y edición
    "SaveScene": "guardar", "SaveSceneAs": "guardar_como", "SaveSceneAsOptions": "guardar_como",
    "IncrementAndSave": "guardar", "Import": "importar", "ImportOptions": "importar",
    "ExportSelection": "exportar", "ExportSelectionOptions": "exportar", "Export": "exportar",
    "ExportAll": "exportar", "OpenScene": "abrir", "NewScene": "nueva", "NewSceneOptions": "nueva",
    "CreateReference": "referencia", "ArchiveScene": "carpeta", "OptimizeScene": "limpiar",
    "OptimizeSceneOptions": "limpiar", "Undo": "deshacer", "Redo": "rehacer", "RepeatLast": "repetir",
    "Delete": "papelera", "DeleteAll": "papelera", "CutSelected": "cortar", "CopySelected": "copiar",
    "PasteSelected": "pegar", "DistanceTool": "medir", "MeasureTool": "medir", "Help": "ayuda",
    # Dinámica y efectos
    "nParticleTool": "particulas", "CreateNParticles": "particulas", "CreateEmitter": "particulas",
    "nClothCreate": "tela", "CreateNCloth": "tela", "AirOptions": "viento", "Air": "viento",
    "Gravity": "viento", "Turbulence": "viento", "BifrostLiquid": "fluido", "CreateBifrostLiquid": "fluido",
    "CreateFluid": "fluido", "CreateXGenDescription": "pelo", "XgCreateDescription": "pelo",
    "CreateMASHNetwork": "mash", "MASHCreateNetwork": "mash", "PaintEffectsTool": "pintar",
    "PaintEffectsWindow": "pintar", "CreateNSolver": "simulacion", "InteractivePlayback": "simulacion",
}

# Reglas por palabras del nombre (en orden: gana la primera que encaja).
# Cada regla: (palabras que deben estar todas, icono).
REGLAS = [
    (("boolean", "union"), "booleana_union"), (("boolean", "difference"), "booleana_diferencia"),
    (("boolean", "intersection"), "booleana_interseccion"), (("boolean",), "booleana_union"),
    (("set", "key"), "llave"), (("next", "key"), "clave_siguiente"), (("previous", "key"), "clave_anterior"),
    (("key",), "clave"), (("keyframe",), "clave"), (("breakdown",), "clave"),
    (("constraint", "parent"), "restriccion_padre"), (("constraint", "point"), "restriccion_punto"),
    (("constraint", "orient"), "restriccion_orientar"), (("constraint", "aim"), "apuntar"),
    (("constraint",), "restriccion"), (("constrain",), "restriccion"),
    (("light", "directional"), "luz_direccional"), (("light", "point"), "luz_puntual"),
    (("light", "spot"), "foco"), (("light", "area"), "luz_area"), (("sky",), "cielo"),
    (("light",), "luz"), (("lights",), "luz"), (("lighting",), "luz"),
    (("camera",), "camara"), (("cameras",), "camara"),
    (("render", "settings"), "ajustes_render"), (("render", "globals"), "ajustes_render"),
    (("ipr",), "render_interactivo"), (("render",), "render"), (("arnold",), "render"),
    (("material",), "material"), (("shader",), "material"), (("shading",), "material"),
    (("hypershade",), "hypershade"), (("texture",), "textura"), (("checker",), "patron_comprobacion"),
    (("projection", "planar"), "proyeccion_plana"), (("projection", "cylindrical"), "proyeccion_cilindrica"),
    (("projection", "cylindric"), "proyeccion_cilindrica"), (("projection", "spherical"), "proyeccion_esferica"),
    (("projection", "automatic"), "proyeccion_auto"), (("projection", "auto"), "proyeccion_auto"), (("projection", "camera"), "proyeccion_camara"),
    (("projection",), "proyeccion_plana"), (("unfold",), "desplegar"), (("layout", "uv"), "organizar"),
    (("sew",), "coser_uv"), (("uv",), "uv"), (("uvs",), "uv"),
    (("extrude",), "extruir"), (("bevel",), "biselar"), (("bridge",), "puente"), (("chamfer",), "achaflanar"),
    (("merge",), "unir"), (("weld",), "soldar"), (("collapse",), "colapsar"), (("extract",), "extraer"),
    (("detach",), "separar_componentes"), (("separate",), "separar"), (("combine",), "combinar"),
    (("fill", "hole"), "rellenar"), (("mirror",), "simetria_malla"), (("symmetry",), "simetria"),
    (("smooth",), "suavizar"), (("reduce",), "reducir"), (("triangulate",), "triangular"),
    (("quadrangulate",), "cuadrangular"), (("cleanup",), "limpiar"), (("clean",), "limpiar"),
    (("edge", "loop"), "bucle"), (("loop",), "bucle"), (("ring",), "anillo"), (("multi", "cut"), "corte_multiple"),
    (("cut",), "cortar_uv"), (("slide",), "deslizar"), (("poke",), "pinchar"), (("wedge",), "cuna"),
    (("subdivide",), "subdividir"), (("average",), "promediar"), (("relax",), "promediar"),
    (("normals",), "normales"), (("normal",), "normales"), (("soften",), "aristas_suaves"),
    (("harden",), "aristas_duras"), (("sculpt",), "esculpir"), (("lattice",), "lattice"),
    (("bend",), "doblar"), (("twist",), "torcer"), (("deformer",), "deformador"), (("blend", "shape"), "deformador"),
    (("joint",), "hueso"), (("ik",), "hueso"), (("skeleton",), "esqueleto"), (("rig",), "esqueleto"),
    (("bind",), "vincular_piel"), (("skin",), "vincular_piel"), (("weights",), "pintar_pesos"),
    (("pose",), "pose"), (("motion", "trail"), "trayectoria"), (("path",), "animar_ruta"),
    (("ghost",), "papel_cebolla"), (("ghosting",), "papel_cebolla"), (("playblast",), "playblast"),
    (("playback", "stop"), "parar"), (("playback",), "play"), (("play",), "play"), (("stop",), "parar"),
    (("min", "frame"), "inicio"), (("max", "frame"), "final"), (("next", "frame"), "fotograma_siguiente"),
    (("previous", "frame"), "fotograma_anterior"), (("bake",), "hornear"), (("graph",), "grafica"),
    (("dope",), "fotogramas"), (("time", "editor"), "editor_tiempo"), (("trax",), "editor_tiempo"),
    (("particle",), "particulas"), (("particles",), "particulas"), (("n", "particle"), "particulas"),
    (("emitter",), "particulas"), (("cloth",), "tela"), (("ncloth",), "tela"), (("hair",), "pelo"),
    (("xgen",), "pelo"), (("fur",), "pelo"), (("fluid",), "fluido"), (("bifrost",), "fluido"),
    (("liquid",), "fluido"), (("ocean",), "fluido"), (("air",), "viento"), (("wind",), "viento"),
    (("gravity",), "viento"), (("field",), "viento"), (("turbulence",), "viento"), (("mash",), "mash"),
    (("solver",), "simulacion"), (("simulation",), "simulacion"), (("cache",), "cache"),
    (("paint", "effects"), "pintar"), (("paint",), "pintar"), (("brush",), "pintar"),
    (("frame", "all"), "encuadrar_todo"), (("frame",), "encuadrar"), (("isolate",), "aislar"),
    (("xray",), "rayos_x"), (("x", "ray"), "rayos_x"), (("wireframe",), "malla_sombreado"),
    (("grid",), "rejilla"), (("snap",), "iman"), (("textured",), "ver_texturas"), (("shaded",), "ver_sombreado"),
    (("hud",), "informacion"), (("heads", "up"), "informacion"), (("poly", "count"), "contar_poligonos"),
    (("hide",), "ocultar"), (("show",), "ojo"), (("unhide",), "ojo"), (("display",), "ojo"),
    (("layer",), "capas"), (("layers",), "capas"), (("view",), "visor"), (("panel",), "panel"),
    (("pane",), "panel"), (("layout",), "panel"),
    (("cube",), "cubo"), (("sphere",), "esfera"), (("cylinder",), "cilindro"), (("cone",), "cono"),
    (("torus",), "toroide"), (("pipe",), "tubo"), (("disc",), "disco"), (("plane",), "plano_malla"),
    (("circle",), "circulo_nurbs"), (("square",), "cuadrado_nurbs"), (("text",), "texto_3d"),
    (("type",), "texto_3d"), (("locator",), "localizador"), (("curve",), "curva"), (("curves",), "curva"),
    (("surface",), "superficie"), (("surfaces",), "superficie"), (("loft",), "superficie"),
    (("revolve",), "superficie"), (("nurbs",), "superficie"),
    (("ungroup",), "desagrupar"), (("group",), "grupo"), (("unparent",), "desemparentar"),
    (("parent",), "emparentar"), (("hierarchy",), "jerarquia"), (("outliner",), "outliner"),
    (("pivot",), "pivote"), (("freeze",), "congelar"), (("reset",), "restablecer"), (("match",), "igualar"),
    (("history",), "historial"), (("duplicate",), "duplicar"), (("instance",), "duplicar"),
    (("move",), "mover"), (("translate",), "mover"), (("rotate",), "rotar"), (("scale",), "escalar"),
    (("grow",), "ampliar_seleccion"), (("shrink",), "reducir_seleccion"), (("invert",), "invertir_seleccion"),
    (("select", "all"), "seleccionar_todo"), (("select",), "seleccionar"), (("selection",), "seleccionar"),
    (("convert",), "a_caras"), (("face",), "a_caras"), (("faces",), "a_caras"), (("facet",), "a_caras"),
    (("edge",), "a_aristas"), (("edges",), "a_aristas"), (("vertex",), "a_vertices"),
    (("vertices",), "a_vertices"), (("component",), "objeto_componente"), (("shell",), "a_isla"),
    (("save",), "guardar"), (("import",), "importar"), (("export",), "exportar"), (("open",), "abrir"),
    (("new", "scene"), "nueva"), (("reference",), "referencia"), (("undo",), "deshacer"), (("redo",), "rehacer"),
    (("repeat",), "repetir"), (("delete",), "papelera"), (("remove",), "papelera"), (("copy",), "copiar"),
    (("paste",), "pegar"), (("measure",), "medir"), (("distance",), "medir"), (("project",), "proyecto"),
    (("node",), "nodos"), (("nodes",), "nodos"), (("connection",), "nodos"), (("attribute",), "atributos"),
    (("attributes",), "atributos"), (("channel",), "canales"), (("script",), "script"),
    (("expression",), "codigo"), (("hotkey",), "atajos"), (("preferences",), "engranaje"),
    (("settings",), "engranaje"), (("options",), "engranaje"), (("plugin",), "plugin"),
    (("plug", "in"), "plugin"), (("shelf",), "estante"), (("help",), "ayuda"), (("tutorial",), "ayuda"),
    (("animation",), "animacion"), (("animate",), "animacion"), (("create",), "crear"),
    (("add",), "crear"), (("tool",), "herramienta"), (("window",), "ventana"), (("editor",), "ventana"),
]

# Categoría del Editor de atajos de Maya (``Menu items.Mesh Tools``) -> icono.
POR_CATEGORIA = [
    ("edit mesh", "extruir"), ("mesh tools", "corte_multiple"), ("mesh display", "normales"),
    ("mesh", "malla"), ("polygon", "malla"), ("modeling", "cubo"), ("uv", "uv"),
    ("animation", "animacion"), ("animate", "animacion"), ("key", "clave"), ("playback", "play"),
    ("constrain", "restriccion"), ("skeleton", "esqueleto"), ("rigging", "esqueleto"), ("skin", "vincular_piel"),
    ("deform", "deformador"), ("lighting", "luz"), ("shading", "material"), ("render", "render"),
    ("arnold", "render"), ("ncloth", "tela"), ("nparticles", "particulas"), ("particle", "particulas"),
    ("fluid", "fluido"), ("bifrost", "fluido"), ("fields", "viento"), ("solver", "simulacion"),
    ("dynamics", "simulacion"), ("fx", "efectos"), ("effects", "efectos"), ("xgen", "pelo"),
    ("hair", "pelo"), ("mash", "mash"), ("cache", "cache"), ("curves", "curva"), ("surfaces", "superficie"),
    ("generate", "pintar"), ("paint", "pintar"), ("select", "seleccionar"), ("display", "ojo"),
    ("panel", "panel"), ("view", "visor"), ("window", "ventana"), ("editor", "ventana"),
    ("file", "carpeta"), ("edit", "editar"), ("modify", "herramienta"), ("create", "crear"),
    ("tools", "herramienta"), ("help", "ayuda"), ("cameras", "camara"), ("camera", "camara"),
]

_PALABRAS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
_PREFIJOS = ("dR_", "dr_", "xg", "MASH", "mash")


def palabras(nombre):
    """``"PolyExtrudeFacet"`` -> ``["poly", "extrude", "facet"]``; ``"dR_quadDrawTool"`` -> ``["quad", "draw", "tool"]``."""
    if not nombre:
        return []
    nombre = nombre.replace("NURBS", "Nurbs").replace("UVs", "Uv").replace("UV", "Uv")
    if nombre.startswith("dR_"):
        nombre = nombre[3:]
    return [p.lower() for p in _PALABRAS.findall(nombre.replace("_", " "))]


def icono_de_comando(nombre, categoria=""):
    """Icono de línea para el comando de Maya ``nombre``, o "" si no se sabe cuál."""
    if not nombre:
        return ""
    if nombre in POR_COMANDO:
        return POR_COMANDO[nombre]
    lista = palabras(nombre)
    conjunto = set(lista)
    for necesarias, icono in REGLAS:
        if all(p in conjunto for p in necesarias):
            return icono
    if categoria:
        texto = categoria.lower().replace("›", " ").replace(".", " ")
        for clave, icono in POR_CATEGORIA:
            if clave in texto:
                return icono
    return ""


# En Python o MEL: «cmds.polyExtrudeFacet(...)», «mel.eval('CenterPivot')», «polyAutoProjection;»
_LLAMADA = re.compile(r"(?:cmds\.|pm\.|mc\.)?\b([A-Za-z_][A-Za-z0-9_]{2,})\s*(?:\(|;|\s+-|['\"]|$)", re.M)
_IGNORAR = {"import", "from", "as", "if", "not", "for", "in", "def", "return", "print", "eval", "mel", "cmds",
            "maya", "python", "source", "loadPlugin", "pluginInfo", "select", "ls", "str", "int", "len",
            "createLocator", "createNode", "shadingNode", "setAttr", "getAttr", "connectAttr", "listRelatives",
            "objExists", "warning", "error", "inViewMessage", "headsUpMessage", "range", "True", "False", "None"}


def icono_de_codigo(codigo):
    """Icono para un botón de Python o MEL según los comandos que llama, o ""."""
    if not codigo:
        return ""
    texto = codigo.replace("mel.eval(", " ")
    for linea in texto.splitlines():
        for comando in _LLAMADA.findall(linea.strip().strip("'\"")):
            if comando in _IGNORAR:
                continue
            icono = icono_de_comando(comando[:1].upper() + comando[1:]) or icono_de_comando(comando)
            if icono and icono not in ("crear", "herramienta", "ventana"):
                return icono
    return ""


def icono_de_boton(boton, categoria=""):
    """El icono de línea que se dibuja en un botón que no tiene uno elegido.

    Devuelve "" si no hay ninguno que encaje (entonces se dibuja la inicial).
    """
    boton = boton or {}
    tipo = boton.get("tipo", "")
    accion = boton.get("accion", "") or ""
    if tipo == "comando":
        return icono_de_comando(accion.strip(), categoria)
    if tipo in ("python", "mel"):
        return icono_de_codigo(accion)
    return ""
