"""Pill extra: otra pill flotante, independiente del menú del doble Tab.

Se activa en Ajustes (o en el menú Radial) y queda siempre a la vista mientras
está activa: no se abre ni se cierra con el doble Tab. Tiene su propio radial
(botones, iconos, carpetas, interruptores, tamaño y opacidad), su orientación
y su sitio. Se configura igual que el menú principal: clic derecho en los
puntitos del extremo abre el configurador.
"""

from maya import cmds

from radial import ajustes as aj
from radial import radiales as rd
from radial.biblioteca import Biblioteca
from radial.i18n import t
from radial.qt import QtCore, QtGui, destruir, sigue_vivo

MENU_ACTIVA = "RadialMenuPillExtra"

_estado = {"ajustes": None, "biblioteca": None, "pill": None, "configurador": None}


def _im():
    from radial import interfaz_maya
    return interfaz_maya


def ajustes():
    base = _im().ajustes()
    if _estado["ajustes"] is None or _estado["ajustes"].base is not base:
        _estado["ajustes"] = aj.AjustesExtra(base)
        _estado["biblioteca"] = None
    return _estado["ajustes"]


def biblioteca():
    extra = ajustes()
    if _estado["biblioteca"] is None:
        _estado["biblioteca"] = Biblioteca(extra, _im().carpeta_mios())
    return _estado["biblioteca"]


def nombre():
    bib = biblioteca()
    return bib.nombre_de(bib.origen) or bib.activo["nombre"]


def _vivo(clave):
    objeto = _estado[clave]
    return objeto if sigue_vivo(objeto) else None


# --- La pill --------------------------------------------------------------------

def pill(crear=True):
    menu = _vivo("pill")
    if menu is None and crear:
        from radial.menu_pill import MenuPill
        menu = MenuPill(_im().ventana_maya(), al_ejecutar=_al_ejecutar, al_mover=_al_mover,
                        al_configurar=abrir_configurador, vertical=ajustes().vertical)
        menu.setObjectName("RadialPillExtra")
        menu.usar_radial(biblioteca().activo)
        menu.al_soltar = _al_soltar
        menu.tiene_opciones = _im()._tiene_opciones
        menu.al_carpeta = lambda carpeta: actualizar_estados()
        menu.al_sobre = lambda boton: _im()._al_sobre(boton, menu)
        _estado["pill"] = menu
    return menu


def visible():
    menu = pill(crear=False)
    return bool(menu and menu.isVisible())


