"""Une el plugin con Maya: menú Radial de la barra, menú flotante, ventanas y doble Tab."""

import os
import platform

from maya import cmds

import radial
from radial import ajustes as aj
from radial import detector_tab as dt
from radial import radiales as rd
from radial.biblioteca import Biblioteca
from radial.i18n import t
from radial.qt import QtCore, QtGui, destruir, sigue_vivo, ventana_maya

MENU = "RadialMenu"
MENU_RADIALES = "RadialMenuRadiales"
MENU_FORMA = "RadialMenuForma"
COMANDO_ALTERNAR = "RadialMostrarOcultar"
COMANDO_CONFIGURAR = "RadialConfigurar"

_estado = {"menu": None, "filtro": None, "ajustes": None, "biblioteca": None,
           "configurador": None, "ventana_ajustes": None, "gestor": None, "buscador": None}


# --- Ajustes y biblioteca -------------------------------------------------------

def carpeta_preferencias():
    return os.path.join(cmds.internalVar(userAppDir=True), "radial")


def carpeta_mios():
    return os.path.join(carpeta_preferencias(), "radiales")


def ajustes():
    if _estado["ajustes"] is None:
        _estado["ajustes"] = aj.Ajustes(carpeta_preferencias())
    return _estado["ajustes"]


def biblioteca():
    if _estado["biblioteca"] is None:
        _estado["biblioteca"] = Biblioteca(ajustes(), carpeta_mios())
    return _estado["biblioteca"]


def radial_activo():
    return biblioteca().activo


def _nombre_activo():
    bib = biblioteca()
    return bib.nombre_de(bib.origen) or bib.activo["nombre"]


def _ventana(clave):
    ventana = _estado[clave]
    return ventana if sigue_vivo(ventana) else None


def _radial_cambiado():
    """Repinta el menú y las ventanas abiertas tras cambiar de radial o editarlo."""
    bib = biblioteca()
    menu = _menu_flotante(crear=False)
    if menu:
        menu.usar_radial(bib.activo)
    configurador = _ventana("configurador")
    if configurador:
        configurador.fijar_radial(bib.activo, bib.sin_guardar, _nombre_activo())
        configurador.boton_guardar.setText(t("boton_guardar_como_nuevo") if bib.es_preconfigurado
                                           else t("boton_guardar"))
    ventana_ajustes = _ventana("ventana_ajustes")
    if ventana_ajustes:
        ventana_ajustes.fijar(bib.activo["apariencia"], ajustes().forma, ajustes().pill_vertical,
                              ajustes().ventana_ms)
    gestor = _ventana("gestor")
    if gestor:
        gestor.refrescar()


def _preguntar(titulo, mensaje, si, no):
    respuesta = cmds.confirmDialog(title=titulo, message=mensaje, button=[si, no], defaultButton=si,
                                   cancelButton=no, dismissString=no)
    return respuesta == si


def _descartar_cambios_si_hace_falta():
    if not biblioteca().sin_guardar:
        return True
    return _preguntar(t("menu_titulo"), t("descartar_pregunta", nombre=_nombre_activo()),
                      t("boton_descartar"), t("boton_cancelar"))


def usar_radial(identificador):
    if identificador == biblioteca().origen or not _descartar_cambios_si_hace_falta():
        return
    try:
        radial_nuevo = biblioteca().usar(identificador)
    except rd.RadialNoValido as error:
        cmds.warning(t("radial_no_valido", ruta=identificador, error=error))
        return
    _radial_cambiado()
    print(t("radial_activo", nombre=radial_nuevo["nombre"]))


def modificar_radial(radial_nuevo):
    biblioteca().modificar(radial_nuevo)
    _radial_cambiado()


def guardar():
    """Guarda los cambios en el radial propio; si es preconfigurado, como radial nuevo."""
    if biblioteca().es_preconfigurado:
        return guardar_como()
    biblioteca().guardar_cambios()
    _radial_cambiado()
    print(t("guardado", nombre=_nombre_activo()))
    return True


def guardar_como():
    base = _nombre_activo()
    if biblioteca().es_preconfigurado:
        base = t("nombre_mi_radial", nombre=base)
    respuesta = cmds.promptDialog(title=t("guardar_como_titulo"), message=t("gestor_nombre"),
                                  text=rd.nombre_libre(carpeta_mios(), base),
                                  button=[t("boton_guardar"), t("boton_cancelar")],
                                  defaultButton=t("boton_guardar"), cancelButton=t("boton_cancelar"),
                                  dismissString=t("boton_cancelar"))
    if respuesta != t("boton_guardar"):
        return False
    nombre = cmds.promptDialog(query=True, text=True).strip()
    if not nombre:
        return False
    nuevo = biblioteca().guardar_como(nombre)
    _radial_cambiado()
    print(t("guardado", nombre=nuevo["nombre"]))
    return True


