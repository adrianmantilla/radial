"""Une el plugin con Maya: menú Radial de la barra, menú flotante y doble Tab."""

import os
import platform

from maya import cmds

import radial
from radial import ajustes as aj
from radial import radiales as rd
from radial.i18n import t
from radial.qt import QtCore, QtGui, sigue_vivo, ventana_maya

MENU = "RadialMenu"
MENU_RADIALES = "RadialMenuRadiales"
COMANDO_ALTERNAR = "RadialMostrarOcultar"
PREFIJO_PRECONFIGURADO = "pre:"

_estado = {"menu": None, "filtro": None, "ajustes": None, "radial": None}


# --- Ajustes y radial activo -----------------------------------------------

def carpeta_preferencias():
    return os.path.join(cmds.internalVar(userAppDir=True), "radial")


def ajustes():
    if _estado["ajustes"] is None:
        _estado["ajustes"] = aj.Ajustes(carpeta_preferencias())
    return _estado["ajustes"]


def _cargar_radial_activo():
    activo = ajustes().radial_activo or ""
    if activo.startswith(PREFIJO_PRECONFIGURADO):
        identificador = activo[len(PREFIJO_PRECONFIGURADO):]
        for nombre, ruta in rd.preconfigurados():
            if nombre == identificador:
                try:
                    return rd.leer(ruta)
                except rd.RadialNoValido as error:
                    cmds.warning(t("radial_no_valido", ruta=ruta, error=error))
    return rd.por_defecto()


def radial_activo():
    if _estado["radial"] is None:
        _estado["radial"] = _cargar_radial_activo()
    return _estado["radial"]


def usar_preconfigurado(identificador):
    for nombre, ruta in rd.preconfigurados():
        if nombre == identificador:
            _estado["radial"] = rd.leer(ruta)
            ajustes().radial_activo = PREFIJO_PRECONFIGURADO + identificador
            ajustes().guardar()
            menu = _estado["menu"]
            if sigue_vivo(menu):
                menu.usar_radial(_estado["radial"])
            print(t("radial_activo", nombre=_estado["radial"]["nombre"]))
            return _estado["radial"]
    return None


# --- Menú flotante ------------------------------------------------------------

def _menu_radial(crear=True):
    from radial.menu_radial import MenuRadial
    menu = _estado["menu"]
    if not sigue_vivo(menu) and crear:
        menu = MenuRadial(ventana_maya(), al_ejecutar=_al_ejecutar, al_mover=_al_mover,
                          al_configurar=_al_configurar)
        menu.usar_radial(radial_activo())
        _estado["menu"] = menu
    return menu if sigue_vivo(menu) else None


def visible():
    menu = _menu_radial(crear=False)
    return bool(menu and menu.isVisible())


def _pantalla_en(punto):
    return QtGui.QGuiApplication.screenAt(punto)


def _ajustar_a_pantalla(centro, menu):
    """Mueve ``centro`` lo justo para que el menú quepa entero en su pantalla."""
    pantalla = _pantalla_en(centro) or QtGui.QGuiApplication.primaryScreen()
    zona = pantalla.availableGeometry()
    mitad = menu.width() // 2
    x = max(zona.left() + mitad, min(zona.right() - mitad, centro.x()))
    y = max(zona.top() + mitad, min(zona.bottom() - mitad, centro.y()))
    return QtCore.QPoint(x, y)


def mostrar():
    menu = _menu_radial()
    guardada = ajustes().posicion
    if guardada is not None and _pantalla_en(QtCore.QPoint(*guardada)) is not None:
        centro = QtCore.QPoint(*guardada)
    else:
        centro = QtGui.QCursor.pos()
    menu.colocar(_ajustar_a_pantalla(centro, menu))
    menu.show()
    menu.raise_()


def ocultar():
    menu = _menu_radial(crear=False)
    if menu:
        menu.hide()


def alternar():
    """Muestra u oculta el menú radial (lo mismo que el doble Tab)."""
    if visible():
        ocultar()
    else:
        mostrar()


def volver_a_centrar():
    """Olvida la posición guardada: el menú vuelve a salir bajo el ratón."""
    ajustes().posicion = None
    ajustes().guardar()
    if visible():
        ocultar()
        mostrar()


def _al_ejecutar(indice):
    from radial import acciones
    acciones.ejecutar(radial_activo()["botones"][indice])


def _al_mover(centro):
    ajustes().posicion = (centro.x(), centro.y())
    ajustes().guardar()


def _al_configurar():
    _proximamente("funcion_configurador")


# --- Doble Tab --------------------------------------------------------------

def _sobre_visor():
    """True si el ratón está sobre un visor 3D (modelPanel)."""
    try:
        panel = cmds.getPanel(underPointer=True)
        return bool(panel) and cmds.getPanel(typeOf=panel) == "modelPanel"
    except RuntimeError:
        return False


def _puede_contar(es_segundo):
    from radial.filtro_teclado import escribiendo
    if visible():
        # Con el menú a la vista, el doble Tab lo oculta desde cualquier sitio
        # salvo mientras se escribe.
        return es_segundo or not escribiendo()
    if not _sobre_visor():
        return False
    # El primer Tab puede mover el foco a un campo; solo cuenta dónde estaba al principio.
    return es_segundo or not escribiendo()


def _instalar_filtro():
    from radial.filtro_teclado import FiltroTeclado
    _quitar_filtro()
    filtro = FiltroTeclado(_puede_contar, alternar, ajustes().ventana_ms)
    filtro.instalar()
    _estado["filtro"] = filtro


