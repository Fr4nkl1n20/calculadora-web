// Lógica de la calculadora. No toca el DOM a propósito: así puede probarse en
// Node sin navegador. En el navegador se carga como script clásico y define
// crearCalculadora en el ámbito global; en Node se importa con require.

// Un double de JavaScript conserva entre 15 y 17 cifras significativas.
// Usamos 15: es el máximo que se puede escribir y devolver sin perder dígitos,
// y sigue bastando para limpiar los artefactos de coma flotante.
// Este valor gobierna a la vez cuánto se puede teclear y con cuánta precisión
// se redondea el resultado; si los dos números se separan, un número más largo
// que la precisión de salida se corrompe en silencio al operar.
const CIFRAS_SIGNIFICATIVAS = 15;

const SIMBOLOS = { '+': '+', '-': '−', '*': '×', '/': '÷' };

const LIMITE_HISTORIAL = 20;

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

function calcular(a, b, operador) {
  switch (operador) {
    case '+': return a + b;
    case '-': return a - b;
    case '*': return a * b;
    case '/': return b === 0 ? NaN : a / b;
    default: return b;
  }
}

function crearCalculadora() {
  const estado = {
    actual: '0',           // número que se está escribiendo (con '.' interno)
    previo: null,          // operando izquierdo pendiente
    operador: null,        // '+', '-', '*', '/'
    expresion: '',         // línea superior de la pantalla
    sobrescribir: true,    // el próximo dígito reemplaza lo mostrado
    operandoListo: false,  // `actual` es un operando derecho aún sin consumir
    repetirOperador: null, // para repetir la última operación al volver a pulsar =
    repetirOperando: null,
    memoria: 0,
    historial: [],
  };

  function registrar(expresion, resultado) {
    estado.historial.unshift({ expresion, resultado: formatear(resultado) });
    if (estado.historial.length > LIMITE_HISTORIAL) estado.historial.pop();
  }

  function fijarError() {
    estado.actual = 'Error';
    estado.previo = null;
    estado.operador = null;
    estado.expresion = '';
    estado.sobrescribir = true;
    estado.operandoListo = false;
    estado.repetirOperador = null;
    estado.repetirOperando = null;
  }

  function limpiar() {
    estado.actual = '0';
    estado.previo = null;
    estado.operador = null;
    estado.expresion = '';
    estado.sobrescribir = true;
    estado.operandoListo = false;
    estado.repetirOperador = null;
    estado.repetirOperando = null;
  }

  function digito(d) {
    if (estado.actual === 'Error') limpiar();

    if (estado.sobrescribir) {
      estado.actual = d;
      estado.sobrescribir = false;
    } else if (estado.actual === '0' || estado.actual === '-0') {
      // '-0' aparece al pulsar +/− antes de teclear el número: conserva el signo.
      estado.actual = (estado.actual === '-0' ? '-' : '') + d;
    } else if (estado.actual.replace(/[-.]/g, '').length < CIFRAS_SIGNIFICATIVAS) {
      estado.actual += d;
    }
    estado.operandoListo = true;
  }

  function decimal() {
    if (estado.actual === 'Error') limpiar();

    if (estado.sobrescribir) {
      estado.actual = '0.';
      estado.sobrescribir = false;
    } else if (!estado.actual.includes('.')) {
      estado.actual += '.';
    }
    estado.operandoListo = true;
  }

  function operador(op) {
    if (estado.actual === 'Error') return;

    // Encadena: 2 + 3 + resuelve el 5 antes de aceptar el nuevo operador.
    if (estado.operador !== null && estado.previo !== null && estado.operandoListo) {
      const resultado = aTexto(
        calcular(Number(estado.previo), Number(estado.actual), estado.operador)
      );
      if (resultado === 'Error') { fijarError(); return; }
      registrar(
        `${formatear(estado.previo)} ${SIMBOLOS[estado.operador]} ${formatear(estado.actual)}`,
        resultado
      );
      estado.actual = resultado;
    }

    estado.previo = estado.actual;
    estado.operador = op;
    estado.expresion = `${formatear(estado.actual)} ${SIMBOLOS[op]}`;
    estado.sobrescribir = true;
    estado.operandoListo = false;
  }

  function igual() {
    let izquierdo, derecho, op;

    if (estado.operador !== null && estado.previo !== null) {
      izquierdo = estado.previo;
      derecho = estado.actual;
      op = estado.operador;
    } else if (estado.repetirOperador !== null && estado.actual !== 'Error') {
      // Volver a pulsar = repite la última operación sobre el resultado.
      izquierdo = estado.actual;
      derecho = estado.repetirOperando;
      op = estado.repetirOperador;
    } else {
      return;
    }

    const resultado = aTexto(calcular(Number(izquierdo), Number(derecho), op));
    const expresion = `${formatear(izquierdo)} ${SIMBOLOS[op]} ${formatear(derecho)}`;

    if (resultado === 'Error') { fijarError(); return; }

    registrar(expresion, resultado);
    estado.expresion = `${expresion} =`;
    estado.repetirOperador = op;
    estado.repetirOperando = derecho;
    estado.actual = resultado;
    estado.previo = null;
    estado.operador = null;
    estado.sobrescribir = true;
    estado.operandoListo = false;
  }

  function signo() {
    if (estado.actual === 'Error') return;

    // Si esperamos un operando nuevo, el signo abre el número que se va a teclear
    // en lugar de negar el operando izquierdo, que ya está guardado.
    if (estado.sobrescribir && estado.operador !== null) {
      estado.actual = '-0';
      estado.sobrescribir = false;
      estado.operandoListo = true;
      return;
    }

    if (estado.actual === '0') return;
    estado.actual = estado.actual.startsWith('-')
      ? estado.actual.slice(1)
      : '-' + estado.actual;
    estado.operandoListo = true;
  }

  function porcentaje() {
    if (estado.actual === 'Error') return;

    // Con + y −, el porcentaje es una fracción del operando izquierdo:
    // 200 + 10 % = 200 + 20. Con × y ÷ basta con dividir entre 100.
    const relativo =
      (estado.operador === '+' || estado.operador === '-') &&
      estado.previo !== null &&
      estado.operandoListo;

    const factor = relativo ? Number(estado.previo) : 1;
    estado.actual = aTexto((Number(estado.actual) / 100) * factor);
    estado.sobrescribir = true;
    estado.operandoListo = true;
  }

  function raiz() {
    if (estado.actual === 'Error') return;

    const valor = Number(estado.actual);
    if (valor < 0) { fijarError(); return; }

    const resultado = aTexto(Math.sqrt(valor));
    if (estado.operador === null) {
      registrar(`√${formatear(estado.actual)}`, resultado);
      estado.expresion = `√${formatear(estado.actual)} =`;
    }
    estado.actual = resultado;
    estado.sobrescribir = true;
    estado.operandoListo = true;
  }

  function borrar() {
    if (estado.sobrescribir || estado.actual === 'Error') {
      estado.actual = '0';
      estado.sobrescribir = false;
      estado.operandoListo = true;
      return;
    }
    estado.actual = estado.actual.slice(0, -1);
    if (estado.actual === '' || estado.actual === '-') estado.actual = '0';
    estado.operandoListo = true;
  }

  function memoriaSumar() {
    if (estado.actual === 'Error') return;
    estado.memoria += Number(estado.actual);
    estado.sobrescribir = true;
  }

  function memoriaLeer() {
    estado.actual = aTexto(estado.memoria);
    estado.sobrescribir = true;
    estado.operandoListo = true;
  }

  function memoriaLimpiar() {
    estado.memoria = 0;
  }

  return {
    estado,
    pantalla: () => formatear(estado.actual),
    expresion: () => estado.expresion,
    memoriaActiva: () => estado.memoria !== 0,
    historial: () => estado.historial.slice(),
    // Operador resaltado: sólo mientras se espera el operando derecho.
    operadorActivo: () => (estado.sobrescribir ? estado.operador : null),
    digito,
    decimal,
    operador,
    igual,
    limpiar,
    signo,
    porcentaje,
    raiz,
    borrar,
    memoriaSumar,
    memoriaLeer,
    memoriaLimpiar,
  };
}

// Export para Node (las pruebas). En el navegador `module` no existe y esto se
// ignora, dejando crearCalculadora como global.
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { crearCalculadora, formatear, aTexto, calcular, CIFRAS_SIGNIFICATIVAS };
}
