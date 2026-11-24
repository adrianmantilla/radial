"""Une el plugin con Maya: menú Radial de la barra, menú flotante, ventanas y doble Tab."""

import os
import platform

from maya import cmds

import radial
from radial import ajustes as aj
from radial import detector_tab as dt
from radial import radiales as rd
from radial.biblioteca import Biblioteca
from radial.i18n import sinonimos, t
from radial.qt import QtCore, QtGui, QtWidgets, destruir, sigue_vivo, ventana_maya

MENU = "RadialMenu"
MENU_RADIALES = "RadialMenuRadiales"
MENU_FORMA = "RadialMenuForma"
COMANDO_ALTERNAR = "RadialMostrarOcultar"
COMANDO_CONFIGURAR = "RadialConfigurar"

_estado = {"menu": None, "filtro": None, "ajustes": None, "biblioteca": None,
           "configurador": None, "ventana_ajustes": None, "gestor": None, "buscador": None,
           "tarjeta": None, "reloj_automatico": None, "contexto": None, "fuentes": None, "atajos": None,
           "reto": None,
           "reloj_gesto": None, "gesto": None}


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
        _actualizar_estados()
    configurador = _ventana("configurador")
    if configurador:
        configurador.fijar_radial(bib.activo, bib.sin_guardar, _nombre_activo())
        if bib.activo.get("bloqueado"):
            configurador.boton_guardar.setText(t("boton_copia_mia"))
        else:
            configurador.boton_guardar.setText(t("boton_guardar_como_nuevo") if bib.es_preconfigurado
                                               else t("boton_guardar"))
    ventana_ajustes = _ventana("ventana_ajustes")
    if ventana_ajustes:
        ventana_ajustes.fijar(bib.activo["apariencia"], ajustes().forma, ajustes().pill_vertical,
                              ajustes().ventana_ms, len(bib.activo["botones"]))
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


def _pedir_nombre(base):
    """Pregunta el nombre del radial nuevo. None si se cancela."""
    respuesta = cmds.promptDialog(title=t("guardar_como_titulo"), message=t("gestor_nombre"),
                                  text=rd.nombre_libre(carpeta_mios(), base),
                                  button=[t("boton_guardar"), t("boton_cancelar")],
                                  defaultButton=t("boton_guardar"), cancelButton=t("boton_cancelar"),
                                  dismissString=t("boton_cancelar"))
    if respuesta != t("boton_guardar"):
        return None
    return cmds.promptDialog(query=True, text=True).strip() or None


def _biblioteca_cambiada():
    """Se guardó un radial nuevo (desde la pill extra): el gestor lo enseña."""
    gestor = _ventana("gestor")
    if gestor:
        gestor.refrescar()


def guardar_como():
    base = _nombre_activo()
    if biblioteca().es_preconfigurado:
        base = t("nombre_mi_radial", nombre=base)
    nombre = _pedir_nombre(base)
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


def exportar_bloqueado():
    """Exporta el radial activo bloqueado: en la carpeta de clase, los alumnos lo usan pero no lo cambian."""
    inicio = os.path.join(ajustes().carpeta_clase or "", rd.nombre_de_archivo(_nombre_activo()) + rd.EXTENSION)
    rutas = cmds.fileDialog2(fileFilter=t("filtro_radial_maya"), fileMode=0, caption=t("menu_exportar_bloqueado"),
                             okCaption=t("boton_exportar"), startingDirectory=inicio)
    if not rutas:
        return
    try:
        ruta = biblioteca().exportar(rutas[0], bloqueado=True)
    except (rd.RadialNoValido, OSError) as error:
        cmds.warning(t("gestor_error", error=error))
        return
    print(t("exportado_bloqueado", ruta=ruta))


# --- Aspecto: tema, acento e idioma -------------------------------------------------

def _rehacer_flotantes():
    """Vuelve a crear el menú, el buscador, la tarjeta y la pill extra (tras cambiar tema o idioma)."""
    from radial import pill_extra
    estaba_visible = visible()
    _destruir_menu_flotante()
    _destruir_buscador()
    tarjeta = _estado.get("tarjeta")
    if sigue_vivo(tarjeta):
        tarjeta.hide()
        destruir(tarjeta)
    _estado["tarjeta"] = None
    extra_activa = pill_extra.visible()
    pill_extra.detener()
    if extra_activa:
        pill_extra.iniciar()
    if estaba_visible:
        mostrar()


def cambiar_aspecto(tema_nuevo=None, acento=None):
    """Tema («oscuro» o «claro») y color de acento («#rrggbb» o "" para el del tema)."""
    from radial import tema
    if tema_nuevo is not None:
        ajustes().tema = tema_nuevo
    if acento is not None:
        ajustes().acento = acento
    ajustes().guardar()
    if tema.aplicar(ajustes().tema, ajustes().acento):
        _rehacer_flotantes()


