// Calculadora — lógica en JavaScript puro, sin dependencias.

const SIMBOLOS = { '+': '+', '-': '−', '*': '×', '/': '÷' };

// Un double de JavaScript conserva entre 15 y 17 cifras significativas.
// Usamos 15: es el máximo que se puede escribir y devolver sin perder dígitos,
// y sigue bastando para limpiar los artefactos de coma flotante.
// Este valor gobierna a la vez cuánto se puede teclear y con cuánta precisión
// se redondea el resultado; si los dos números se separan, un número más largo
// que la precisión de salida se corrompe en silencio al operar.
const CIFRAS_SIGNIFICATIVAS = 15;

const estado = {
  actual: '0',      // número que se está escribiendo (con '.' interno)
  previo: null,     // operando izquierdo pendiente
  operador: null,   // '+', '-', '*', '/'
  expresion: '',    // línea superior de la pantalla
  sobrescribir: true, // el próximo dígito reemplaza lo mostrado
};

const $resultado = document.getElementById('resultado');
const $historial = document.getElementById('historial');

// --- Formato -----------------------------------------------------------

// Muestra el número al estilo es-VE: punto como separador de miles, coma decimal.
function formatear(valor) {
  if (valor === 'Error') return 'Error';
  if (/e/i.test(valor)) return valor.replace('.', ',');

  const negativo = valor.startsWith('-');
  const [entera, decimal] = (negativo ? valor.slice(1) : valor).split('.');
  const agrupada = entera.replace(/\B(?=(\d{3})+(?!\d))/g, '.');

  return (negativo ? '-' : '') + agrupada + (decimal !== undefined ? ',' + decimal : '');
}

// Convierte un número a string evitando los artefactos de coma flotante
// (0.1 + 0.2 -> "0.3" en vez de "0.30000000000000004").
function aTexto(numero) {
  if (!Number.isFinite(numero)) return 'Error';
  return String(parseFloat(numero.toPrecision(CIFRAS_SIGNIFICATIVAS)));
}

function actualizarPantalla() {
  $resultado.textContent = formatear(estado.actual);
  $historial.textContent = estado.expresion;

  document.querySelectorAll('.tecla.operador').forEach((tecla) => {
    tecla.classList.toggle(
      'seleccionado',
      estado.sobrescribir && tecla.dataset.operador === estado.operador
    );
  });
}

// --- Operaciones -------------------------------------------------------

function calcular(a, b, operador) {
  switch (operador) {
    case '+': return a + b;
    case '-': return a - b;
    case '*': return a * b;
    case '/': return b === 0 ? NaN : a / b;
    default: return b;
  }
}

function limpiar() {
  estado.actual = '0';
  estado.previo = null;
  estado.operador = null;
  estado.expresion = '';
  estado.sobrescribir = true;
}

function ingresarDigito(digito) {
  if (estado.actual === 'Error') limpiar();

  if (estado.sobrescribir) {
    estado.actual = digito;
    estado.sobrescribir = false;
  } else if (estado.actual === '0') {
    estado.actual = digito;
  } else if (estado.actual.replace(/[-.]/g, '').length < CIFRAS_SIGNIFICATIVAS) {
    estado.actual += digito;
  }
}

function ingresarDecimal() {
  if (estado.actual === 'Error') limpiar();

  if (estado.sobrescribir) {
    estado.actual = '0.';
    estado.sobrescribir = false;
  } else if (!estado.actual.includes('.')) {
    estado.actual += '.';
  }
}

function elegirOperador(operador) {
  if (estado.actual === 'Error') return;

  // Encadena: 2 + 3 + -> resuelve el 5 antes de aceptar el nuevo operador.
  if (estado.operador !== null && estado.previo !== null && !estado.sobrescribir) {
    estado.actual = aTexto(
      calcular(Number(estado.previo), Number(estado.actual), estado.operador)
    );
    if (estado.actual === 'Error') {
      estado.previo = null;
      estado.operador = null;
      estado.expresion = '';
      estado.sobrescribir = true;
      return;
    }
  }

  estado.previo = estado.actual;
  estado.operador = operador;
  estado.expresion = `${formatear(estado.actual)} ${SIMBOLOS[operador]}`;
  estado.sobrescribir = true;
}

function igual() {
  if (estado.operador === null || estado.previo === null) return;

  const resultado = aTexto(
    calcular(Number(estado.previo), Number(estado.actual), estado.operador)
  );

  estado.expresion = `${estado.expresion} ${formatear(estado.actual)} =`;
  estado.actual = resultado;
  estado.previo = null;
  estado.operador = null;
  estado.sobrescribir = true;
}

function cambiarSigno() {
  if (estado.actual === 'Error' || estado.actual === '0') return;
  estado.actual = estado.actual.startsWith('-')
    ? estado.actual.slice(1)
    : '-' + estado.actual;
}

function porcentaje() {
  if (estado.actual === 'Error') return;
  estado.actual = aTexto(Number(estado.actual) / 100);
  estado.sobrescribir = false;
}

function borrar() {
  if (estado.sobrescribir || estado.actual === 'Error') {
    estado.actual = '0';
    estado.sobrescribir = false;
    return;
  }
  estado.actual = estado.actual.slice(0, -1);
  if (estado.actual === '' || estado.actual === '-') estado.actual = '0';
}

const ACCIONES = {
  limpiar,
  decimal: ingresarDecimal,
  igual,
  signo: cambiarSigno,
  porcentaje,
  borrar,
};

// --- Eventos -----------------------------------------------------------

document.querySelector('.teclado').addEventListener('click', (evento) => {
  const tecla = evento.target.closest('.tecla');
  if (!tecla) return;

  const { digito, operador, accion } = tecla.dataset;

  if (digito !== undefined) ingresarDigito(digito);
  else if (operador !== undefined) elegirOperador(operador);
  else if (accion !== undefined) ACCIONES[accion]();

  actualizarPantalla();
});

const TECLAS_TECLADO = {
  Enter: '[data-accion="igual"]',
  '=': '[data-accion="igual"]',
  Escape: '[data-accion="limpiar"]',
  Backspace: '[data-accion="borrar"]',
  '.': '[data-accion="decimal"]',
  ',': '[data-accion="decimal"]',
  '%': '[data-accion="porcentaje"]',
  '+': '[data-operador="+"]',
  '-': '[data-operador="-"]',
  '*': '[data-operador="*"]',
  '/': '[data-operador="/"]',
};

document.addEventListener('keydown', (evento) => {
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
