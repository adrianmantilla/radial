"""Plugin de Maya para Radial.

Aparece en el Plug-in Manager como «radial_plugin». Al cargarlo crea el menú
Radial en la barra de Maya y empieza a escuchar el doble Tab; al descargarlo
lo quita todo. El instalador lo marca para que se cargue solo cada vez que se
abre Maya.
"""

import maya.api.OpenMaya as om
from maya import cmds


def maya_useNewAPI():
    pass


def initializePlugin(objeto):
    import radial
    plugin = om.MFnPlugin(objeto, "Radial", radial.__version__, "Any")
    try:
        from radial import interfaz_maya
        cmds.evalDeferred(interfaz_maya.iniciar, lowestPriority=True)
    except Exception as error:
        cmds.warning("Radial no se pudo cargar: {}".format(error))
    return plugin


def uninitializePlugin(objeto):
    try:
        from radial import interfaz_maya
        interfaz_maya.detener()
    except Exception:
        pass