def descartar_cambios():
    if not biblioteca().sin_guardar:
        return
    if _preguntar(t("menu_titulo"), t("descartar_pregunta", nombre=_nombre_activo()),
                  t("boton_descartar"), t("boton_cancelar")):
        biblioteca().restaurar()
        _radial_cambiado()


def importar():
    rutas = cmds.fileDialog2(fileFilter=t("filtro_radial_maya"), fileMode=1, caption=t("importar_titulo"),
                             okCaption=t("boton_importar"))
    if not rutas or not _descartar_cambios_si_hace_falta():
        return
    try:
        nuevo = biblioteca().importar(rutas[0])
    except (rd.RadialNoValido, OSError) as error:
        cmds.warning(t("radial_no_valido", ruta=rutas[0], error=error))
        return
    _radial_cambiado()
    print(t("importado", nombre=nuevo["nombre"]))


def exportar():
    rutas = cmds.fileDialog2(fileFilter=t("filtro_radial_maya"), fileMode=0, caption=t("exportar_titulo"),
                             okCaption=t("boton_exportar"),
                             startingDirectory=rd.nombre_de_archivo(_nombre_activo()) + rd.EXTENSION)
    if not rutas:
        return
    try:
        ruta = biblioteca().exportar(rutas[0])
    except (rd.RadialNoValido, OSError) as error:
        cmds.warning(t("gestor_error", error=error))
        return
    print(t("exportado", ruta=ruta))


# --- Menú flotante ------------------------------------------------------------

def _menu_flotante(crear=True):
    menu = _estado["menu"]
    if not sigue_vivo(menu):
        menu = None
    if menu is None and crear:
        if ajustes().forma == "pill":
            from radial.menu_pill import MenuPill
            menu = MenuPill(ventana_maya(), al_ejecutar=_al_ejecutar, al_mover=_al_mover,
                            al_configurar=abrir_configurador, vertical=ajustes().pill_vertical)
        else:
            from radial.menu_radial import MenuRadial
            menu = MenuRadial(ventana_maya(), al_ejecutar=_al_ejecutar, al_mover=_al_mover,
                              al_configurar=abrir_configurador)
        menu.usar_radial(radial_activo())
        menu.al_soltar = _al_soltar
        _estado["menu"] = menu
        buscador = _buscador()
        buscador.activo = ajustes().buscador
        buscador.acompanar(menu)
    return menu


def _destruir_menu_flotante():
    menu = _estado["menu"]
    buscador = _estado.get("buscador")
    if sigue_vivo(buscador):
        buscador.acompanar(None)
    if sigue_vivo(menu):
        menu.hide()
        if getattr(menu, "etiqueta", None) is not None:
            destruir(menu.etiqueta)
        destruir(menu)
    _estado["menu"] = None


def visible():
    menu = _menu_flotante(crear=False)
    return bool(menu and menu.isVisible())


def _ajustar_a_pantalla(centro, menu):
    """Mueve ``centro`` lo justo para que el menú quepa entero en su pantalla."""
    pantalla = QtGui.QGuiApplication.screenAt(centro) or QtGui.QGuiApplication.primaryScreen()
    zona = pantalla.availableGeometry()
    mitad_x, mitad_y = menu.width() // 2, menu.height() // 2
    x = max(zona.left() + mitad_x, min(zona.right() - mitad_x, centro.x()))
    y = max(zona.top() + mitad_y, min(zona.bottom() - mitad_y, centro.y()))
    return QtCore.QPoint(x, y)


def mostrar():
    menu = _menu_flotante()
    guardada = ajustes().posicion
    if guardada is not None and QtGui.QGuiApplication.screenAt(QtCore.QPoint(*guardada)) is not None:
        centro = QtCore.QPoint(*guardada)
    else:
        centro = QtGui.QCursor.pos()
    menu.colocar(_ajustar_a_pantalla(centro, menu))
    menu.show()
    menu.raise_()


def ocultar():
    menu = _menu_flotante(crear=False)
    if menu:
        menu.hide()


def alternar():
    """Muestra u oculta el menú (lo mismo que el doble Tab)."""
    if visible():
        ocultar()
    else:
        mostrar()