def _centro_inicial(menu):
    """Donde se dejó; si no, arriba en el centro de la ventana de Maya."""
    guardada = ajustes().posicion
    if guardada is not None and QtGui.QGuiApplication.screenAt(QtCore.QPoint(*guardada)) is not None:
        return QtCore.QPoint(*guardada)
    principal = _im().ventana_maya()
    if principal is not None and principal.isVisible():
        zona = principal.frameGeometry()
        return QtCore.QPoint(zona.center().x(), zona.top() + 90 + menu.height() // 2)
    pantalla = QtGui.QGuiApplication.primaryScreen()
    zona = pantalla.availableGeometry()
    return QtCore.QPoint(zona.center().x(), zona.top() + 90)


def mostrar():
    menu = pill()
    menu.colocar(_im()._ajustar_a_pantalla(_centro_inicial(menu), menu))
    menu.show()
    menu.raise_()
    actualizar_estados()


def ocultar():
    menu = pill(crear=False)
    if menu:
        menu.hide()


def activar(activa):
    """Muestra (y recuerda) u oculta la pill extra."""
    ajustes().activa = bool(activa)
    ajustes().guardar()
    if activa:
        mostrar()
    else:
        ocultar()
    if cmds.menuItem(MENU_ACTIVA, exists=True):
        cmds.menuItem(MENU_ACTIVA, edit=True, checkBox=bool(activa))


def cambiar_vertical(vertical):
    ajustes().vertical = bool(vertical)
    ajustes().guardar()
    menu = pill(crear=False)
    if menu:
        menu.usar_radial(biblioteca().activo, vertical=bool(vertical))


def volver_a_centrar():
    ajustes().posicion = None
    ajustes().guardar()
    if visible():
        mostrar()


def actualizar_estados():
    menu = pill(crear=False)
    if not menu or not menu.isVisible():
        return
    from radial import acciones
    menu.fijar_estados([acciones.estado(b) for b in menu.botones_visibles()])


def _al_ejecutar(indice, opciones=False):
    from radial import acciones
    menu = pill(crear=False)
    botones = menu.botones_visibles() if menu else biblioteca().activo["botones"]
    acciones.ejecutar(botones[indice], opciones=opciones)
    _im()._actualizar_estados()  # también pone al día esta pill


def _al_mover(centro):
    ajustes().posicion = (centro.x(), centro.y())
    ajustes().guardar()


def _al_soltar(indice, boton):
    """Una acción del buscador soltada en un botón de la pill extra."""
    radial = biblioteca().activo
    if radial.get("bloqueado"):
        cmds.warning(t("radial_bloqueado_aviso", nombre=nombre()))
        return
    menu = pill(crear=False)
    carpeta = menu.carpeta if menu else None
    if carpeta is not None and radial["botones"][carpeta]["tipo"] == "carpeta":
        radial["botones"][carpeta]["botones"][indice] = rd.normalizar_boton(boton, carpeta_permitida=False)
        nuevo = radial["botones"][carpeta]["botones"][indice]
    else:
        radial["botones"][indice] = rd.normalizar_boton(boton)
        nuevo = radial["botones"][indice]
    modificar(radial)
    print(t("buscador_asignado", texto=nuevo["texto"], numero=indice + 1))


# --- Su radial ------------------------------------------------------------------

def refrescar():
    """Repinta la pill y su configurador tras cambiar de radial o editarlo."""
    bib = biblioteca()
    menu = pill(crear=False)
    if menu:
        menu.usar_radial(bib.activo)
        actualizar_estados()
    configurador = _vivo("configurador")
    if configurador:
        configurador.fijar_radial(bib.activo, bib.sin_guardar, t("extra_cabecera", nombre=nombre()))
        if bib.activo.get("bloqueado"):
            configurador.boton_guardar.setText(t("boton_copia_mia"))
        else:
            configurador.boton_guardar.setText(t("boton_guardar_como_nuevo") if bib.es_preconfigurado
                                               else t("boton_guardar"))


def usar_radial(identificador):
    bib = biblioteca()
    if identificador == bib.origen:
        return
    if bib.sin_guardar and not _im()._preguntar(t("menu_titulo"), t("descartar_pregunta", nombre=nombre()),
                                                t("boton_descartar"), t("boton_cancelar")):
        return
    try:
        bib.usar(identificador)
    except rd.RadialNoValido as error:
        cmds.warning(t("radial_no_valido", ruta=identificador, error=error))
        return
    refrescar()


def modificar(radial):
    biblioteca().modificar(radial)
    refrescar()


def cambiar_apariencia(apariencia):
    radial = dict(biblioteca().activo)
    radial["apariencia"] = rd.normalizar_apariencia(apariencia)
    modificar(radial)


def guardar():
    bib = biblioteca()
    if bib.es_preconfigurado:
        return guardar_como()
    bib.guardar_cambios()
    refrescar()
    _im()._biblioteca_cambiada()
    print(t("guardado", nombre=nombre()))
    return True


def guardar_como():
    bib = biblioteca()
    base = nombre()
    if bib.es_preconfigurado:
        base = t("nombre_mi_radial", nombre=base)
    texto = _im()._pedir_nombre(base)
    if not texto:
        return False
    nuevo = bib.guardar_como(texto)
    refrescar()
    _im()._biblioteca_cambiada()
    print(t("guardado", nombre=nuevo["nombre"]))
    return True


def descartar_cambios():
    biblioteca().restaurar()
    refrescar()


def abrir_configurador():
    bib = biblioteca()
    ventana = _vivo("configurador")
    if ventana is None:
        from radial.configurador import Configurador
        ventana = Configurador(bib.activo, _im()._fuentes(), al_cambiar=modificar, al_guardar=guardar,
                               al_restaurar=descartar_cambios, puede_guardar=not bib.es_preconfigurado,
                               padre=_im().ventana_maya(), carpetas=_im().ajustes().carpetas)
        ventana.setWindowTitle(t("extra_config_titulo"))
        _estado["configurador"] = ventana
    refrescar()
    if not visible():
        mostrar()
    return _im()._traer(ventana)


def fijar_carpetas(valor):
    configurador = _vivo("configurador")
    if configurador:
        configurador.carpetas = bool(valor)
        configurador._ocultar_tipos()


# --- Arranque y parada ------------------------------------------------------------

def iniciar():
    """Al cargar el plugin: si estaba activa, vuelve a salir."""
    if ajustes().activa:
        mostrar()


def detener():
    configurador = _vivo("configurador")
    if configurador:
        configurador.close()
        destruir(configurador)
    menu = _vivo("pill")
    if menu:
        menu.hide()
        if getattr(menu, "etiqueta", None) is not None:
            destruir(menu.etiqueta)
        destruir(menu)
    _estado.update(ajustes=None, biblioteca=None, pill=None, configurador=None)