def cambiar_iconos(modo):
    """Iconos automáticos: «propios» (los del plugin) o «maya» (los de Maya a color)."""
    from radial import iconos
    ajustes().iconos = modo
    ajustes().guardar()
    if iconos.modo() != ajustes().iconos:
        iconos.usar_iconos(ajustes().iconos, _icono_de_comando)
        _rehacer_flotantes()
        configurador = _ventana("configurador")
        if configurador:
            configurador.fijar_radial(biblioteca().activo, biblioteca().sin_guardar, _nombre_activo())


def cambiar_idioma(idioma):
    """Idioma de la interfaz («es», «en»...). Rehace el menú de Maya y las ventanas."""
    from radial import i18n
    ajustes().idioma = idioma
    ajustes().guardar()
    if i18n.idioma() == (idioma or i18n.IDIOMA_BASE):
        return
    i18n.usar_idioma(idioma)
    crear_menu()
    _rehacer_flotantes()
    ventana = _ventana("ventana_ajustes")
    if ventana:
        indice = ventana.pestanas.currentIndex()

        def reabrir():
            if _ventana("ventana_ajustes"):
                _estado["ventana_ajustes"].close()
                destruir(_estado["ventana_ajustes"])
            _estado["ventana_ajustes"] = None
            nueva = abrir_ajustes()
            nueva.pestanas.setCurrentIndex(indice)

        QtCore.QTimer.singleShot(0, reabrir)  # no se destruye una ventana desde su propia señal


# --- Paquete de clase -----------------------------------------------------------

def cargar_fijadas():
    """Lee las opciones que fija el profesor en la carpeta de clase. Devuelve True si cambió algo."""
    from radial import paquete
    antes = dict(ajustes().fijadas)
    ajustes().fijar_opciones(paquete.fijadas_de_carpeta(ajustes().carpeta_clase))
    return ajustes().fijadas != antes


def _aplicar_opciones_vigentes(forma_antes):
    """Tras cambiar las opciones (paquete o carpeta de clase), pone al día lo que se ve."""
    filtro = _estado["filtro"]
    if filtro is not None:
        filtro.detector.ventana_ms = ajustes().ventana_ms
    if (ajustes().forma, ajustes().pill_vertical) != forma_antes:
        estaba_visible = visible()
        _destruir_menu_flotante()
        if estaba_visible:
            mostrar()
    buscador = _estado.get("buscador")
    if sigue_vivo(buscador):
        buscador.activo = ajustes().buscador
        buscador.actualizar()
    from radial import pill_extra
    pill_extra.fijar_carpetas(ajustes().carpetas)
    if not ajustes().aprendizaje:
        _ocultar_tarjeta()
    _estado["contexto"] = None
    _reloj_automatico()


def exportar_paquete():
    """El profesor exporta su menú, su pill extra y sus opciones en un archivo para la clase."""
    from radial import paquete, pill_extra
    fijar, no_fijar, cancelar = t("boton_fijar"), t("boton_no_fijar"), t("boton_cancelar")
    respuesta = cmds.confirmDialog(title=t("menu_exportar_paquete"), message=t("paquete_fijar_pregunta"),
                                   button=[fijar, no_fijar, cancelar], defaultButton=no_fijar,
                                   cancelButton=cancelar, dismissString=cancelar)
    if respuesta not in (fijar, no_fijar):
        return None
    inicio = os.path.join(ajustes().carpeta_clase or "", rd.nombre_de_archivo(_nombre_activo()) + paquete.EXTENSION)
    rutas = cmds.fileDialog2(fileFilter=t("filtro_paquete"), fileMode=0, caption=t("menu_exportar_paquete"),
                             okCaption=t("boton_exportar"), startingDirectory=inicio)
    if not rutas:
        return None
    extra_activa = pill_extra.ajustes().activa
    datos = paquete.crear(_nombre_activo(), radial_activo(), ajustes(),
                          extra=pill_extra.biblioteca().activo if extra_activa else None,
                          extra_activa=extra_activa, fijar=respuesta == fijar)
    try:
        ruta = paquete.escribir(datos, rutas[0])
    except (paquete.PaqueteNoValido, OSError) as error:
        cmds.warning(t("gestor_error", error=error))
        return None
    print(t("paquete_exportado", ruta=ruta))
    return ruta


