"""Decide cuándo dos pulsaciones de Tab cuentan como «doble Tab».

No depende de Maya ni de Qt para poder probarlo fuera. El filtro de teclado
(``filtro_teclado.py``) le pasa el momento de cada Tab y si en ese momento el
Tab puede contar (por ejemplo, no cuenta si se está escribiendo en un campo).
"""

VENTANA_MINIMA_MS = 150
VENTANA_MAXIMA_MS = 400
VENTANA_POR_DEFECTO_MS = 250


def limitar_ventana(ms):
    """Ajusta ``ms`` al rango permitido; si no es un número, usa el valor por defecto."""
    try:
        ms = int(ms)
    except (TypeError, ValueError):
        return VENTANA_POR_DEFECTO_MS
    return max(VENTANA_MINIMA_MS, min(VENTANA_MAXIMA_MS, ms))


class DetectorDobleTab(object):
    """Recuerda el último Tab y dice si el siguiente llega a tiempo.

    El primer Tab siempre se deja pasar a Maya. Solo el segundo, si llega
    dentro de la ventana, activa el menú (y el filtro se lo queda).
    """

    def __init__(self, ventana_ms=VENTANA_POR_DEFECTO_MS):
        self.ventana_ms = limitar_ventana(ventana_ms)
        self._ultimo = None

    def olvidar(self):
        """Otra tecla, un clic o un Tab que no cuenta rompen la secuencia."""
        self._ultimo = None

    def esperando(self, momento_ms):
        """True si un Tab en ``momento_ms`` completaría un doble Tab."""
        return self._ultimo is not None and 0 <= momento_ms - self._ultimo <= self.ventana_ms

    def pulsar(self, momento_ms, cuenta=True):
        """Registra un Tab en ``momento_ms``. Devuelve True si completa un doble Tab."""
        if not cuenta:
            self.olvidar()
            return False
        completa = self.esperando(momento_ms)
        self._ultimo = momento_ms
        if completa:
            # Tras un doble Tab se empieza de cero: un tercer Tab rápido es un primer Tab.
            self._ultimo = None
            return True
        return False
