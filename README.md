# Radial

Menú radial de seis botones para Autodesk Maya 2026 y 2027 (Windows y macOS), pensado para estudiantes.
Pon el ratón sobre un visor y pulsa **Tab dos veces rápido**: aparece el menú. Otro doble Tab lo oculta.
Cada botón lanza una orden de Maya.

> **Estado: fases 0 y 1.** Instalación, menú Radial, doble Tab y menú flotante con el radial
> «Modelado». El configurador de botones, la ventana de ajustes y guardar/cargar radiales llegan
> en las fases siguientes.

No necesita instalar nada más: funciona con el Python que trae Maya.

## Instalar

1. Descarga o clona esta carpeta donde quieras dejarla, por ejemplo `Documentos/Plugins/Radial`.
   No la muevas después de instalar (si la mueves, repite el paso 2).
2. Abre Maya y **arrastra el archivo `instalar.py` hasta el visor**.

Aparece el menú **Radial** en la barra de Maya y se cargará solo cada vez que abras Maya.
Si algo falla, usa **Radial > Comprobar instalación**.

## Cómo se usa

| Qué | Cómo |
| --- | --- |
| Mostrar u ocultar el menú | Tab dos veces rápido con el ratón sobre un visor 3D (o **Radial > Mostrar/ocultar radial**) |
| Usar un botón | Acerca el ratón a un punto: se abre y el nombre aparece en el centro. Haz clic |
| Mover el menú | Arrástralo desde el círculo del centro. Recuerda dónde lo dejaste |
| Volver a sacarlo bajo el ratón | **Radial > Volver a sacar el radial bajo el ratón** |
| Usar otra tecla | En el Editor de atajos, categoría *Custom Scripts*, comando `RadialMostrarOcultar` |

El menú sigue a la vista después de pulsar un botón, hasta el siguiente doble Tab.
Fuera de los puntos, la línea y el centro, los clics pasan a Maya.

### Cuándo cuenta el doble Tab

- Los dos Tab tienen que llegar en menos de 250 ms.
- El primer Tab llega a Maya como siempre; el plugin solo se queda con el segundo.
- No cuenta con Mayúsculas, Ctrl, Cmd u Opción pulsadas, ni al dejar Tab pulsado.
- No cuenta mientras escribes en un campo de texto, el Script Editor o la Caja de canales.
- Con el menú oculto solo cuenta sobre un visor 3D, así que el Tab del Editor de nodos y del
  Hypershade (abrir el buscador de nodos) sigue igual.

El plugin no cambia ningún atajo de Maya: escucha las teclas que llegan a la ventana de Maya.

## Desinstalar

Borra el archivo `radial.mod` de la carpeta `modules` de tus preferencias de Maya
(la ruta exacta se escribe en el Script Editor al instalar) y desactiva `radial_plugin`
en el Plug-in Manager.

## Radiales

Un radial es un juego de seis botones más su tamaño, guardado como JSON (`.radial`).
Los que vienen con el plugin están en `scripts/radial/preconfigurados/` y se eligen en
**Radial > Radiales**. Cada botón tiene un tipo:

| Tipo | Acción |
| --- | --- |
| `comando` | Un comando de Maya, con el mismo nombre que en el Editor de atajos (`CenterPivot`) |
| `python` | Código Python |
| `mel` | Código MEL |
| `vacio` | Nada (el punto se ve atenuado) |

## Idiomas

Los textos están en `scripts/radial/i18n/es.json`. Para traducir, copia ese archivo como
`en.json` (u otro código), traduce los valores y define la variable de entorno
`RADIAL_IDIOMA=en` antes de abrir Maya.

## Estructura

```
instalar.py                  arrastrar al visor para instalar
plug-ins/radial_plugin.py    plugin de Maya (crea el menú y activa el doble Tab)
scripts/radial/
  detector_tab.py            cuándo dos Tab son un doble Tab (no depende de Maya)
  filtro_teclado.py          escucha el teclado de Maya
  menu_radial.py             el menú flotante (Qt)
  radiales.py                leer y comprobar radiales, geometría del menú (no depende de Maya)
  ajustes.py                 radial activo, posición y velocidad (no depende de Maya)
  acciones.py                ejecutar el botón
  iconos.py                  iconos de línea
  interfaz_maya.py           menú de la barra y conexión con Maya
  preconfigurados/           radiales que vienen con el plugin
  i18n/                      textos por idioma
herramientas/
  prueba_maya.py             prueba dentro de Maya con mayapy
tests/                       pruebas sin Maya: python3 -m unittest discover tests
```

`tests/test_qt.py` prueba el filtro de teclado y el menú con Qt sin pantalla si tienes
PySide6 instalado (`pip install PySide6-Essentials`); si no, se salta.