def importar_paquete(ruta=None):
    """El alumno importa un paquete: los radiales pasan a ser suyos y se aplican las opciones."""
    from radial import paquete, pill_extra
    if ruta is None:
        rutas = cmds.fileDialog2(fileFilter=t("filtro_paquete"), fileMode=1, caption=t("menu_importar_paquete"),
                                 okCaption=t("boton_importar"))
        if not rutas:
            return False
        ruta = rutas[0]
    try:
        datos = paquete.leer(ruta)
    except paquete.PaqueteNoValido as error:
        cmds.warning(t("radial_no_valido", ruta=ruta, error=error))
        return False
    if not _descartar_cambios_si_hace_falta():
        return False
    forma_antes = (ajustes().forma, ajustes().pill_vertical)
    for clave, valor in datos["opciones"].items():
        setattr(ajustes(), clave, valor)
    identificador, _, _ = rd.guardar_nuevo(datos["menu"], carpeta_mios(), datos["menu"]["nombre"])
    biblioteca().usar("mio:" + identificador)
    if datos["extra"] is not None:
        extra = pill_extra.biblioteca()
        if extra.sin_guardar:
            extra.restaurar()
        otro, _, _ = rd.guardar_nuevo(datos["extra"], carpeta_mios(), datos["extra"]["nombre"])
        extra.usar("mio:" + otro)
        pill_extra.refrescar()
        pill_extra.activar(datos["extra_activa"])
    ajustes().guardar()
    _radial_cambiado()
    _aplicar_opciones_vigentes(forma_antes)
    print(t("paquete_importado", nombre=datos["nombre"]))
    return True


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
        menu.tiene_opciones = _tiene_opciones
        menu.al_carpeta = lambda carpeta: _actualizar_estados()
        menu.al_sobre = _al_sobre
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
    if biblioteca().refrescar_clase():
        _radial_cambiado()
    menu = _menu_flotante()
    _aplicar_automatico(anunciar=False)
    guardada = ajustes().posicion
    if guardada is not None and QtGui.QGuiApplication.screenAt(QtCore.QPoint(*guardada)) is not None:
        centro = QtCore.QPoint(*guardada)
    else:
        centro = QtGui.QCursor.pos()
    menu.colocar(_ajustar_a_pantalla(centro, menu))
    menu.show()
    menu.raise_()
    _actualizar_estados()
    _reloj_automatico()


def ocultar():
    menu = _menu_flotante(crear=False)
    if menu:
        menu.hide()
    _ocultar_tarjeta()


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


def _botones_visibles():
    menu = _menu_flotante(crear=False)
    return menu.botones_visibles() if menu else radial_activo()["botones"]


def _al_ejecutar(indice, opciones=False):
    from radial import acciones
    acciones.ejecutar(_botones_visibles()[indice], opciones=opciones)
    _actualizar_estados()


_cache_opciones = {}


def _tiene_opciones(boton):
    """True si el botón es un comando con ventana de opciones (se pregunta a Maya una vez)."""
    if boton.get("tipo") != "comando":
        return False
    accion = boton.get("accion", "")
    if accion not in _cache_opciones:
        from radial import acciones
        _cache_opciones[accion] = acciones.comando_de_opciones(boton) is not None
    return _cache_opciones[accion]


def _actualizar_estados():
    """Marca los interruptores encendidos. Se llama al mostrar el menú y tras cada clic."""
    from radial import pill_extra
    pill_extra.actualizar_estados()
    menu = _menu_flotante(crear=False)
    if not menu or not menu.isVisible():
        return
    from radial import acciones
    menu.fijar_estados([acciones.estado(b) for b in menu.botones_visibles()])


def _al_soltar(indice, boton):
    """Se soltó una acción del buscador encima de un botón: pasa a ser ese botón."""
    radial = radial_activo()
    if radial.get("bloqueado"):
        cmds.warning(t("radial_bloqueado_aviso", nombre=_nombre_activo()))
        return
    menu = _menu_flotante(crear=False)
    carpeta = menu.carpeta if menu else None
    if carpeta is not None and radial["botones"][carpeta]["tipo"] == "carpeta":
        if indice >= len(radial["botones"][carpeta]["botones"]):
            return  # hueco de relleno: las carpetas tienen seis botones
        radial["botones"][carpeta]["botones"][indice] = rd.normalizar_boton(boton, carpeta_permitida=False)
        nuevo = radial["botones"][carpeta]["botones"][indice]
    else:
        radial["botones"][indice] = rd.normalizar_boton(boton)
        nuevo = radial["botones"][indice]
    modificar_radial(radial)
    print(t("buscador_asignado", texto=nuevo["texto"], numero=indice + 1))


# --- Buscador -------------------------------------------------------------------

def _buscador():
    buscador = _estado.get("buscador")
    if not sigue_vivo(buscador):
        from radial.buscador import Buscador
        buscador = Buscador(_acciones_buscador, _al_buscar, recientes=lambda: ajustes().recientes,
                            al_terminar=_devolver_foco, padre=ventana_maya(), buscar_icono=_icono_de_comando,
                            favoritos=lambda: ajustes().favoritos, al_favorito=_alternar_favorito)
        _estado["buscador"] = buscador
    return buscador


def _fuentes():
    if _estado.get("fuentes") is None:
        from radial.fuentes_maya import FuentesMaya
        _estado["fuentes"] = FuentesMaya()
    return _estado["fuentes"]


def _icono_de_comando(nombre):
    return _fuentes().icono_de_comando(nombre)