def cambiar_forma(forma, vertical=None):
    """Cambia entre el radial y la pill (horizontal o vertical) sin perder la posición."""
    vertical = ajustes().pill_vertical if vertical is None else bool(vertical)
    if forma == ajustes().forma and vertical == ajustes().pill_vertical:
        return
    estaba_visible = visible()
    ajustes().forma = forma
    ajustes().pill_vertical = vertical
    ajustes().guardar()
    _destruir_menu_flotante()
    if estaba_visible:
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


def _al_soltar(indice, boton):
    """Se soltó una acción del buscador encima de un botón: pasa a ser ese botón."""
    radial = radial_activo()
    radial["botones"][indice] = rd.normalizar_boton(boton)
    modificar_radial(radial)
    print(t("buscador_asignado", texto=radial["botones"][indice]["texto"], numero=indice + 1))


# --- Buscador -------------------------------------------------------------------

def _buscador():
    buscador = _estado.get("buscador")
    if not sigue_vivo(buscador):
        from radial.buscador import Buscador
        buscador = Buscador(_acciones_buscador, _al_buscar, recientes=lambda: ajustes().recientes,
                            al_terminar=_devolver_foco, padre=ventana_maya())
        _estado["buscador"] = buscador
    return buscador


def _acciones_buscador():
    from radial import busqueda
    from radial.fuentes_maya import FuentesMaya
    fuentes = FuentesMaya()
    acciones = [busqueda.accion_de_comando(*c) for c in fuentes.comandos()]
    for estante, botones in fuentes.estantes():
        acciones.extend(busqueda.accion_de_estante(estante, b) for b in botones)
    return acciones


def _al_buscar(accion):
    from radial import acciones, busqueda
    ajustes().recientes = busqueda.anadir_reciente(ajustes().recientes, accion)
    ajustes().guardar()
    acciones.ejecutar(accion["boton"])


def _devolver_foco():
    principal = ventana_maya()
    if principal is not None:
        principal.activateWindow()


def cambiar_buscador(activo):
    """Muestra u oculta el buscador bajo el menú."""
    ajustes().buscador = bool(activo)
    ajustes().guardar()
    buscador = _estado.get("buscador")
    if sigue_vivo(buscador):
        buscador.activo = bool(activo)
        buscador.actualizar()


def _destruir_buscador():
    buscador = _estado.get("buscador")
    if sigue_vivo(buscador):
        buscador.acompanar(None)
        buscador.hide()
        destruir(buscador.lista)
        destruir(buscador)
    _estado["buscador"] = None


def _al_mover(centro):
    ajustes().posicion = (centro.x(), centro.y())
    ajustes().guardar()


# --- Ventanas -------------------------------------------------------------------

def _traer(ventana):
    ventana.show()
    ventana.raise_()
    ventana.activateWindow()
    return ventana


def abrir_configurador():
    ventana = _ventana("configurador")
    if ventana:
        bib = biblioteca()
        ventana.fijar_radial(bib.activo, bib.sin_guardar, _nombre_activo())
        if not visible():
            mostrar()
        return _traer(ventana)
    from radial.configurador import Configurador
    from radial.fuentes_maya import FuentesMaya
    bib = biblioteca()
    ventana = Configurador(bib.activo, FuentesMaya(), al_cambiar=modificar_radial, al_guardar=guardar,
                           al_restaurar=descartar_cambios, puede_guardar=not bib.es_preconfigurado,
                           padre=ventana_maya())
    ventana.fijar_cabecera(_nombre_activo(), bib.sin_guardar)
    _estado["configurador"] = ventana
    if not visible():
        mostrar()
    return _traer(ventana)


def abrir_ajustes():
    ventana = _ventana("ventana_ajustes")
    if ventana:
        ventana.fijar(radial_activo()["apariencia"], ajustes().forma, ajustes().pill_vertical,
                      ajustes().ventana_ms)
        if not visible():
            mostrar()
        return _traer(ventana)
    from radial.ventana_ajustes import VentanaAjustes
    ventana = VentanaAjustes(radial_activo()["apariencia"], ajustes().forma, ajustes().pill_vertical,
                             ajustes().ventana_ms, al_apariencia=_apariencia_cambiada,
                             al_forma=cambiar_forma, al_velocidad=_velocidad_cambiada, padre=ventana_maya(),
                             buscador=ajustes().buscador, al_buscador=cambiar_buscador)
    _estado["ventana_ajustes"] = ventana
    if not visible():
        mostrar()
    return _traer(ventana)


