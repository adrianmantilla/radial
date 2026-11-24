"""Radiales: un juego de seis botones más su apariencia, guardado como JSON.

Un archivo ``.radial`` tiene esta forma::

    {
      "formato": 1,
      "nombre": "Modelado",
      "botones": [
        {"texto": "Duplicar", "detalle": "especial", "icono": "duplicar",
         "tipo": "comando", "accion": "DuplicateSpecialOptions"},
        ...  (seis en total)
      ],
      "apariencia": {"radio": 84, "punto": 5, "abierto": 21, "opacidad": 1.0}
    }

``tipo`` puede ser ``comando`` (comando de Maya, el mismo nombre que usa el
Editor de atajos), ``python``, ``mel`` o ``vacio``. Este módulo no depende de
Maya; lee, comprueba y calcula la geometría del menú.
"""

import json
import math
import os

FORMATO = 1
NUM_BOTONES = 6
EXTENSION = ".radial"
TIPOS = ("comando", "python", "mel", "vacio")
CARPETA_PRECONFIGURADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preconfigurados")

# Rango de cada valor de apariencia: (mínimo, máximo, por defecto)
APARIENCIA = {
    "radio": (50, 140, 84),
    "punto": (3.0, 9.0, 5.0),
    "abierto": (15, 30, 21),
    "opacidad": (0.4, 1.0, 1.0),
}
RADIO_CENTRO = 15  # el círculo del centro, desde donde se arrastra


class RadialNoValido(ValueError):
    pass


def boton_vacio():
    return {"texto": "", "detalle": "", "icono": "", "tipo": "vacio", "accion": ""}


def _limitar(valor, minimo, maximo, defecto):
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return defecto
    if math.isnan(valor):
        return defecto
    return max(minimo, min(maximo, valor))


def normalizar_apariencia(datos):
    datos = datos if isinstance(datos, dict) else {}
    return {clave: _limitar(datos.get(clave), *rango) for clave, rango in APARIENCIA.items()}


def normalizar_boton(datos):
    if not isinstance(datos, dict):
        return boton_vacio()
    boton = boton_vacio()
    for clave in ("texto", "detalle", "icono", "accion"):
        valor = datos.get(clave, "")
        boton[clave] = valor if isinstance(valor, str) else ""
    tipo = datos.get("tipo")
    boton["tipo"] = tipo if tipo in TIPOS else "vacio"
    if boton["tipo"] != "vacio" and not boton["accion"].strip():
        boton["tipo"] = "vacio"
    return boton


def normalizar(datos):
    """Devuelve un radial completo y válido a partir de ``datos``.

    Lanza ``RadialNoValido`` si no parece un radial. Lo demás se corrige:
    faltan botones → se rellenan vacíos; sobran → se descartan; valores
    fuera de rango → se ajustan.
    """
    if not isinstance(datos, dict) or not isinstance(datos.get("botones"), list):
        raise RadialNoValido("no tiene lista de botones")
    if datos.get("formato", FORMATO) > FORMATO:
        raise RadialNoValido("formato más nuevo que esta versión del plugin")
    botones = [normalizar_boton(b) for b in datos["botones"][:NUM_BOTONES]]
    botones += [boton_vacio() for _ in range(NUM_BOTONES - len(botones))]
    nombre = datos.get("nombre")
    return {
        "formato": FORMATO,
        "nombre": nombre.strip() if isinstance(nombre, str) and nombre.strip() else "Radial",
        "botones": botones,
        "apariencia": normalizar_apariencia(datos.get("apariencia")),
    }


def leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError) as error:
        raise RadialNoValido(str(error))
    return normalizar(datos)


def escribir(radial, ruta):
    radial = normalizar(radial)
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    temporal = ruta + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(radial, f, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta)
    return ruta


def preconfigurados():
    """Lista de (identificador, ruta) de los radiales que vienen con el plugin, en orden."""
    try:
        nombres = sorted(n for n in os.listdir(CARPETA_PRECONFIGURADOS) if n.endswith(EXTENSION))
    except OSError:
        return []
    return [(n[:-len(EXTENSION)], os.path.join(CARPETA_PRECONFIGURADOS, n)) for n in nombres]


def por_defecto():
    """El primer radial preconfigurado o, si faltara, uno con seis botones vacíos."""
    for _, ruta in preconfigurados():
        try:
            return leer(ruta)
        except RadialNoValido:
            continue
    return normalizar({"nombre": "Radial", "botones": []})


# --- Geometría --------------------------------------------------------------
# Coordenadas con el origen en el centro del menú y la y hacia abajo (como en
# pantalla). El botón 1 está arriba y los demás siguen el sentido del reloj.

def posiciones(radio, n=NUM_BOTONES):
    resultado = []
    for i in range(n):
        angulo = math.radians(-90 + i * 360.0 / n)
        resultado.append((radio * math.cos(angulo), radio * math.sin(angulo)))
    return resultado


def lado_ventana(apariencia):
    """Ancho (= alto) de la ventana que contiene el menú."""
    return int(math.ceil(2 * (apariencia["radio"] + apariencia["abierto"] + 6)))


def que_hay_en(x, y, apariencia):
    """Qué hay bajo el punto (x, y): un índice de botón, ``"centro"`` o None."""
    for i, (bx, by) in enumerate(posiciones(apariencia["radio"])):
        if math.hypot(x - bx, y - by) <= apariencia["abierto"] + 2:
            return i
    if math.hypot(x, y) <= RADIO_CENTRO + 4:
        return "centro"
    return None