def _acciones_buscador():
    from radial import busqueda
    fuentes = _fuentes()
    traducciones = sinonimos()
    try:
        atajos = fuentes.atajos()
    except Exception:  # sin atajos el buscador sigue funcionando
        atajos = {}
    acciones = []
    for nombre, categoria, descripcion in fuentes.comandos():
        extra = traducciones.get(nombre, {})
        acciones.append(busqueda.accion_de_comando(nombre, categoria, descripcion, extra.get("es", ""),
                                                   extra.get("ayuda", ""), atajos.get(nombre, "")))
    for estante, botones in fuentes.estantes():
        acciones.extend(busqueda.accion_de_estante(estante, b) for b in botones)
    try:
        busqueda.unir_menus(acciones, fuentes.menus())
    except Exception:  # sin los menús de Maya el buscador sigue funcionando
        pass
    try:
        acciones.extend(busqueda.accion_de_script(ruta, t("buscador_mis_scripts")) for ruta in fuentes.scripts())
    except Exception:
        pass
    return acciones


def _al_buscar(accion, opciones=False):
    from radial import acciones, busqueda
    ajustes().recientes = busqueda.anadir_reciente(ajustes().recientes, accion)
    ajustes().guardar()
    acciones.ejecutar(accion["boton"], opciones=opciones)
    _actualizar_estados()


def _alternar_favorito(accion):
    from radial import busqueda
    ajustes().favoritos = busqueda.alternar_favorito(ajustes().favoritos, accion)
    ajustes().guardar()


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
                           padre=ventana_maya(), carpetas=ajustes().carpetas)
    ventana.fijar_cabecera(_nombre_activo(), bib.sin_guardar)
    _estado["configurador"] = ventana
    if not visible():
        mostrar()
    return _traer(ventana)


def abrir_ajustes():
    ventana = _ventana("ventana_ajustes")
    if ventana:
        ventana.fijar(radial_activo()["apariencia"], ajustes().forma, ajustes().pill_vertical,
                      ajustes().ventana_ms, len(radial_activo()["botones"]))
        if not visible():
            mostrar()
        return _traer(ventana)
    from radial.ventana_ajustes import VentanaAjustes
    ventana = VentanaAjustes(radial_activo()["apariencia"], ajustes().forma, ajustes().pill_vertical,
                             ajustes().ventana_ms, al_apariencia=_apariencia_cambiada,
                             al_forma=cambiar_forma, al_velocidad=_velocidad_cambiada, padre=ventana_maya(),
                             buscador=ajustes().buscador, al_buscador=cambiar_buscador,
                             opciones=_opciones(), al_opcion=cambiar_opcion, al_reglas=abrir_reglas,
                             extra=_datos_extra(), al_extra=cambiar_extra,
                             cantidad=len(radial_activo()["botones"]), al_cantidad=cambiar_cantidad,
                             atajo=ajustes().atajo, al_atajo=cambiar_atajo,
                             aspecto=_datos_aspecto(), al_aspecto=_al_aspecto)
    ventana.fijar_bloqueadas(dict(ajustes().fijadas))
    _estado["ventana_ajustes"] = ventana
    if not visible():
        mostrar()
    return _traer(ventana)


def _datos_aspecto():
    from radial import i18n
    return {"tema": ajustes().tema, "acento": ajustes().acento, "iconos": ajustes().iconos, "idioma": i18n.idioma(),
            "idiomas": i18n.idiomas()}


def _al_aspecto(clave, valor):
    if clave == "tema":
        cambiar_aspecto(tema_nuevo=valor)
    elif clave == "acento":
        cambiar_aspecto(acento=valor)
    elif clave == "iconos":
        cambiar_iconos(valor)
    elif clave == "idioma":
        cambiar_idioma(valor)


def cambiar_cantidad(cantidad):
    """Número de botones del menú principal (de 2 a 12)."""
    if len(radial_activo()["botones"]) != cantidad:
        modificar_radial(rd.cambiar_cantidad(radial_activo(), cantidad))


def cambiar_atajo(texto):
    """Pone (o quita, con "") el atajo de teclado del menú. Devuelve "" o el motivo por el que no se puede."""
    from radial import atajo
    anterior = ajustes().atajo
    if texto == anterior:
        return ""
    if texto:
        try:
            atajo.asignar(texto, COMANDO_ALTERNAR, t("comando_anotacion"))
        except atajo.AtajoNoValido as error:
            ocupado = str(error)
            return t("atajo_ocupado", comando=ocupado) if ocupado and ocupado != texto else t("atajo_no_valido")
        except RuntimeError as error:
            return str(error)
    if anterior:
        atajo.quitar(anterior)
    ajustes().atajo = texto
    ajustes().guardar()
    print(t("atajo_asignado", atajo=texto) if texto else t("atajo_quitado"))
    return ""


def _ejecutar_dialogo(dialogo):
    """Abre ``dialogo`` y espera (aparte para poder probarlo sin ventana)."""
    return dialogo.exec_() if hasattr(dialogo, "exec_") else dialogo.exec()