def _apariencia_cambiada(apariencia):
    nuevo = dict(radial_activo())
    nuevo["apariencia"] = apariencia
    biblioteca().modificar(nuevo)
    menu = _menu_flotante(crear=False)
    if menu:
        menu.usar_radial(biblioteca().activo)
    configurador = _ventana("configurador")
    if configurador:
        configurador.fijar_cabecera(_nombre_activo(), True)


def _velocidad_cambiada(ms):
    ajustes().ventana_ms = ms
    ajustes().guardar()
    filtro = _estado["filtro"]
    if filtro is not None:
        filtro.detector.ventana_ms = dt.limitar_ventana(ms)


def abrir_gestor():
    ventana = _ventana("gestor")
    if ventana:
        ventana.refrescar()
        return _traer(ventana)
    from radial.gestor_radiales import GestorRadiales
    ventana = GestorRadiales(biblioteca(), al_cambiar=_radial_cambiado, padre=ventana_maya())
    _estado["gestor"] = ventana
    return _traer(ventana)


def _cerrar_ventanas():
    for clave in ("configurador", "ventana_ajustes", "gestor"):
        ventana = _ventana(clave)
        if ventana:
            ventana.close()
            destruir(ventana)
        _estado[clave] = None


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
    if es_segundo:
        # El primer Tab ya pasó las comprobaciones; puede haber movido el foco a un campo.
        return True
    if escribiendo():
        return False
    # Con el menú a la vista, el doble Tab lo oculta desde cualquier sitio.
    return visible() or _sobre_visor()


def _instalar_filtro(intentos=10):
    """Escucha el teclado en las ventanas de Maya (no en toda la aplicación)."""
    if os.environ.get("RADIAL_SIN_TECLADO"):
        return
    from radial.filtro_teclado import FiltroTeclado
    principal = ventana_maya()
    ventana = principal.windowHandle() if principal is not None else None
    if ventana is None:
        if intentos > 0:  # la ventana de Maya aún no está a la vista
            QtCore.QTimer.singleShot(1000, lambda: _instalar_filtro(intentos - 1))
        return
    _quitar_filtro()
    filtro = FiltroTeclado(_puede_contar, alternar, ajustes().ventana_ms)
    filtro.instalar([ventana])
    # Paneles separados de la ventana principal: se escuchan cuando reciben el foco.
    QtGui.QGuiApplication.instance().focusWindowChanged.connect(filtro.escuchar)
    _estado["filtro"] = filtro


def _quitar_filtro():
    filtro = _estado["filtro"]
    if filtro is not None:
        try:
            QtGui.QGuiApplication.instance().focusWindowChanged.disconnect(filtro.escuchar)
        except (RuntimeError, TypeError):
            pass
        filtro.quitar()
        destruir(filtro)
    _estado["filtro"] = None


def _crear_comandos():
    """Comandos para el Editor de atajos (categoría Custom Scripts)."""
    for nombre, codigo, clave in (
            (COMANDO_ALTERNAR, "from radial import interfaz_maya; interfaz_maya.alternar()", "comando_anotacion"),
            (COMANDO_CONFIGURAR, "from radial import interfaz_maya; interfaz_maya.abrir_configurador()",
             "comando_configurar_anotacion")):
        if cmds.runTimeCommand(nombre, exists=True):
            cmds.runTimeCommand(nombre, edit=True, command=codigo, commandLanguage="python",
                                annotation=t(clave))
        else:
            cmds.runTimeCommand(nombre, annotation=t(clave), category="Custom Scripts", command=codigo,
                                commandLanguage="python")


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

    lineas.append(t("comprobar_radial", nombre=_nombre_activo(), forma=t("forma_" + ajustes().forma)))
    for i, boton in enumerate(radial_activo()["botones"]):
        if boton["tipo"] == "comando" and not acciones.comando_existe(boton["accion"]):
            lineas.append(t("comprobar_boton_aviso", numero=i + 1, comando=boton["accion"]))
            bien = False
    lineas.append(t("comprobar_carpeta", ruta=carpeta_mios(), n=len(biblioteca().mios())))

    lineas.append("")
    lineas.append(t("comprobar_ok") if bien else t("comprobar_avisos"))
    for linea in lineas:
        print("Radial | " + linea)
    if mostrar_dialogo:
        cmds.confirmDialog(title=t("comprobar_titulo"), message="\n".join(lineas),
                           button=[t("boton_aceptar")])
    return bien, lineas


