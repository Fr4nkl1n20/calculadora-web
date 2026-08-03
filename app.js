// Conexión entre la lógica (calculadora.js) y el DOM.

const calc = crearCalculadora();

const $resultado = document.getElementById('resultado');
const $historial = document.getElementById('historial');
const $memoria = document.getElementById('memoria');
const $registro = document.getElementById('registro');
const $registroVacio = document.getElementById('registro-vacio');

const ACCIONES = {
  limpiar: () => calc.limpiar(),
  decimal: () => calc.decimal(),
  igual: () => calc.igual(),
  signo: () => calc.signo(),
  porcentaje: () => calc.porcentaje(),
  raiz: () => calc.raiz(),
  borrar: () => calc.borrar(),
  'memoria-sumar': () => calc.memoriaSumar(),
  'memoria-leer': () => calc.memoriaLeer(),
  'memoria-limpiar': () => calc.memoriaLimpiar(),
};

function actualizarPantalla() {
  $resultado.textContent = calc.pantalla();
  $historial.textContent = calc.expresion();
  $memoria.hidden = !calc.memoriaActiva();

  const activo = calc.operadorActivo();
  document.querySelectorAll('.tecla.operador').forEach((tecla) => {
    tecla.classList.toggle('seleccionado', tecla.dataset.operador === activo);
  });

  const entradas = calc.historial();
  $registroVacio.hidden = entradas.length > 0;
  $registro.replaceChildren(
    ...entradas.map((e) => {
      const li = document.createElement('li');
      const op = document.createElement('span');
      op.className = 'registro-operacion';
      op.textContent = e.expresion;
      const res = document.createElement('span');
      res.className = 'registro-resultado';
      res.textContent = e.resultado;
      li.append(op, res);
      return li;
    })
  );
}

// --- Ratón ------------------------------------------------------------

document.querySelector('.teclado').addEventListener('click', (evento) => {
  const tecla = evento.target.closest('.tecla');
  if (!tecla) return;

  const { digito, operador, accion } = tecla.dataset;

  if (digito !== undefined) calc.digito(digito);
  else if (operador !== undefined) calc.operador(operador);
  else if (accion !== undefined) ACCIONES[accion]();

  actualizarPantalla();
});

// --- Teclado ----------------------------------------------------------

const TECLAS_TECLADO = {
  Enter: '[data-accion="igual"]',
  '=': '[data-accion="igual"]',
  Escape: '[data-accion="limpiar"]',
  Backspace: '[data-accion="borrar"]',
  '.': '[data-accion="decimal"]',
  ',': '[data-accion="decimal"]',
  '%': '[data-accion="porcentaje"]',
  r: '[data-accion="raiz"]',
  R: '[data-accion="raiz"]',
  '+': '[data-operador="+"]',
  '-': '[data-operador="-"]',
  '*': '[data-operador="*"]',
  '/': '[data-operador="/"]',
};

document.addEventListener('keydown', (evento) => {
  if (evento.ctrlKey || evento.altKey || evento.metaKey) return;

  const selector = /^[0-9]$/.test(evento.key)
    ? `[data-digito="${evento.key}"]`
    : TECLAS_TECLADO[evento.key];

  if (!selector) return;

  evento.preventDefault();
  const tecla = document.querySelector(selector);
  tecla.click();

  // Realimentación visual de la pulsación.
  tecla.classList.add('activa');
  setTimeout(() => tecla.classList.remove('activa'), 90);
});

actualizarPantalla();

// --- Instalable sin conexión ------------------------------------------

// El service worker sólo funciona sobre http(s); abriendo el archivo con
// file:// no se registra y la calculadora funciona igual.
if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {
      /* sin conexión offline: no es motivo para romper la aplicación */
    });
  });
}