def _titulo_hueco(i, boton):
    return "{} · {}".format(i + 1, boton["texto"] or t("config_hueco_vacio"))


def crear_boton_de_lo_ultimo():
    """Crea un botón con las últimas órdenes del Script Editor, sin escribir código."""
    from radial import grabar, pill_extra
    lineas = grabar.ordenes(grabar.registro_maya())
    if not lineas:
        cmds.confirmDialog(title=t("grabar_titulo"), message=t("grabar_vacio"), button=[t("boton_aceptar")])
        return False
    destinos = [("menu", t("grabar_menu_principal", nombre=_nombre_activo()))]
    huecos = {"menu": [(i, _titulo_hueco(i, b)) for i, b in enumerate(radial_activo()["botones"])]}
    if pill_extra.ajustes().activa:
        destinos.append(("extra", t("grabar_menu_extra", nombre=pill_extra.nombre())))
        huecos["extra"] = [(i, _titulo_hueco(i, b)) for i, b in enumerate(pill_extra.biblioteca().activo["botones"])]
    dialogo = grabar.dialogo(lineas, huecos, destinos, padre=ventana_maya())
    vacios = [i for i, b in enumerate(radial_activo()["botones"]) if b["tipo"] == "vacio"]
    if vacios:
        dialogo.hueco.setCurrentIndex(dialogo.hueco.findData(vacios[0]))
    if not _ejecutar_dialogo(dialogo):
        return False
    boton, destino, indice = dialogo.resultado()
    if boton is None or indice is None:
        return False
    extra = destino == "extra"
    radial = pill_extra.biblioteca().activo if extra else radial_activo()
    if radial.get("bloqueado"):
        cmds.warning(t("radial_bloqueado_aviso", nombre=pill_extra.nombre() if extra else _nombre_activo()))
        return False
    radial = dict(radial, botones=list(radial["botones"]))
    radial["botones"][indice] = rd.normalizar_boton(boton)
    (pill_extra.modificar if extra else modificar_radial)(radial)
    print(t("buscador_asignado", texto=boton["texto"], numero=indice + 1))
    return True


def _datos_extra():
    from radial import pill_extra
    return {"activa": pill_extra.ajustes().activa, "vertical": pill_extra.ajustes().vertical,
            "radial": pill_extra.biblioteca().origen, "apariencia": pill_extra.biblioteca().activo["apariencia"],
            "cantidad": len(pill_extra.biblioteca().activo["botones"]),
            "radiales": _todos_los_radiales()}


def cambiar_extra(clave, valor=None):
    """La pill extra desde Ajustes: activa, radial, vertical, apariencia, cantidad o configurar."""
    from radial import pill_extra
    if clave == "activa":
        pill_extra.activar(valor)
    elif clave == "radial":
        pill_extra.usar_radial(valor)
    elif clave == "vertical":
        pill_extra.cambiar_vertical(valor)
    elif clave == "apariencia":
        pill_extra.cambiar_apariencia(valor)
    elif clave == "cantidad":
        pill_extra.cambiar_cantidad(valor)
    elif clave == "configurar":
        pill_extra.abrir_configurador()
    ventana = _ventana("ventana_ajustes")
    if ventana and clave in ("radial", "configurar"):
        ventana.fijar_extra(_datos_extra())


def _opciones():
    a = ajustes()
    return {"carpetas": a.carpetas, "automatico": a.automatico, "aprendizaje": a.aprendizaje,
            "carpeta_clase": a.carpeta_clase}


def cambiar_opcion(clave, valor):
    """Una opción de Ajustes: carpetas, automatico, aprendizaje o carpeta_clase."""
    setattr(ajustes(), clave, valor)
    ajustes().guardar()
    if clave == "carpetas":
        from radial import pill_extra
        pill_extra.fijar_carpetas(valor)
        configurador = _ventana("configurador")
        if configurador:
            configurador.carpetas = bool(valor)
            configurador._ocultar_tipos()
    elif clave == "automatico":
        _estado["contexto"] = None
        if valor:
            _aplicar_automatico()
        _reloj_automatico()
    elif clave == "aprendizaje" and not valor:
        _ocultar_tarjeta()
    elif clave == "carpeta_clase":
        biblioteca()._activo = None  # se vuelve a leer: si era de clase y ya no está, se usa otro
        _radial_cambiado()
        forma_antes = (ajustes().forma, ajustes().pill_vertical)
        if cargar_fijadas():
            _aplicar_opciones_vigentes(forma_antes)
            ventana = _ventana("ventana_ajustes")
            if ventana:
                ventana.fijar_bloqueadas(dict(ajustes().fijadas))


def _todos_los_radiales():
    bib = biblioteca()
    clase = [(i, "{} ({})".format(n, t("menu_de_clase"))) for i, n, _ in bib.de_clase()]
    return bib.preconfigurados() + bib.mios() + clase