# --- Menú de la barra ---------------------------------------------------------

def _ayuda():
    cmds.confirmDialog(title=t("menu_ayuda"), message=t("ayuda_texto"), button=[t("boton_aceptar")])


def _acerca():
    cmds.confirmDialog(title=t("menu_acerca"), message=t("acerca_texto", version=radial.__version__),
                       button=[t("boton_aceptar")])


def _llenar_radiales(*_):
    bib = biblioteca()
    origen = bib.origen
    cmds.menu(MENU_RADIALES, edit=True, deleteAllItems=True)
    cmds.setParent(MENU_RADIALES, menu=True)
    cmds.radioMenuItemCollection()
    cmds.menuItem(divider=True, dividerLabel=t("menu_preconfigurados"))
    for identificador, nombre in bib.preconfigurados():
        cmds.menuItem(label=nombre, radioButton=identificador == origen,
                      command=lambda *_, i=identificador: usar_radial(i))
    cmds.menuItem(divider=True, dividerLabel=t("menu_mis_radiales"))
    mios = bib.mios()
    if not mios:
        cmds.menuItem(label=t("menu_sin_mios"), enable=False)
    for identificador, nombre in mios:
        cmds.menuItem(label=nombre, radioButton=identificador == origen,
                      command=lambda *_, i=identificador: usar_radial(i))
    cmds.menuItem(divider=True)
    nombre = _nombre_activo()
    if bib.es_preconfigurado:
        cmds.menuItem(label=t("menu_guardar_cambios", nombre=nombre), enable=False)
    else:
        cmds.menuItem(label=t("menu_guardar_cambios", nombre=nombre), enable=bib.sin_guardar,
                      command=lambda *_: guardar())
    cmds.menuItem(label=t("menu_guardar_como"), command=lambda *_: guardar_como())
    cmds.menuItem(label=t("menu_descartar"), enable=bib.sin_guardar, command=lambda *_: descartar_cambios())
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_importar"), command=lambda *_: importar())
    cmds.menuItem(label=t("menu_exportar"), command=lambda *_: exportar())
    cmds.menuItem(label=t("menu_gestionar"), command=lambda *_: abrir_gestor())


def _llenar_forma(*_):
    cmds.menu(MENU_FORMA, edit=True, deleteAllItems=True)
    cmds.setParent(MENU_FORMA, menu=True)
    cmds.radioMenuItemCollection()
    forma, vertical = ajustes().forma, ajustes().pill_vertical
    for etiqueta, f, v in (("forma_radial", "radial", None), ("forma_pill_horizontal", "pill", False),
                           ("forma_pill_vertical", "pill", True)):
        marcado = forma == f and (v is None or v == vertical)
        cmds.menuItem(label=t(etiqueta), radioButton=marcado,
                      command=lambda *_, f=f, v=v: cambiar_forma(f, v))


def crear_menu():
    quitar_menu()
    cmds.menu(MENU, parent="MayaWindow", label=t("menu_titulo"), tearOff=True)
    cmds.menuItem(label=t("menu_alternar"), command=lambda *_: alternar())
    cmds.menuItem(label=t("menu_configurar"), command=lambda *_: abrir_configurador())
    cmds.menuItem(MENU_RADIALES, label=t("menu_radiales"), subMenu=True, tearOff=True,
                  postMenuCommand=_llenar_radiales)
    cmds.setParent("..", menu=True)
    cmds.menuItem(divider=True)
    cmds.menuItem(MENU_FORMA, label=t("menu_forma"), subMenu=True, postMenuCommand=_llenar_forma)
    cmds.setParent("..", menu=True)
    cmds.menuItem(label=t("menu_ajustes"), command=lambda *_: abrir_ajustes())
    cmds.menuItem(label=t("menu_centrar"), command=lambda *_: volver_a_centrar())
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_comprobar"), command=lambda *_: comprobar())
    cmds.menuItem(label=t("menu_ayuda"), command=lambda *_: _ayuda())
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
    _crear_comandos()
    # Con Maya ya abierto, no a mitad del arranque.
    QtCore.QTimer.singleShot(2000, _instalar_filtro)
    print(t("iniciado", version=radial.__version__))


def detener():
    """Lo llama el plugin al descargarse: quita el filtro, las ventanas y los menús."""
    _quitar_filtro()
    _cerrar_ventanas()
    _destruir_menu_flotante()
    _destruir_buscador()
    _estado.update(ajustes=None, biblioteca=None)
    if not cmds.about(batch=True):
        quitar_menu()
