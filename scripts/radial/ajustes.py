"""Ajustes del usuario: radial activo, forma, posición del menú y velocidad del doble Tab.

Se guardan en ``<preferencias de Maya>/radial/ajustes.json``. Este módulo no
depende de Maya; la carpeta se la pasa quien lo usa.
"""

import json
import os

from radial import detector_tab
from radial import radiales as rd

FORMAS = ("radial", "pill")

# Radial automático: qué radial va con cada workspace de Maya (se cambia en Ajustes).
REGLAS_POR_DEFECTO = {
    "ws:Modeling - Standard": "pre:1_modelado",
    "ws:Modeling - Expert": "pre:1_modelado",
    "ws:UV Editing": "pre:2_uv_texturas",
    "ws:Animation": "pre:3_animacion",
    "ws:Rendering": "pre:4_render_arnold",
}

_ARCHIVO = "ajustes.json"


def _fijable(leer):
    """Para una opción que el profesor puede fijar: si está en ``fijadas``, manda ese valor."""
    clave = leer.__name__

    def leer_o_fijada(self):
        fijadas = getattr(self, "fijadas", None) or {}
        return fijadas[clave] if clave in fijadas else leer(self)

    leer_o_fijada.__name__ = clave
    leer_o_fijada.__doc__ = leer.__doc__
    return leer_o_fijada