def abrir_reglas():
    from radial import automatico
    from radial.ventana_ajustes import DialogoReglas
    dialogo = DialogoReglas(ajustes().reglas, automatico.workspaces_maya(), _todos_los_radiales(),
                            padre=_ventana("ventana_ajustes") or ventana_maya())
    if dialogo.exec_() if hasattr(dialogo, "exec_") else dialogo.exec():
        ajustes().reglas = dialogo.reglas()
        ajustes().guardar()
        _estado["contexto"] = None
        _aplicar_automatico()


# --- Radial automático ------------------------------------------------------------

def _reloj_automatico():
    """Mientras el menú se ve y la opción está activa, mira cada poco el workspace y la selección."""
    reloj = _estado.get("reloj_automatico")
    if ajustes().automatico and visible():
        if not sigue_vivo(reloj):
            reloj = QtCore.QTimer(ventana_maya())
            reloj.setInterval(800)
            reloj.timeout.connect(_tic_automatico)
            _estado["reloj_automatico"] = reloj
        if not reloj.isActive():
            reloj.start()
    elif sigue_vivo(reloj):
        reloj.stop()


def _tic_automatico():
    if not ajustes().automatico or not visible():
        _reloj_automatico()
        return
    _aplicar_automatico()


def _aplicar_automatico(anunciar=True):
    """Cambia al radial de la regla que toca, solo cuando cambia el contexto.

    Así, si el alumno elige otro radial a mano, se respeta hasta que cambie de
    workspace o de modo de selección. Con cambios sin guardar no se toca nada.
    """
    if not ajustes().automatico:
        return
    from radial import automatico
    try:
        contexto = automatico.contexto_maya()
    except Exception:  # nunca debe romper el menú
        return
    if contexto == _estado.get("contexto"):
        return
    _estado["contexto"] = contexto
    bib = biblioteca()
    identificador = automatico.elegir(ajustes().reglas, *contexto)
    if not identificador or identificador == bib.origen or bib.sin_guardar:
        return
    try:
        bib.usar(identificador)
    except rd.RadialNoValido:
        return
    _radial_cambiado()
    menu = _menu_flotante(crear=False)
    if anunciar and menu:
        menu.anunciar(_nombre_activo())


# --- Modo aprendizaje -------------------------------------------------------------

def _tarjeta():
    tarjeta = _estado.get("tarjeta")
    if not sigue_vivo(tarjeta):
        from radial.ayuda import TarjetaAyuda
        tarjeta = TarjetaAyuda(ventana_maya())
        _estado["tarjeta"] = tarjeta
    return tarjeta


def _ocultar_tarjeta():
    tarjeta = _estado.get("tarjeta")
    if sigue_vivo(tarjeta):
        tarjeta.ocultar()


def _info_de(boton):
    """La acción del buscador que corresponde a ``boton`` (traducción, ayuda, atajo...)."""
    if boton.get("tipo") != "comando":
        return {}
    nombre = boton.get("accion", "")
    for accion in _buscador().acciones():
        if accion["boton"].get("tipo") == "comando" and accion["nombre"] == nombre:
            return accion
    return {}


def _al_sobre(boton, menu=None):
    """Modo aprendizaje: el ratón está sobre ``boton`` de ``menu`` (el principal si no se dice)."""
    if not boton or not ajustes().aprendizaje:
        _ocultar_tarjeta()
        return
    from radial import acciones
    from radial.ayuda import contenido
    try:
        icono = _icono_de_comando(boton["accion"]) if boton.get("tipo") == "comando" else ""
        datos = contenido(boton, _info_de(boton), acciones.estado(boton), _tiene_opciones(boton), icono)
    except Exception:  # la ayuda nunca debe romper el menú
        return
    menu = menu if menu is not None else _menu_flotante(crear=False)
    if menu:
        _tarjeta().mostrar(datos, menu)


def _al_usar(boton):
    """Cuenta los usos de cada comando; a las 3, 10 y 25 veces recuerda su atajo de teclado."""
    if boton.get("tipo") != "comando":
        return
    from radial import reto
    comando = boton.get("accion", "")
    veces = reto.registrar_uso(ajustes().usos, comando)
    ajustes().guardar()
    if veces not in reto.AVISOS or not ajustes().aprendizaje:
        return
    atajo = _atajos().get(comando)
    if atajo:
        texto = t("reto_recuerda", nombre=_nombre_comando(comando), atajo=atajo)
        try:
            cmds.inViewMessage(assistMessage=texto, position="botCenter", fade=True, fadeStayTime=2500)
        except Exception:
            print("Radial: " + texto)


def _atajos():
    if _estado.get("atajos") is None:
        try:
            _estado["atajos"] = _fuentes().atajos()
        except Exception:
            _estado["atajos"] = {}
    return _estado["atajos"]


def _nombre_comando(comando):
    """El nombre en el idioma del alumno si lo hay («Extruir»); si no, el de Maya («Poly Extrude»)."""
    from radial import busqueda
    traducido = sinonimos().get(comando, {}).get("es", "")
    return traducido or busqueda.texto_de_comando(comando)