def _quitar_filtro():
    filtro = _estado["filtro"]
    if filtro is not None:
        filtro.quitar()
        if sigue_vivo(filtro):
            filtro.deleteLater()
    _estado["filtro"] = None


def _crear_comando():
    """Comando para el Editor de atajos, por si alguien prefiere otra tecla."""
    codigo = "from radial import interfaz_maya; interfaz_maya.alternar()"
    if cmds.runTimeCommand(COMANDO_ALTERNAR, exists=True):
        cmds.runTimeCommand(COMANDO_ALTERNAR, edit=True, command=codigo, commandLanguage="python")
    else:
        cmds.runTimeCommand(COMANDO_ALTERNAR, annotation=t("comando_anotacion"), category="Custom Scripts",
                            command=codigo, commandLanguage="python")


# --- Comprobar --------------------------------------------------------------

def comprobar(mostrar_dialogo=True):
    """Devuelve (todo_bien, líneas) y, si ``mostrar_dialogo``, las enseña."""
    from radial import acciones
    lineas, bien = [t("comprobar_version", version=radial.__version__)], True

    version = cmds.about(version=True)
    sistema = "{} {}".format(platform.system(), platform.release())
    if any(v in version for v in ("2026", "2027")):
        lineas.append(t("comprobar_maya", version=version, sistema=sistema))
    else:
        lineas.append(t("comprobar_maya_aviso", version=version))
        bien = False

    lineas.append(t("comprobar_qt", version=QtCore.qVersion()))
    filtro = _estado["filtro"]
    if filtro is not None:
        lineas.append(t("comprobar_tab_ok", ms=filtro.detector.ventana_ms))
    else:
        lineas.append(t("comprobar_tab_aviso"))
        bien = False

    activo = radial_activo()
    lineas.append(t("comprobar_radial", nombre=activo["nombre"]))
    for i, boton in enumerate(activo["botones"]):
        if boton["tipo"] == "comando" and not acciones.comando_existe(boton["accion"]):
            lineas.append(t("comprobar_boton_aviso", numero=i + 1, comando=boton["accion"]))
            bien = False

    lineas.append("")
    lineas.append(t("comprobar_ok") if bien else t("comprobar_avisos"))
    for linea in lineas:
        print("Radial | " + linea)
    if mostrar_dialogo:
        cmds.confirmDialog(title=t("comprobar_titulo"), message="\n".join(lineas),
                           button=[t("boton_aceptar")])
    return bien, lineas


# --- Menú de la barra ---------------------------------------------------------

def _proximamente(clave_funcion):
    cmds.confirmDialog(title=t("menu_titulo"), message=t("proximamente", funcion=t(clave_funcion)),
                       button=[t("boton_aceptar")])


def _acerca():
    cmds.confirmDialog(title=t("menu_acerca"), message=t("acerca_texto", version=radial.__version__),
                       button=[t("boton_aceptar")])


def _llenar_radiales(*_):
    cmds.menu(MENU_RADIALES, edit=True, deleteAllItems=True)
    cmds.setParent(MENU_RADIALES, menu=True)
    activo = ajustes().radial_activo or ""
    hay_activo = any(activo == PREFIJO_PRECONFIGURADO + n for n, _ in rd.preconfigurados())
    cmds.menuItem(divider=True, dividerLabel=t("menu_preconfigurados"))
    cmds.radioMenuItemCollection()
    for indice, (nombre, ruta) in enumerate(rd.preconfigurados()):
        try:
            titulo = rd.leer(ruta)["nombre"]
        except rd.RadialNoValido:
            continue
        marcado = activo == PREFIJO_PRECONFIGURADO + nombre or (not hay_activo and indice == 0)
        cmds.menuItem(label=titulo, radioButton=marcado,
                      command=lambda *_, n=nombre: usar_preconfigurado(n))
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_guardar_cargar"), enable=False)


def crear_menu():
    quitar_menu()
    cmds.menu(MENU, parent="MayaWindow", label=t("menu_titulo"), tearOff=True)
    cmds.menuItem(label=t("menu_alternar"), command=lambda *_: alternar())
    cmds.menuItem(label=t("menu_configurar"), command=lambda *_: _proximamente("funcion_configurador"))
    cmds.menuItem(MENU_RADIALES, label=t("menu_radiales"), subMenu=True, tearOff=True,
                  postMenuCommand=_llenar_radiales)
    cmds.setParent("..", menu=True)
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_ajustes"), command=lambda *_: _proximamente("funcion_ajustes"))
    cmds.menuItem(label=t("menu_centrar"), command=lambda *_: volver_a_centrar())
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_comprobar"), command=lambda *_: comprobar())
    cmds.menuItem(label=t("menu_acerca"), command=lambda *_: _acerca())
    return MENU


def quitar_menu():
    if cmds.menu(MENU, exists=True):
        cmds.deleteUI(MENU)


# --- Arranque y parada --------------------------------------------------------

def iniciar():
    """Lo llama el plugin al cargarse."""
    if cmds.about(batch=True):
        return
    crear_menu()
    _crear_comando()
    _instalar_filtro()
    print(t("iniciado", version=radial.__version__))


def detener():
    """Lo llama el plugin al descargarse: quita el filtro, el menú flotante y el de la barra."""
    _quitar_filtro()
    menu = _estado["menu"]
    if sigue_vivo(menu):
        menu.hide()
        menu.deleteLater()
    _estado.update(menu=None, radial=None, ajustes=None)
    if not cmds.about(batch=True):
        quitar_menu()
