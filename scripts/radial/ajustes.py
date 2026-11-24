"""Ajustes del usuario: radial activo, forma, posición del menú y velocidad del doble Tab.

Se guardan en ``<preferencias de Maya>/radial/ajustes.json``. Este módulo no
depende de Maya; la carpeta se la pasa quien lo usa.
"""

import json
import os

from radial import detector_tab
from radial import radiales as rd

FORMAS = ("radial", "pill")

_ARCHIVO = "ajustes.json"


class Ajustes(object):
    def __init__(self, carpeta_preferencias):
        self.carpeta = carpeta_preferencias
        self.ruta = os.path.join(carpeta_preferencias, _ARCHIVO)
        self.datos = self._leer()

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
    def forma(self):
        valor = self.datos.get("forma")
        return valor if valor in FORMAS else FORMAS[0]

    @forma.setter
    def forma(self, valor):
        self.datos["forma"] = valor if valor in FORMAS else FORMAS[0]

    @property
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