def abrir_reto():
    """Modo reto: pregunta los atajos de los comandos que más usas."""
    from radial import reto
    _estado["atajos"] = None  # por si se cambió algún atajo en Maya
    lista = reto.preguntas(ajustes().usos, _atajos())
    if not lista:
        cmds.confirmDialog(title=t("reto_titulo"), message=t("reto_sin_atajos"), button=[t("boton_aceptar")])
        return None
    ventana = reto.dialogo(lista, _nombre_comando, padre=ventana_maya())
    _estado["reto"] = ventana
    ventana.show()
    ventana.raise_()
    return ventana


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
    _parar_gesto()
    reloj = _estado.get("reloj_automatico")
    if sigue_vivo(reloj):
        reloj.stop()
    _estado["reloj_automatico"] = None
    tarjeta = _estado.get("tarjeta")
    if sigue_vivo(tarjeta):
        tarjeta.hide()
        destruir(tarjeta)
    _estado["tarjeta"] = None
    for clave in ("configurador", "ventana_ajustes", "gestor", "reto"):
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


# Gesto: Tab, Tab sin soltar el segundo, mover el ratón hacia un botón y soltar.

def _al_doble_tab():
    alternar()
    filtro = _estado.get("filtro")
    if visible() and filtro is not None and filtro.manteniendo:
        _empezar_gesto()


# Sin auto-repetición de Tab en este tiempo (y sin poder preguntar al sistema), se da por soltado.
GESTO_SIN_REPETICION_MS = 1200


def _empezar_gesto():
    from radial.filtro_teclado import _ahora_ms, tab_pulsado
    reloj = _estado.get("reloj_gesto")
    if not sigue_vivo(reloj):
        reloj = QtCore.QTimer(ventana_maya())
        reloj.setInterval(16)
        reloj.timeout.connect(_seguir_gesto)
        _estado["reloj_gesto"] = reloj
    _estado["gesto"] = QtGui.QCursor.pos()
    _estado["gesto_ms"] = _ahora_ms()
    # Si el sistema dice ahora que Tab está pulsada, se le puede preguntar mientras dure el gesto.
    _estado["gesto_nativo"] = tab_pulsado() is True
    # El soltar de Tab puede llegar a la ventana del menú en vez de a la de Maya: se escucha también.
    filtro = _estado.get("filtro")
    menu = _menu_flotante(crear=False)
    if filtro is not None and menu is not None and menu.windowHandle() is not None:
        filtro.escuchar(menu.windowHandle())
    reloj.start()


def _tab_sigue_pulsado(filtro):
    """Si el segundo Tab sigue pulsado, aunque su evento de soltar no haya llegado."""
    from radial.filtro_teclado import _ahora_ms, tab_pulsado
    if _estado.get("gesto_nativo"):
        return tab_pulsado() is not False
    ultimo = max(filtro.ultimo_tab, _estado.get("gesto_ms", 0))
    return _ahora_ms() - ultimo < GESTO_SIN_REPETICION_MS


def _seguir_gesto():
    menu = _menu_flotante(crear=False)
    inicio = _estado.get("gesto")
    filtro = _estado.get("filtro")
    if menu is None or inicio is None or not menu.isVisible() or filtro is None:
        _cancelar_gesto()
        return
    if not filtro.manteniendo:
        _parar_gesto()  # Tab se soltó y su aviso (_al_soltar_tab) ya está en camino
        return
    if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.NoButton:
        filtro.terminar()
        _cancelar_gesto()  # un clic durante el gesto: manda el clic
        return
    if not _tab_sigue_pulsado(filtro):
        # El evento de soltar Tab no ha llegado, pero Tab ya no está pulsada.
        filtro.terminar()
        if _estado.get("gesto_nativo"):
            _al_soltar_tab()  # el sistema lo sabe seguro: cuenta como soltar
        else:
            _cancelar_gesto()
        return
    menu.marcar_gesto(menu.boton_en_gesto(inicio, QtGui.QCursor.pos()))


def _parar_gesto():
    reloj = _estado.get("reloj_gesto")
    if sigue_vivo(reloj):
        reloj.stop()


def _cancelar_gesto():
    """Deja de seguir el ratón sin ejecutar nada y quita el resaltado del gesto."""
    _parar_gesto()
    if _estado.pop("gesto", None) is None:
        return
    menu = _menu_flotante(crear=False)
    if menu is not None and menu.isVisible():
        menu.marcar_gesto(None)


