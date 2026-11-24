"""Colores y dibujo compartidos por el radial, la pill y las ventanas del plugin."""

from radial import iconos
from radial.qt import QtCore, QtGui, QtSvg

Qt = QtCore.Qt

COLOR_PUNTO = QtGui.QColor(16, 17, 19, 178)
COLOR_FONDO = QtGui.QColor(16, 17, 19, 158)
COLOR_ABIERTO = QtGui.QColor(244, 244, 244, 255)
COLOR_BORDE = QtGui.QColor(255, 255, 255, 72)
COLOR_BORDE_FONDO = QtGui.QColor(255, 255, 255, 36)
COLOR_LINEA = QtGui.QColor(255, 255, 255, 46)
COLOR_CENTRO = QtGui.QColor(16, 17, 19, 170)
COLOR_AGARRE = QtGui.QColor(255, 255, 255, 95)
COLOR_AGARRE_SOBRE = QtGui.QColor(255, 255, 255, 200)
COLOR_TEXTO = QtGui.QColor(242, 242, 242)
COLOR_DETALLE = QtGui.QColor(196, 196, 196)
COLOR_SOMBRA = QtGui.QColor(0, 0, 0, 150)
COLOR_ICONO_CLARO = "#ececec"
COLOR_ICONO_OSCURO = "#141414"


def mezclar(a, b, t):
    return QtGui.QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def pixmap_icono(icono, tamano, escala=1.0, color=COLOR_ICONO_OSCURO):
    """QPixmap de un icono de línea, un icono de Maya o un archivo. None si no hay icono."""
    lado = max(1, int(round(tamano * escala)))
    mapa = None
    datos = iconos.svg(icono, color)
    if datos is not None and QtSvg is not None:
        mapa = QtGui.QPixmap(lado, lado)
        mapa.fill(Qt.transparent)
        pintor = QtGui.QPainter(mapa)
        pintor.setRenderHint(QtGui.QPainter.Antialiasing)
        QtSvg.QSvgRenderer(QtCore.QByteArray(datos)).render(pintor)
        pintor.end()
    elif iconos.es_imagen(icono):
        imagen = QtGui.QPixmap(icono)
        if not imagen.isNull():
            mapa = imagen.scaled(lado, lado, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    if mapa is not None:
        mapa.setDevicePixelRatio(escala)
    return mapa


def qicono(icono, tamano=20, color=COLOR_ICONO_CLARO):
    """QIcon para listas y botones de las ventanas (iconos de línea en claro)."""
    mapa = pixmap_icono(icono, tamano, 2.0, color)
    return QtGui.QIcon(mapa) if mapa is not None else QtGui.QIcon()


def dibujar_icono_boton(pintor, boton, centro, radio, opacidad, cache, escala):
    """Dibuja el icono del botón (o su inicial) dentro del círculo blanco."""
    tamano = min(22.0, radio * 1.25)
    clave = (boton["icono"], escala)
    if clave not in cache:
        cache[clave] = pixmap_icono(boton["icono"], 22.0, escala)
    mapa = cache[clave]
    x, y = centro
    pintor.save()
    pintor.setOpacity(opacidad)
    if mapa is not None:
        rect = QtCore.QRectF(x - tamano / 2, y - tamano / 2, tamano, tamano)
        pintor.drawPixmap(rect, mapa, QtCore.QRectF(mapa.rect()))
    elif boton["texto"]:
        fuente = QtGui.QFont(pintor.font())
        fuente.setPixelSize(max(8, int(radio * 0.9)))
        fuente.setBold(True)
        pintor.setFont(fuente)
        pintor.setPen(QtGui.QColor(20, 20, 20))
        pintor.drawText(QtCore.QRectF(x - radio, y - radio, 2 * radio, 2 * radio), Qt.AlignCenter,
                        boton["texto"][:1].upper())
    pintor.restore()


def dibujar_texto(pintor, texto, rect, color, negrita=False, tamano=12):
    """Texto centrado con una sombra suave para leerse sobre modelos claros y oscuros."""
    if not texto:
        return
    fuente = QtGui.QFont(pintor.font())
    fuente.setPixelSize(tamano)
    fuente.setBold(negrita)
    pintor.setFont(fuente)
    texto = QtGui.QFontMetrics(fuente).elidedText(texto, Qt.ElideRight, int(rect.width()))
    pintor.setPen(COLOR_SOMBRA)
    pintor.drawText(rect.translated(0, 1), Qt.AlignCenter, texto)
    pintor.setPen(color)
    pintor.drawText(rect, Qt.AlignCenter, texto)
