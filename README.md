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

## Limitación conocida

Los resultados se redondean a 12 cifras significativas (`toPrecision(12)` en
`aTexto`), pero la interfaz permite escribir hasta 15 dígitos. Un número de más
de 12 dígitos pierde precisión al operar: `123456789012345 + 0` devuelve
`123.456.789.012.000`. Se corrige alineando ambos límites.

## Estructura

| Archivo | Contenido |
| --- | --- |
| `index.html` | Estructura: marco de bates, escena, pantalla y teclado |
| `styles.css` | Estilos, marco de bates y disposición en rejilla |
| `app.js` | Lógica de la calculadora y manejo de eventos |
| `assets/escena.svg` | Ilustración del león devorando el galeón |
| `assets/bate-h.svg` | Bate horizontal (bordes superior e inferior) |
| `assets/bate-v.svg` | Bate vertical (bordes laterales) |
