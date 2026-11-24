# Radial

Menú flotante de seis botones para Autodesk Maya 2026 y 2027, en Windows y macOS.
Pon el ratón sobre un visor y pulsa **Tab dos veces rápido**: aparece el menú. Otro doble Tab lo oculta.
Cada botón lanza la orden de Maya que tú elijas.

![Radial](docs/radial.png)

- Dos formas a juego: **radial** (seis puntos en un anillo) y **pill** (una cápsula, horizontal o vertical).
- Cada botón puede ser un comando de Maya, un botón de cualquier estante, código Python o código MEL.
- Cuatro radiales preconfigurados (Modelado, UV y texturas, Animación y Render con Arnold) y los tuyos propios.
- Se guarda, se exporta y se comparte como un archivo `.radial`.
- No cambia ningún atajo de Maya.

No necesita instalar nada más: funciona con el Python que trae Maya. Versión **1.0.0**.

> *English summary:* Radial is a floating six-button menu for Maya 2026/2027 (Windows and macOS). Hover a
> viewport and press **Tab twice quickly** to show or hide it. Buttons can run any Maya command, a shelf
> button, Python or MEL. Comes as a ring or a pill, with presets you can save and share as `.radial` files.
> Install by dragging `instalar.py` into the viewport. The interface is in Spanish and ready to translate
> (`scripts/radial/i18n/`). MIT licence.

## Instalar

1. Descarga o clona esta carpeta donde quieras dejarla, por ejemplo `Documentos/Plugins/Radial`.
   No la muevas después de instalar (si la mueves, repite el paso 2).
2. Abre Maya y **arrastra el archivo `instalar.py` hasta el visor**.

Aparece el menú **Radial** en la barra de Maya y el plugin se cargará solo cada vez que abras Maya.
Si algo falla, usa **Radial > Comprobar instalación**.

Para actualizar a una versión nueva, sustituye la carpeta y vuelve a arrastrar `instalar.py`.
Tus radiales y ajustes se conservan.

## Cómo se usa

| Qué | Cómo |
| --- | --- |
| Mostrar u ocultar el menú | Tab dos veces rápido con el ratón sobre un visor 3D, o **Radial > Mostrar/ocultar menú** |
| Usar un botón | Acerca el ratón: el botón se vuelve blanco y aparece su nombre. Haz clic |
| Mover el menú | Arrástralo desde el centro (en la pill, desde los puntitos del extremo). Recuerda dónde lo dejas |
| Cambiar los botones | Clic derecho en el centro, o **Radial > Configurar botones** |
| Cambiar de radial | **Radial > Radiales** |
| Radial o pill | **Radial > Forma**, o en **Radial > Ajustes** |
| Tamaño, opacidad y velocidad | **Radial > Ajustes** (se ve al momento en el menú) |
| Volver a sacarlo bajo el ratón | **Radial > Volver a sacar el menú bajo el ratón** |
| Usar otra tecla | En el Editor de atajos, categoría *Custom Scripts*: `RadialMostrarOcultar` y `RadialConfigurar` |

El menú sigue a la vista después de pulsar un botón, hasta el siguiente doble Tab.
Fuera de los botones, la línea y el centro, los clics pasan a Maya, así que puedes seguir trabajando con él abierto.

### Cuándo cuenta el doble Tab

- Los dos Tab tienen que llegar en menos de 250 ms (se cambia en Ajustes, entre 150 y 400 ms).
- El primer Tab llega a Maya como siempre; el plugin solo se queda con el segundo.
- No cuenta con Mayúsculas, Ctrl, Cmd u Opción pulsadas, ni al dejar Tab pulsado.
- No cuenta mientras escribes en un campo de texto, el Script Editor o la Caja de canales.
- Con el menú oculto solo cuenta sobre un visor 3D, así que el Tab del Editor de nodos y del
  Hypershade (abrir el buscador de nodos) funciona igual que siempre.

## Configurar los botones

**Radial > Configurar botones** (o clic derecho en el centro del menú). A la izquierda están los seis
huecos: arrástralos para cambiar el orden. El 1 va arriba y los demás siguen el sentido del reloj.
Para cada botón eliges:

- **Texto** y una **segunda línea** opcional.
- **Icono**: uno de los iconos de línea del plugin, cualquier icono de Maya (con buscador) o ninguno
  (se ve la inicial del texto).
- **Acción**:

| Tipo | Qué hace |
| --- | --- |
| Comando de Maya | Cualquiera de los comandos del Editor de atajos, con buscador (casi todo lo que hay en los menús) |
| Botón del estante | Copia la orden, el icono y el texto de un botón de cualquier estante |
| Código Python / MEL | Tus propias líneas. Se deshacen de una vez con Ctrl+Z |
| Vacío | No hace nada; el botón se ve atenuado |

**Probar este botón** lo ejecuta sin cerrar la ventana. Los cambios se ven en el menú al momento y se
recuerdan aunque cierres Maya, pero no se escriben en el archivo del radial hasta que pulsas **Guardar**.
Los radiales preconfigurados no se modifican nunca: sus cambios se guardan como radial nuevo.

## Radiales

Un radial es un juego de seis botones más su tamaño y su opacidad. En **Radial > Radiales**:

- **Preconfigurados**: Modelado, UV y texturas, Animación y Render con Arnold. Vienen con el plugin.
- **Mis radiales**: los que guardas tú. Están en la carpeta `radial/radiales` de tus preferencias de Maya
  (la ruta exacta sale en **Comprobar instalación**).
- **Guardar cambios**, **Guardar como nuevo radial**, **Descartar cambios sin guardar**.
- **Exportar el radial activo** crea un archivo `.radial`. Para repartirlo en clase, cada alumno lo carga
  con **Importar desde archivo**.
- **Gestionar mis radiales** abre una ventana para usar, renombrar, duplicar, exportar y borrar.

## Desinstalar

Borra el archivo `radial.mod` de la carpeta `modules` de tus preferencias de Maya
(la ruta exacta se escribe en el Script Editor al instalar) y desactiva `radial_plugin`
en el Plug-in Manager. Tus radiales quedan en la carpeta `radial` de las preferencias por si vuelves.

## Idiomas

Los textos están en `scripts/radial/i18n/es.json`. Para traducir, copia ese archivo como
`en.json` (u otro código), traduce los valores y define la variable de entorno
`RADIAL_IDIOMA=en` antes de abrir Maya.

## Formato `.radial`

JSON con el nombre, los seis botones y la apariencia:

```json
{
  "formato": 1,
  "nombre": "Modelado",
  "botones": [
    {"texto": "Centrar", "detalle": "pivote", "icono": "pivote", "tipo": "comando", "accion": "CenterPivot"},
    {"texto": "Cubo", "detalle": "", "icono": ":/polyCube.png", "tipo": "mel", "accion": "polyCube;"}
  ],
  "apariencia": {"radio": 84, "punto": 5, "abierto": 21, "opacidad": 1.0, "pill_boton": 32}
}
```

`tipo` es `comando`, `python`, `mel` o `vacio`. Si faltan botones se rellenan vacíos, y los valores
fuera de rango se ajustan al cargar.

## Para desarrollar

```
instalar.py                  arrastrar al visor para instalar
plug-ins/radial_plugin.py    plugin de Maya (crea el menú y activa el doble Tab)
scripts/radial/
  detector_tab.py            cuándo dos Tab son un doble Tab (sin Maya)
  filtro_teclado.py          escucha el teclado de Maya
  menu_radial.py             el menú en forma de anillo de puntos
  menu_pill.py               el menú en forma de pill
  dibujo.py                  colores e iconos compartidos
  configurador.py            ventana para configurar los botones
  ventana_ajustes.py         ventana de ajustes
  gestor_radiales.py         ventana de mis radiales
  biblioteca.py              radial activo, guardar, importar y exportar (sin Maya)
  radiales.py                formato .radial y geometría de los menús (sin Maya)
  ajustes.py                 preferencias del usuario (sin Maya)
  acciones.py                ejecutar un botón
  fuentes_maya.py            comandos, estantes e iconos de Maya
  iconos.py                  iconos de línea
  interfaz_maya.py           menú de la barra y conexión con Maya
  preconfigurados/           radiales que vienen con el plugin
  i18n/                      textos por idioma
herramientas/prueba_maya.py  prueba dentro de Maya con mayapy
tests/                       pruebas sin Maya: python3 -m unittest discover tests
```

Las pruebas de `tests/test_qt.py` y `tests/test_interfaz.py` usan Qt sin pantalla si tienes PySide6
(`pip install PySide6-Essentials`); si no, se saltan.

## Licencia

MIT. Consulta `LICENSE`.