def _al_soltar_tab():
    """Fin del gesto: si apunta a un botón, se ejecuta y el menú se cierra; si no, se queda abierto."""
    _parar_gesto()
    inicio = _estado.pop("gesto", None)
    menu = _menu_flotante(crear=False)
    if inicio is None or menu is None or not menu.isVisible():
        return
    indice = menu.boton_en_gesto(inicio, QtGui.QCursor.pos())
    if indice is None:
        return
    boton = menu.botones_visibles()[indice]
    if boton["tipo"] == "carpeta":
        menu.abrir_carpeta(indice)
        return
    if boton["tipo"] == "vacio":
        return
    from radial import acciones
    acciones.ejecutar(boton)
    ocultar()


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
    filtro = FiltroTeclado(_puede_contar, _al_doble_tab, ajustes().ventana_ms, al_soltar_tab=_al_soltar_tab)
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
    clase = bib.de_clase()
    if bib.carpeta_clase:
        cmds.menuItem(divider=True, dividerLabel=t("menu_de_clase"))
        if not clase:
            cmds.menuItem(label=t("menu_clase_vacia"), enable=False)
        for identificador, nombre, bloqueado in clase:
            cmds.menuItem(label=("\U0001F512 " if bloqueado else "") + nombre, radioButton=identificador == origen,
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
    cmds.menuItem(label=t("menu_exportar_bloqueado"), command=lambda *_: exportar_bloqueado())
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_importar_paquete"), command=lambda *_: importar_paquete())
    cmds.menuItem(label=t("menu_exportar_paquete"), command=lambda *_: exportar_paquete())
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
                      enable=not ({"forma", "pill_vertical"} & set(ajustes().fijadas)),
                      command=lambda *_, f=f, v=v: cambiar_forma(f, v))


def crear_menu():
    from radial import pack
    pack.crear_menu(MENU, t("menu_titulo"))
    cmds.menuItem(label=t("menu_alternar"), command=lambda *_: alternar())
    cmds.menuItem(label=t("menu_configurar"), command=lambda *_: abrir_configurador())
    cmds.menuItem(label=t("menu_grabar"), command=lambda *_: crear_boton_de_lo_ultimo())
    cmds.menuItem(label=t("menu_reto"), command=lambda *_: abrir_reto())
    cmds.menuItem(MENU_RADIALES, label=t("menu_radiales"), subMenu=True, tearOff=True,
                  postMenuCommand=_llenar_radiales)
    cmds.setParent("..", menu=True)
    cmds.menuItem(divider=True)
    cmds.menuItem(MENU_FORMA, label=t("menu_forma"), subMenu=True, postMenuCommand=_llenar_forma)
    cmds.setParent("..", menu=True)
    cmds.menuItem(label=t("menu_ajustes"), command=lambda *_: abrir_ajustes())
    from radial import pill_extra
    cmds.menuItem(pill_extra.MENU_ACTIVA, label=t("menu_pill_extra"), checkBox=pill_extra.ajustes().activa,
                  command=lambda activa, *_: pill_extra.activar(bool(activa)))
    cmds.menuItem(label=t("menu_pill_extra_configurar"), command=lambda *_: pill_extra.abrir_configurador())
    cmds.menuItem(label=t("menu_centrar"), command=lambda *_: volver_a_centrar())
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_comprobar"), command=lambda *_: comprobar())
    cmds.menuItem(label=t("menu_ayuda"), command=lambda *_: _ayuda())
    cmds.menuItem(label=t("menu_acerca"), command=lambda *_: _acerca())
    return MENU


def quitar_menu():
    from radial import pack
    pack.quitar_menu(MENU)


# --- Arranque y parada --------------------------------------------------------

def iniciar():
    """Lo llama el plugin al cargarse."""
    if cmds.about(batch=True):
        return
    try:
        cargar_fijadas()
    except Exception as error:  # una carpeta de clase rota no impide que el plugin cargue
        cmds.warning(str(error))
    from radial import i18n, tema
    if ajustes().idioma:
        i18n.usar_idioma(ajustes().idioma)
    tema.aplicar(ajustes().tema, ajustes().acento)
    from radial import iconos
    iconos.usar_iconos(ajustes().iconos, _icono_de_comando)
    from radial import acciones
    if _al_usar not in acciones.oyentes:
        acciones.oyentes.append(_al_usar)
    crear_menu()
    _crear_comandos()
    # Con Maya ya abierto, no a mitad del arranque.
    QtCore.QTimer.singleShot(2000, _instalar_filtro)
    QtCore.QTimer.singleShot(2500, _iniciar_extra)
    print(t("iniciado", version=radial.__version__))


def _iniciar_extra():
    from radial import pill_extra
    try:
        pill_extra.iniciar()
    except Exception as error:  # la pill extra nunca debe impedir que Maya arranque
        cmds.warning(t("extra_error", error=error))


def detener():
    """Lo llama el plugin al descargarse: quita el filtro, las ventanas y los menús."""
    from radial import acciones, pill_extra
    if _al_usar in acciones.oyentes:
        acciones.oyentes.remove(_al_usar)
    pill_extra.detener()
    _quitar_filtro()
    _cerrar_ventanas()
    _destruir_menu_flotante()
    _destruir_buscador()
    _estado.update(ajustes=None, biblioteca=None, fuentes=None, atajos=None)
    if not cmds.about(batch=True):
        quitar_menu()
