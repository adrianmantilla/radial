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
      "apariencia": {"radio": 84, "punto": 5, "abierto": 21, "opacidad": 1.0,
                     "pill_boton": 32}
    }

``tipo`` puede ser ``comando`` (comando de Maya, el mismo nombre que usa el
Editor de atajos), ``python``, ``mel`` o ``vacio``. Este módulo no depende de
Maya; lee, comprueba y calcula la geometría del menú.
"""

import json
import math
import os
import re
import unicodedata

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
    "pill_boton": (24, 44, 32),  # tamaño de los botones en la forma pill
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


# --- Forma pill ---------------------------------------------------------------
# La pill es una cápsula con un agarre, una raya y los seis botones en fila.

PILL_MARGEN = 5
PILL_AGARRE = 22
PILL_SEPARACION = 4
PILL_RAYA = 9


def geometria_pill(apariencia, vertical=False):
    """Tamaño de la cápsula y rectángulos (x, y, ancho, alto) del agarre y los botones.

    Devuelve ``(ancho, alto, agarre, [botones])`` con el origen en la esquina.
    """
    b = int(round(apariencia["pill_boton"]))
    largo = PILL_MARGEN * 2 + PILL_AGARRE + PILL_RAYA + NUM_BOTONES * b + (NUM_BOTONES - 1) * PILL_SEPARACION
    grueso = b + PILL_MARGEN * 2
    botones = []
    pos = PILL_MARGEN + PILL_AGARRE + PILL_RAYA
    for _ in range(NUM_BOTONES):
        botones.append((pos, PILL_MARGEN, b, b))
        pos += b + PILL_SEPARACION
    agarre = (PILL_MARGEN, PILL_MARGEN, PILL_AGARRE, b)
    if vertical:
        botones = [(y, x, h, w) for (x, y, w, h) in botones]
        agarre = (agarre[1], agarre[0], agarre[3], agarre[2])
        return grueso, largo, agarre, botones
    return largo, grueso, agarre, botones


def que_hay_en_pill(x, y, apariencia, vertical=False):
    """Índice de botón, ``"centro"`` (el agarre) o None, con el origen en la esquina."""
    _, _, agarre, botones = geometria_pill(apariencia, vertical)
    for i, (bx, by, bw, bh) in enumerate(botones):
        if math.hypot(x - (bx + bw / 2.0), y - (by + bh / 2.0)) <= bw / 2.0 + 1:
            return i
    ax, ay, aw, ah = agarre
    if ax <= x <= ax + aw and ay <= y <= ay + ah:
        return "centro"
    return None


# --- Radiales del usuario ---------------------------------------------------
# Cada radial propio es un archivo .radial en la carpeta del usuario. El nombre
# del archivo sale del nombre del radial, sin acentos ni símbolos.

def nombre_de_archivo(nombre):
    texto = unicodedata.normalize("NFKD", nombre or "").encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_").lower()
    return (texto or "radial")[:60]


def ruta_libre(carpeta, nombre):
    """Ruta nueva en ``carpeta`` para un radial llamado ``nombre`` (sin pisar otro)."""
    base = nombre_de_archivo(nombre)
    ruta = os.path.join(carpeta, base + EXTENSION)
    n = 2
    while os.path.exists(ruta):
        ruta = os.path.join(carpeta, "{}_{}{}".format(base, n, EXTENSION))
        n += 1
    return ruta


def mios(carpeta):
    """Radiales del usuario: lista de (identificador, ruta, nombre) ordenada por nombre."""
    try:
        archivos = [n for n in os.listdir(carpeta) if n.endswith(EXTENSION)]
    except OSError:
        return []
    resultado = []
    for archivo in archivos:
        ruta = os.path.join(carpeta, archivo)
        try:
            nombre = leer(ruta)["nombre"]
        except RadialNoValido:
            continue
        resultado.append((archivo[:-len(EXTENSION)], ruta, nombre))
    return sorted(resultado, key=lambda r: (r[2].lower(), r[0]))


def nombres_usados(carpeta):
    return {nombre.lower() for _, _, nombre in mios(carpeta)}


def nombre_libre(carpeta, nombre):
    """``nombre`` o, si ya hay un radial propio con ese nombre, «nombre 2», «nombre 3»..."""
    nombre = (nombre or "").strip() or "Radial"
    usados = nombres_usados(carpeta)
    if nombre.lower() not in usados:
        return nombre
    n = 2
    while "{} {}".format(nombre, n).lower() in usados:
        n += 1
    return "{} {}".format(nombre, n)


def guardar_nuevo(radial, carpeta, nombre=None):
    """Guarda una copia de ``radial`` como radial propio. Devuelve (identificador, ruta, radial)."""
    radial = normalizar(radial)
    radial["nombre"] = nombre_libre(carpeta, nombre or radial["nombre"])
    ruta = ruta_libre(carpeta, radial["nombre"])
    escribir(radial, ruta)
    return os.path.basename(ruta)[:-len(EXTENSION)], ruta, radial


def importar(ruta_origen, carpeta):
    """Copia un archivo .radial a los radiales propios. Lanza RadialNoValido si no lo es."""
    return guardar_nuevo(leer(ruta_origen), carpeta)


def renombrar(ruta, nuevo_nombre, carpeta):
    """Cambia el nombre de un radial propio (y su archivo). Devuelve (identificador, ruta)."""
    radial = leer(ruta)
    nuevo_nombre = (nuevo_nombre or "").strip()
    if not nuevo_nombre:
        raise RadialNoValido("nombre vacío")
    if nuevo_nombre.lower() != radial["nombre"].lower():
        nuevo_nombre = nombre_libre(carpeta, nuevo_nombre)
    radial["nombre"] = nuevo_nombre
    nueva = ruta
    if nombre_de_archivo(nuevo_nombre) != nombre_de_archivo(os.path.basename(ruta)[:-len(EXTENSION)]):
        nueva = ruta_libre(carpeta, nuevo_nombre)
    escribir(radial, nueva)
    if os.path.normcase(os.path.abspath(nueva)) != os.path.normcase(os.path.abspath(ruta)):
        os.remove(ruta)
    return os.path.basename(nueva)[:-len(EXTENSION)], nueva
