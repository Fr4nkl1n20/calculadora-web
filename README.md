# Calculadora Web

Calculadora hecha con HTML, CSS y JavaScript puro (sin dependencias ni build).

## Uso

Abre `index.html` en cualquier navegador. No hace falta instalar nada.

## Características

- Operaciones básicas: suma, resta, multiplicación y división.
- Operaciones encadenadas (`2 + 3 + 4` resuelve sobre la marcha).
- Porcentaje, cambio de signo, borrado por dígito (`⌫`) y borrado total (`AC`).
- Soporte de teclado: dígitos, `+ - * /`, `Enter` o `=`, `Escape`, `Backspace`, `,`/`.` y `%`.
- Formato numérico es-VE (punto para miles, coma para decimales).
- Tema claro y oscuro automático según las preferencias del sistema.
- Manejo de errores: la división entre cero muestra `Error`.

## Estructura

| Archivo | Contenido |
| --- | --- |
| `index.html` | Estructura de la pantalla y el teclado |
| `styles.css` | Estilos, tema claro/oscuro y disposición en rejilla |
| `app.js` | Lógica de la calculadora y manejo de eventos |
