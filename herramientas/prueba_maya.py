"""Prueba de Radial 1.2 dentro de Maya, sin interfaz (herramienta de desarrollo).

Desde la terminal, con el mayapy de cada versión:

    /Applications/Autodesk/maya2027/Maya.app/Contents/bin/mayapy herramientas/prueba_maya.py
    "C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe" herramientas\\prueba_maya.py

No toca tus preferencias de Maya. Comprueba que el plugin carga, que todos los
comandos de los radiales preconfigurados existen en esta versión de Maya, que
los botones se ejecutan, que la lista de comandos y los iconos de Maya se leen
y que guardar, exportar e importar radiales funciona. El doble Tab y el menú flotante necesitan la interfaz
de Maya: pruébalos abriendo Maya normalmente.
Termina con «RESULTADO: OK» o con la lista de fallos.
"""

import os
import sys
import traceback

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

fallos = []


def comprobar(condicion, texto):
    print(("  ok    " if condicion else "  FALLO ") + texto)
    if not condicion:
        fallos.append(texto)


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds

    print("Maya", cmds.about(version=True), "-", cmds.about(operatingSystem=True))

    ruta_plugin = os.path.join(RAIZ, "plug-ins", "radial_plugin.py")
    cmds.loadPlugin(ruta_plugin)
    comprobar(cmds.pluginInfo("radial_plugin", query=True, loaded=True), "el plugin se carga")

    from radial import acciones, radiales as rd
    for identificador, ruta in rd.preconfigurados():
        radial = rd.leer(ruta)
        for i, boton in enumerate(radial["botones"]):
            if boton["tipo"] == "comando":
                comprobar(acciones.comando_existe(boton["accion"]),
                          "{} · botón {}: existe el comando {}".format(identificador, i + 1, boton["accion"]))

    # Ejecutar botones de cada tipo sobre una escena de prueba
    cubo = cmds.polyCube(name="radial_prueba")[0]
    cmds.move(3, 2, 1, cubo)
    cmds.select(cubo)
    comprobar(acciones.ejecutar({"texto": "Congelar", "tipo": "comando", "accion": "FreezeTransformations"}),
              "un comando de Maya se ejecuta")
    comprobar(cmds.getAttr(cubo + ".translate")[0] == (0.0, 0.0, 0.0), "Congelar transformaciones funcionó")
    comprobar(acciones.ejecutar({"texto": "Python", "tipo": "python",
                                 "accion": "from maya import cmds\ncmds.polySphere(name='radial_esfera')"}),
              "código Python se ejecuta")
    comprobar(cmds.objExists("radial_esfera"), "el código Python creó la esfera")
    comprobar(acciones.ejecutar({"texto": "MEL", "tipo": "mel", "accion": 'polyCylinder -name "radial_cilindro";'}),
              "código MEL se ejecuta")
    comprobar(cmds.objExists("radial_cilindro"), "el código MEL creó el cilindro")
    cmds.undo()
    comprobar(not cmds.objExists("radial_cilindro"), "un Ctrl+Z deshace el botón MEL")
    comprobar(not acciones.ejecutar({"texto": "Roto", "tipo": "python", "accion": "1/0"}),
              "un botón con error avisa sin romper nada")
    comprobar(not acciones.ejecutar({"texto": "No existe", "tipo": "comando", "accion": "ComandoQueNoExiste"}),
              "un comando inexistente avisa sin romper nada")

    # Fuentes del configurador
    from radial import fuentes_maya
    fuentes = fuentes_maya.FuentesMaya()
    comandos = fuentes.comandos()
    comprobar(len(comandos) > 500, "la lista de comandos del Editor de atajos se lee ({})".format(len(comandos)))
    comprobar(any(c[0] == "CenterPivot" for c in comandos), "CenterPivot está en la lista de comandos")
    try:
        iconos = fuentes.iconos_maya("polyCube")
    except RuntimeError:
        iconos = []
    comprobar(bool(iconos), "los iconos de Maya se encuentran ({})".format(len(iconos)))

    # 1.1: buscador en español, atajos, opciones, interruptores y radial automático
    from radial import acciones as acc, automatico, interruptores
    from radial.i18n import sinonimos
    existentes = {c[0] for c in comandos}
    traducidos = sinonimos("es")
    faltan = sorted(n for n in traducidos if n not in existentes and not acc.comando_existe(n))
    comprobar(len(faltan) <= len(traducidos) // 10,
              "los comandos traducidos existen ({} de {})".format(len(traducidos) - len(faltan), len(traducidos)))
    if faltan:
        print("        no existen: " + ", ".join(faltan))
    muestra = ["PolyExtrude", "CenterPivot", "BevelPolygon", "UVEditor", "Hypershade", "CreatePolygonCube",
               "FreezeTransformations", "MultiCutTool", "DeleteHistory", "RenderViewWindow"]
    con_icono = {n: fuentes.icono_de_comando(n) for n in muestra}
    comprobar(sum(1 for v in con_icono.values() if v) >= len(muestra) // 2,
              "el buscador encuentra iconos de Maya ({} de {})".format(sum(1 for v in con_icono.values() if v),
                                                                     len(muestra)))
    print("        iconos: " + ", ".join("{}={}".format(k, v or "-") for k, v in con_icono.items()))
    atajos = fuentes.atajos()
    comprobar(isinstance(atajos, dict), "los atajos de teclado se leen ({})".format(len(atajos)))
    comprobar(acc.comando_de_opciones({"tipo": "comando", "accion": "DuplicateSpecial"}) is not None,
              "Mayús + clic encuentra DuplicateSpecialOptions")
    for clave in interruptores.ORDEN:
        try:
            antes = interruptores.encendido(clave)
            comprobar(antes in (True, False), "el interruptor {} se lee".format(clave))
        except Exception as error:  # noqa: BLE001
            comprobar(False, "el interruptor {} se lee ({})".format(clave, error))
    for clave in ("snap_rejilla", "snap_vertice", "simetria"):
        try:
            antes = interruptores.encendido(clave)
            interruptores.alternar(clave)
            cambiado = interruptores.encendido(clave) != antes
            interruptores.alternar(clave)
            comprobar(cambiado and interruptores.encendido(clave) == antes,
                      "el interruptor {} se enciende y se apaga".format(clave))
        except Exception as error:  # noqa: BLE001
            comprobar(False, "el interruptor {} se enciende y se apaga ({})".format(clave, error))
    try:
        contexto = automatico.contexto_maya()
        comprobar(len(contexto) == 2, "el radial automático lee el contexto {}".format(contexto))
    except Exception as error:  # noqa: BLE001
        comprobar(False, "el radial automático lee el contexto ({})".format(error))
    print("        workspaces: " + ", ".join(automatico.workspaces_maya()))

    # Biblioteca: guardar, exportar e importar en una carpeta temporal
    import tempfile
    from radial import ajustes as aj, biblioteca as bib
    with tempfile.TemporaryDirectory() as tmp:
        b = bib.Biblioteca(aj.Ajustes(tmp), os.path.join(tmp, "radiales"))
        radial = b.activo
        radial["botones"][0]["texto"] = "Prueba"
        b.modificar(radial)
        comprobar(not b.guardar_cambios(), "un preconfigurado no se sobrescribe")
        b.guardar_como("Mi prueba")
        comprobar(b.origen.startswith("mio:") and not b.sin_guardar, "guardar como nuevo radial")
        ruta = os.path.join(tmp, "exportado.radial")
        b.exportar(ruta)
        comprobar(os.path.isfile(ruta), "exportar crea el archivo .radial")
        b.importar(ruta)
        comprobar(b.activo["nombre"].startswith("Mi prueba") and len(b.mios()) == 2,
                  "importar el archivo exportado")
        clase = os.path.join(tmp, "clase")
        os.makedirs(clase)
        b.exportar(os.path.join(clase, "examen"), bloqueado=True)
        b.ajustes.carpeta_clase = clase
        b.usar("clase:examen")
        comprobar(b.es_de_clase and b.es_preconfigurado and not b.guardar_cambios(),
                  "un radial de clase bloqueado no se sobrescribe")

    cmds.unloadPlugin("radial_plugin")
    comprobar(not cmds.pluginInfo("radial_plugin", query=True, loaded=True), "el plugin se descarga")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        fallos.append("error inesperado")
    print()
    print("RESULTADO: OK" if not fallos else "RESULTADO: {} fallos".format(len(fallos)))
    sys.stdout.flush()  # os._exit no vacía la salida si va a una tubería
    os._exit(0 if not fallos else 1)
