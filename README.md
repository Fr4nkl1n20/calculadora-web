# Calculadora Web

Calculadora con temática de béisbol, hecha con HTML, CSS y JavaScript puro
(sin dependencias, sin build, sin imágenes de mapa de bits).

**En vivo:** https://fr4nkl1n20.github.io/calculadora-web/

## Uso

Abre `index.html` en cualquier navegador. No hace falta instalar nada.

## Diseño

- Ilustración de cabecera: un león devorando un galeón, dibujada a mano en SVG.
- Marco formado por cuatro bates de béisbol, también en SVG.
- Pantalla estilo marcador de estadio, con dígitos ámbar sobre fondo oscuro.
- Teclas por función: crema para los dígitos, azul marino para las funciones,
  escarlata para los operadores y dorado para el igual.

Todo el arte es vectorial y original, así que escala sin perder nitidez y el
sitio completo pesa unos pocos kilobytes.

## Características

- Operaciones básicas: suma, resta, multiplicación y división.
- Operaciones encadenadas (`2 + 3 + 4` resuelve sobre la marcha).
- Porcentaje, cambio de signo, borrado por dígito (`⌫`) y borrado total (`AC`).
- Soporte de teclado: dígitos, `+ - * /`, `Enter` o `=`, `Escape`, `Backspace`, `,`/`.` y `%`.
- Formato numérico es-VE (punto para miles, coma para decimales).
- Manejo de errores: la división entre cero muestra `Error`.

## Precisión

Un `double` de JavaScript conserva entre 15 y 17 cifras significativas. La
calculadora trabaja con 15, definidas una sola vez en la constante
`CIFRAS_SIGNIFICATIVAS` de `app.js`, que gobierna a la vez cuántos dígitos se
pueden teclear y con cuánta precisión se redondea el resultado.

Mantener ambos límites atados a un mismo valor es lo que evita el fallo: si la
entrada admite más dígitos que la precisión de salida, los números largos se
corrompen en silencio al operar. Redondear a 15 cifras sigue bastando para
ocultar los artefactos de coma flotante (`0,1 + 0,2` da `0,3`).

## Estructura

| Archivo | Contenido |
| --- | --- |
| `index.html` | Estructura: marco de bates, escena, pantalla y teclado |
| `styles.css` | Estilos, marco de bates y disposición en rejilla |
| `app.js` | Lógica de la calculadora y manejo de eventos |
| `assets/escena.svg` | Ilustración del león devorando el galeón |
| `assets/bate-h.svg` | Bate horizontal (bordes superior e inferior) |
| `assets/bate-v.svg` | Bate vertical (bordes laterales) |
