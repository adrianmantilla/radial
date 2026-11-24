"""El radial activo y la biblioteca de radiales (preconfigurados y propios).

El radial activo se identifica como ``pre:<id>`` (viene con el plugin),
``clase:<id>`` (de la carpeta de clase que comparte el profesor) o ``mio:<id>``
(archivo del usuario). Mientras se edita, la copia de trabajo se
guarda en los ajustes, así los cambios no se pierden al cerrar Maya aunque
todavía no se hayan guardado en el archivo. Los preconfigurados, los de clase y
los bloqueados no se sobrescriben nunca: sus cambios se guardan como radial nuevo.

No depende de Maya.
"""

import os

from radial import radiales as rd

PRE = "pre:"
MIO = "mio:"
CLASE = "clase:"


class Biblioteca(object):
    def __init__(self, ajustes, carpeta_mios):
        self.ajustes = ajustes
        self.carpeta = carpeta_mios
        self._activo = None

    # --- Consultas ----------------------------------------------------------

    @property
    def origen(self):
        """Identificador del radial activo, siempre uno que existe."""
        valor = self.ajustes.radial_activo
        if valor and self._ruta(valor):
            return valor
        pre = rd.preconfigurados()
        return PRE + pre[0][0] if pre else None

    @property
    def carpeta_clase(self):
        return self.ajustes.carpeta_clase

    @property
    def es_preconfigurado(self):
        """True si el radial activo no se puede sobrescribir (preconfigurado, de clase o bloqueado)."""
        origen = self.origen
        return (origen is None or origen.startswith(PRE) or origen.startswith(CLASE)
                or bool(self.activo.get("bloqueado")))

    @property
    def es_de_clase(self):
        origen = self.origen
        return bool(origen) and origen.startswith(CLASE)

    @property
    def sin_guardar(self):
        return self.ajustes.sin_guardar

    @property
    def activo(self):
        if self._activo is None:
            actual = self.ajustes.radial_actual
            if actual is not None and self.ajustes.radial_activo == self.origen:
                self._activo = actual
            else:
                self._activo = self._leer_origen()
        return self._activo

    def _ruta(self, identificador):
        if identificador.startswith(PRE):
            nombre = identificador[len(PRE):]
            return next((r for n, r in rd.preconfigurados() if n == nombre), None)
        if identificador.startswith(MIO):
            ruta = os.path.join(self.carpeta, identificador[len(MIO):] + rd.EXTENSION)
            return ruta if os.path.isfile(ruta) else None
        if identificador.startswith(CLASE) and self.carpeta_clase:
            ruta = os.path.join(self.carpeta_clase, identificador[len(CLASE):] + rd.EXTENSION)
            return ruta if os.path.isfile(ruta) else None
        return None

    def _leer_origen(self):
        origen = self.origen
        if origen:
            try:
                return rd.leer(self._ruta(origen))
            except rd.RadialNoValido:
                pass
        return rd.por_defecto()

    def preconfigurados(self):
        resultado = []
        for nombre, ruta in rd.preconfigurados():
            try:
                resultado.append((PRE + nombre, rd.leer(ruta)["nombre"]))
            except rd.RadialNoValido:
                continue
        return resultado

    def mios(self):
        return [(MIO + i, nombre) for i, _, nombre in rd.mios(self.carpeta)]

    def de_clase(self):
        """Radiales de la carpeta de clase: lista de (identificador, nombre, bloqueado)."""
        if not self.carpeta_clase:
            return []
        resultado = []
        for i, ruta, nombre in rd.mios(self.carpeta_clase):
            try:
                bloqueado = bool(rd.leer(ruta).get("bloqueado"))
            except rd.RadialNoValido:
                continue
            resultado.append((CLASE + i, nombre, bloqueado))
        return resultado

    def nombre_de(self, identificador):
        for i, nombre in self.preconfigurados() + self.mios() + [(c[0], c[1]) for c in self.de_clase()]:
            if i == identificador:
                return nombre
        return None

    # --- Cambios ------------------------------------------------------------

    def _fijar(self, identificador, radial, sin_guardar=False):
        self._activo = rd.normalizar(radial)
        self.ajustes.radial_activo = identificador
        self.ajustes.radial_actual = self._activo
        self.ajustes.sin_guardar = sin_guardar
        self.ajustes.guardar()
        return self._activo

    def usar(self, identificador):
        """Activa otro radial. Los cambios sin guardar del anterior se descartan."""
        ruta = self._ruta(identificador)
        if ruta is None:
            raise rd.RadialNoValido("no existe {}".format(identificador))
        return self._fijar(identificador, rd.leer(ruta))

    def modificar(self, radial):
        """Cambia la copia de trabajo (botones o apariencia) sin tocar el archivo."""
        return self._fijar(self.origen, radial, sin_guardar=True)

    def restaurar(self):
        """Descarta los cambios sin guardar."""
        return self._fijar(self.origen, self._leer_origen())

    def refrescar_clase(self):
        """Si el activo es de clase y no tiene cambios, lo vuelve a leer (el profesor pudo cambiarlo).

        Devuelve True si cambió."""
        if not self.es_de_clase or self.sin_guardar:
            return False
        nuevo = self._leer_origen()
        if nuevo == self.activo:
            return False
        self._fijar(self.origen, nuevo)
        return True

    def guardar_cambios(self):
        """Escribe la copia de trabajo en su archivo. False si es un preconfigurado."""
        if self.es_preconfigurado:
            return False
        radial = rd.normalizar(self.activo)
        radial["nombre"] = rd.leer(self._ruta(self.origen))["nombre"]
        rd.escribir(radial, self._ruta(self.origen))
        self._fijar(self.origen, radial)
        return True

    def guardar_como(self, nombre):
        """Guarda la copia de trabajo como radial propio nuevo (ya sin bloquear) y lo activa."""
        copia = dict(self.activo)
        copia.pop("bloqueado", None)
        identificador, _, radial = rd.guardar_nuevo(copia, self.carpeta, nombre)
        return self._fijar(MIO + identificador, radial)

    def importar(self, ruta):
        identificador, _, radial = rd.importar(ruta, self.carpeta)
        return self._fijar(MIO + identificador, radial)

    def exportar(self, ruta, identificador=None, bloqueado=False):
        """Escribe el radial activo (o ``identificador``) en ``ruta``.

        Con ``bloqueado``, los alumnos lo usan pero no lo editan (hacen una copia)."""
        if identificador is None or identificador == self.origen:
            radial = dict(self.activo)
        else:
            radial = rd.leer(self._ruta(identificador))
        if bloqueado:
            radial["bloqueado"] = True
        if not ruta.endswith(rd.EXTENSION):
            ruta += rd.EXTENSION
        return rd.escribir(radial, ruta)

    def renombrar(self, identificador, nombre):
        if not identificador.startswith(MIO):
            raise rd.RadialNoValido("solo se renombran los radiales propios")
        era_activo = identificador == self.origen
        nuevo, _ = rd.renombrar(self._ruta(identificador), nombre, self.carpeta)
        if era_activo:
            radial = rd.normalizar(self.activo)
            radial["nombre"] = self.nombre_de(MIO + nuevo)
            self._fijar(MIO + nuevo, radial, self.sin_guardar)
        return MIO + nuevo

    def duplicar(self, identificador):
        radial = rd.leer(self._ruta(identificador))
        radial.pop("bloqueado", None)
        nuevo, _, _ = rd.guardar_nuevo(radial, self.carpeta, radial["nombre"])
        return MIO + nuevo

    def borrar(self, identificador):
        """Borra un radial propio. Si era el activo, se pasa al primer preconfigurado."""
        if not identificador.startswith(MIO):
            raise rd.RadialNoValido("los preconfigurados no se borran")
        ruta = self._ruta(identificador)
        era_activo = identificador == self.ajustes.radial_activo
        if ruta:
            os.remove(ruta)
        if era_activo:
            pre = rd.preconfigurados()
            if pre:
                self.usar(PRE + pre[0][0])
            else:
                self._fijar(None, rd.por_defecto())