class Ajustes(object):
    def __init__(self, carpeta_preferencias):
        self.carpeta = carpeta_preferencias
        self.ruta = os.path.join(carpeta_preferencias, _ARCHIVO)
        self.datos = self._leer()
        # Opciones que fija el profesor desde la carpeta de clase (no se guardan: mandan mientras estén)
        self.fijadas = {}

    def fijar_opciones(self, opciones):
        """Pone las opciones que fija el profesor. Las del alumno no se tocan y vuelven al quitarlas."""
        prueba = Ajustes.__new__(Ajustes)
        prueba.datos, prueba.fijadas = dict(opciones or {}), {}
        self.fijadas = {clave: getattr(prueba, clave) for clave in (opciones or {})
                        if isinstance(getattr(Ajustes, clave, None), property)}

    def _leer(self):
        try:
            with open(self.ruta, encoding="utf-8") as f:
                datos = json.load(f)
            return datos if isinstance(datos, dict) else {}
        except (OSError, ValueError):
            return {}

    def guardar(self):
        os.makedirs(self.carpeta, exist_ok=True)
        temporal = self.ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(self.datos, f, ensure_ascii=False, indent=2)
        os.replace(temporal, self.ruta)

    # Velocidad del doble Tab
    @property
    @_fijable
    def ventana_ms(self):
        return detector_tab.limitar_ventana(self.datos.get("ventana_ms"))

    @ventana_ms.setter
    def ventana_ms(self, valor):
        self.datos["ventana_ms"] = detector_tab.limitar_ventana(valor)

    # Dónde se dejó el menú (centro, en coordenadas de pantalla)
    @property
    def posicion(self):
        valor = self.datos.get("posicion")
        if (isinstance(valor, list) and len(valor) == 2
                and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in valor)):
            return int(valor[0]), int(valor[1])
        return None

    @posicion.setter
    def posicion(self, valor):
        if valor is None:
            self.datos.pop("posicion", None)
        else:
            self.datos["posicion"] = [int(valor[0]), int(valor[1])]

    # Radial activo: «pre:<id>» para uno preconfigurado
    @property
    def radial_activo(self):
        valor = self.datos.get("radial_activo")
        return valor if isinstance(valor, str) and valor else None

    @radial_activo.setter
    def radial_activo(self, valor):
        self.datos["radial_activo"] = valor

    # Forma del menú: «radial» (anillo de puntos) o «pill» (cápsula)
    @property
    @_fijable
    def forma(self):
        valor = self.datos.get("forma")
        return valor if valor in FORMAS else FORMAS[0]

    @forma.setter
    def forma(self, valor):
        self.datos["forma"] = valor if valor in FORMAS else FORMAS[0]

    @property
    @_fijable
    def pill_vertical(self):
        return self.datos.get("pill_vertical") is True

    @pill_vertical.setter
    def pill_vertical(self, valor):
        self.datos["pill_vertical"] = bool(valor)

    # Copia de trabajo del radial activo, con los cambios aún sin guardar
    @property
    def radial_actual(self):
        try:
            return rd.normalizar(self.datos.get("radial_actual"))
        except rd.RadialNoValido:
            return None

    @radial_actual.setter
    def radial_actual(self, radial):
        if radial is None:
            self.datos.pop("radial_actual", None)
        else:
            self.datos["radial_actual"] = rd.normalizar(radial)

    @property
    def sin_guardar(self):
        return self.datos.get("sin_guardar") is True

    @sin_guardar.setter
    def sin_guardar(self, valor):
        self.datos["sin_guardar"] = bool(valor)

    # Buscador de acciones bajo el menú
    @property
    @_fijable
    def buscador(self):
        return self.datos.get("buscador") is not False

    @buscador.setter
    def buscador(self, valor):
        self.datos["buscador"] = bool(valor)

    @property
    def recientes(self):
        valor = self.datos.get("recientes")
        if not isinstance(valor, list):
            return []
        return [a for a in valor if isinstance(a, dict) and isinstance(a.get("boton"), dict)
                and isinstance(a.get("texto"), str)]

    @recientes.setter
    def recientes(self, valor):
        self.datos["recientes"] = list(valor)

    @property
    def favoritos(self):
        """Acciones del buscador marcadas con estrella (mismo formato que ``recientes``)."""
        valor = self.datos.get("favoritos")
        if not isinstance(valor, list):
            return []
        return [a for a in valor if isinstance(a, dict) and isinstance(a.get("boton"), dict)
                and isinstance(a.get("texto"), str)]

    @favoritos.setter
    def favoritos(self, valor):
        self.datos["favoritos"] = list(valor)

    # Carpeta de clase: radiales que comparte el profesor (también con RADIAL_CLASE)
    @property
    def carpeta_clase(self):
        valor = self.datos.get("carpeta_clase")
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
        return os.environ.get("RADIAL_CLASE", "").strip()

    @carpeta_clase.setter
    def carpeta_clase(self, valor):
        if valor:
            self.datos["carpeta_clase"] = str(valor)
        else:
            self.datos.pop("carpeta_clase", None)

    # Opciones que se activan en Ajustes
    @property
    @_fijable
    def carpetas(self):
        return self.datos.get("carpetas") is True

    @carpetas.setter
    def carpetas(self, valor):
        self.datos["carpetas"] = bool(valor)

    @property
    @_fijable
    def automatico(self):
        return self.datos.get("automatico") is True

    @automatico.setter
    def automatico(self, valor):
        self.datos["automatico"] = bool(valor)

    @property
    def reglas(self):
        """Radial automático: ``{"ws:<workspace>" o "sel:<modo>": identificador}``."""
        valor = self.datos.get("reglas")
        if not isinstance(valor, dict):
            return dict(REGLAS_POR_DEFECTO)
        return {k: v for k, v in valor.items() if isinstance(k, str) and isinstance(v, str) and v}

    @reglas.setter
    def reglas(self, valor):
        self.datos["reglas"] = dict(valor)

    @property
    def atajo(self):
        """Atajo de teclado opcional para el menú («Ctrl+Alt+R»), o ""."""
        valor = self.datos.get("atajo")
        return valor if isinstance(valor, str) else ""

    @atajo.setter
    def atajo(self, valor):
        self.datos["atajo"] = valor or ""

    @property
    @_fijable
    def aprendizaje(self):
        return self.datos.get("aprendizaje") is not False

    @aprendizaje.setter
    def aprendizaje(self, valor):
        self.datos["aprendizaje"] = bool(valor)


class AjustesExtra(object):
    """Los ajustes de la pill extra: otra pill flotante, independiente del menú del doble Tab.

    Tiene su propio radial (botones, tamaño y opacidad), su orientación y su sitio. Se guarda dentro
    de ``ajustes.json`` en ``"extra"``. Ofrece lo mismo que ``Ajustes`` necesita ``Biblioteca``.
    """

    def __init__(self, ajustes):
        self.base = ajustes

    @property
    def datos(self):
        extra = self.base.datos.get("extra")
        if not isinstance(extra, dict):
            extra = self.base.datos["extra"] = {}
        return extra

    def guardar(self):
        self.base.guardar()

    @property
    def carpeta_clase(self):
        return self.base.carpeta_clase

    @property
    def activa(self):
        return self.datos.get("activa") is True

    @activa.setter
    def activa(self, valor):
        self.datos["activa"] = bool(valor)

    @property
    def vertical(self):
        return self.datos.get("vertical") is True

    @vertical.setter
    def vertical(self, valor):
        self.datos["vertical"] = bool(valor)

    posicion = Ajustes.posicion
    radial_activo = Ajustes.radial_activo
    radial_actual = Ajustes.radial_actual
    sin_guardar = Ajustes.sin_guardar
