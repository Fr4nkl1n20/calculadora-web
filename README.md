# Calculadora Web

[![Pruebas](https://github.com/Fr4nkl1n20/calculadora-web/actions/workflows/pruebas.yml/badge.svg)](https://github.com/Fr4nkl1n20/calculadora-web/actions/workflows/pruebas.yml)

Dos calculadoras en el mismo sitio, sin dependencias ni build:

| | Motor | Enlace |
| --- | --- | --- |
| **Básica**, con temática de pesca y tecnología | JavaScript | https://fr4nkl1n20.github.io/calculadora-web/ |
| **Científica**, con todo lo de un modelo fx | Python sobre Pyodide | https://fr4nkl1n20.github.io/calculadora-web/cientifica/ |

La científica está documentada aparte en [`cientifica/README.md`](cientifica/README.md):
trigonometría en tres unidades angulares, complejos, estadística con regresión,
ecuaciones, cálculo numérico, base-N, unidades y constantes físicas.

El resto de este archivo describe la **calculadora básica**.

## Uso

Abre `index.html` en cualquier navegador. No hace falta instalar nada.

Desde el sitio publicado también puedes **instalarla** como aplicación (el
navegador ofrece «Instalar» en la barra de direcciones). Una vez instalada
funciona sin conexión.

## Operaciones

- Suma, resta, multiplicación, división y raíz cuadrada.
- Operaciones encadenadas: `2 + 3 + 4` resuelve sobre la marcha.
- **Porcentaje contextual**: con `+` y `−` es una fracción del operando
  izquierdo (`200 + 10 %` da `220`); con `×` y `÷` divide entre 100.
- **Repetir**: volver a pulsar `=` repite la última operación
  (`2 + 3 =` da `5`, pulsar `=` otra vez da `8`).
- **Memoria**: `M+` acumula, `MR` recupera, `MC` vacía. Un indicador rojo `M`
  se enciende en la pantalla mientras haya un valor guardado.
- **Historial** de las últimas 20 operaciones, desplegable bajo el teclado.
- Cambio de signo, borrado por dígito (`⌫`) y borrado total (`AC`).
- La división entre cero y la raíz de un negativo muestran `Error`.

## Teclado

| Tecla | Acción |
| --- | --- |
| `0`–`9` | Dígitos |
| `+` `-` `*` `/` | Operadores |
| `Enter` o `=` | Igual |
| `Escape` | Borrar todo |
| `Backspace` | Borrar un dígito |
| `,` o `.` | Coma decimal |
| `%` | Porcentaje |
| `r` | Raíz cuadrada |

## Pruebas

Los 63 casos están en `pruebas/casos.js` y se ejecutan de dos formas, sobre la
misma definición:

```bash
npm test                          # en Node, es lo que corre GitHub Actions
```

```
pruebas/index.html                # ábrelo en el navegador para verlos en tabla
```

GitHub Actions las ejecuta en cada push a `main` y en cada pull request.

## Precisión

Un `double` de JavaScript conserva entre 15 y 17 cifras significativas. La
calculadora trabaja con 15, definidas una sola vez en la constante
`CIFRAS_SIGNIFICATIVAS`, que gobierna a la vez cuántos dígitos se pueden
teclear y con cuánta precisión se redondea el resultado.

Mantener ambos límites atados a un mismo valor es lo que evita un fallo real:
si la entrada admite más dígitos que la precisión de salida, los números largos
se corrompen en silencio al operar. Redondear a 15 cifras sigue bastando para
ocultar los artefactos de coma flotante (`0,1 + 0,2` da `0,3`).

## Diseño

Tema de pesca con tecnología, apoyado en una analogía visual: **una red de
pesca y un grafo neuronal son la misma figura** — nudos unidos por hilos. La
malla de la ilustración es literalmente las dos cosas a la vez.

- Ilustración de cabecera: un pez formado por trazas de circuito impreso,
  atrapado en una red cuyos nudos son nodos luminosos. Dibujada a mano en SVG.
- Marco formado por cuatro cañas de pescar, con empuñadura de corcho,
  portacarrete con testigo encendido y una traza luminosa recorriendo el tramo.
- Pantalla estilo sonar: dígitos cian sobre fondo oscuro, con líneas de barrido.
- Teclas por función: hielo los dígitos, azul profundo las funciones, verde
  azulado los operadores, ámbar el igual y cian sobre azul la memoria.
- El único color cálido de la escena es el ojo del pez y sus vías; sirve para
  separarlo del cian de la red y dar un punto de atención.

Todo el arte es vectorial y original, así que escala sin perder nitidez.

## Estructura

| Archivo | Contenido |
| --- | --- |
| `index.html` | Estructura: marco, escena, pantalla, teclado e historial |
| `styles.css` | Estilos y disposición |
| `calculadora.js` | Lógica pura, sin DOM: es lo que se prueba en Node |
| `app.js` | Conexión con el DOM, teclado y registro del service worker |
| `sw.js` | Service worker: caché para funcionar sin conexión |
| `manifest.webmanifest` | Metadatos para instalarla como aplicación |
| `pruebas/casos.js` | Los 63 casos, compartidos por ambos ejecutores |
| `pruebas/calculadora.test.js` | Ejecutor de Node |
| `pruebas/index.html` | Ejecutor de navegador |
| `assets/escena.svg` | Ilustración del pez de circuitos en la red neuronal |
| `assets/cana-h.svg`, `assets/cana-v.svg` | Cañas del marco |
| `assets/icono.svg`, `assets/icono-*.png` | Iconos de la aplicación |

`calculadora.js` está separado de `app.js` a propósito: al no tocar el DOM,
puede probarse en Node sin navegador, que es lo que hace CI rápido y fiable.

## Al modificar algo

Si cambias un archivo de la aplicación, sube `VERSION` en `sw.js`. Si no, los
navegadores que ya la tengan instalada seguirán sirviendo la copia guardada en
caché y no verán el cambio.
