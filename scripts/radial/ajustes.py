"""Ajustes del usuario: radial activo, posición del menú y velocidad del doble Tab.

Se guardan en ``<preferencias de Maya>/radial/ajustes.json``. Este módulo no
depende de Maya; la carpeta se la pasa quien lo usa.
"""

import json
import os

from radial import detector_tab

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
