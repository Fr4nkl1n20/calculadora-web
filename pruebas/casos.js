// Casos de prueba compartidos entre el ejecutor de Node (calculadora.test.js)
// y el del navegador (index.html). Al estar en un solo sitio, no hay riesgo de
// que las dos versiones se desincronicen.

// Lenguaje de pulsaciones: 0-9 dígitos, "." coma decimal, "+-*/" operadores,
// "=" igual, "C" borrar todo, "<" borrar dígito, "~" cambiar signo,
// "%" porcentaje, "r" raíz, "M" sumar a memoria, "R" leer memoria,
// "L" limpiar memoria.
const PULSACIONES = {
  '+': (c) => c.operador('+'),
  '-': (c) => c.operador('-'),
  '*': (c) => c.operador('*'),
  '/': (c) => c.operador('/'),
  '.': (c) => c.decimal(),
  '=': (c) => c.igual(),
  C: (c) => c.limpiar(),
  '<': (c) => c.borrar(),
  '~': (c) => c.signo(),
  '%': (c) => c.porcentaje(),
  r: (c) => c.raiz(),
  M: (c) => c.memoriaSumar(),
  R: (c) => c.memoriaLeer(),
  L: (c) => c.memoriaLimpiar(),
};

function reproducir(calc, teclas) {
  for (const tecla of teclas) {
    if (/[0-9]/.test(tecla)) calc.digito(tecla);
    else if (PULSACIONES[tecla]) PULSACIONES[tecla](calc);
    else throw new Error(`Tecla desconocida en el caso: ${tecla}`);
  }
  return calc;
}

function leer(calc, campo) {
  switch (campo) {
    case 'expresion':
      return calc.expresion();
    case 'historial':
      return calc.historial().map((e) => `${e.expresion} = ${e.resultado}`).join(' | ');
    case 'memoria':
      return String(calc.memoriaActiva());
    default:
      return calc.pantalla();
  }
}

const CASOS = [
  // --- aritmética básica
  { nombre: '2+3=', teclas: '2+3=', esperado: '5' },
  { nombre: '9-12=', teclas: '9-12=', esperado: '-3' },
  { nombre: '7*8=', teclas: '7*8=', esperado: '56' },
  { nombre: '84/4=', teclas: '84/4=', esperado: '21' },

  // --- encadenado
  { nombre: '2+3+4=', teclas: '2+3+4=', esperado: '9' },
  { nombre: '2+3*4= resuelve de izquierda a derecha', teclas: '2+3*4=', esperado: '20' },
  { nombre: 'operador doble 5+*3=', teclas: '5+*3=', esperado: '15' },
  { nombre: 'seguir operando tras el igual', teclas: '2+3=*2=', esperado: '10' },

  // --- decimales y coma flotante
  { nombre: '0,1+0,2=', teclas: '.1+.2=', esperado: '0,3' },
  { nombre: 'segunda coma ignorada 1.2.3', teclas: '1.2.3', esperado: '1,23' },
  { nombre: '1/3=', teclas: '1/3=', esperado: '0,333333333333333' },
  { nombre: '2/3= redondea', teclas: '2/3=', esperado: '0,666666666666667' },
  { nombre: '0,1+0,7=', teclas: '.1+.7=', esperado: '0,8' },
  { nombre: '0,3-0,1=', teclas: '.3-.1=', esperado: '0,2' },
  { nombre: '1,1*1,1=', teclas: '1.1*1.1=', esperado: '1,21' },
  { nombre: '4,35*100=', teclas: '4.35*100=', esperado: '435' },
  { nombre: '2,675*100=', teclas: '2.675*100=', esperado: '267,5' },
  { nombre: '1,005*1000=', teclas: '1.005*1000=', esperado: '1.005' },

  // --- precisión: entrada y salida usan las mismas 15 cifras
  { nombre: '999999999999+1= (12 dígitos)', teclas: '999999999999+1=', esperado: '1.000.000.000.000' },
  { nombre: '123456789012345+0= (15 dígitos)', teclas: '123456789012345+0=', esperado: '123.456.789.012.345' },
  { nombre: '123456789012345*1= (15 dígitos)', teclas: '123456789012345*1=', esperado: '123.456.789.012.345' },
  { nombre: '999999999999999+1= (desborde)', teclas: '999999999999999+1=', esperado: '1.000.000.000.000.000' },
  { nombre: 'límite de 15 dígitos al teclear', teclas: '1234567890123456', esperado: '123.456.789.012.345' },

  // --- formato
  { nombre: 'separador de miles', teclas: '1234567', esperado: '1.234.567' },
  { nombre: 'negativo con separador', teclas: '1234567~', esperado: '-1.234.567' },

  // --- porcentaje contextual
  { nombre: '50% suelto divide entre 100', teclas: '50%', esperado: '0,5' },
  { nombre: '200+10%= suma el 10% de 200', teclas: '200+10%=', esperado: '220' },
  { nombre: '200-10%= resta el 10% de 200', teclas: '200-10%=', esperado: '180' },
  { nombre: '200*10%= multiplica por 0,1', teclas: '200*10%=', esperado: '20' },
  { nombre: '200/10%= divide entre 0,1', teclas: '200/10%=', esperado: '2.000' },

  // --- repetir la última operación al volver a pulsar =
  { nombre: '2+3== repite la suma', teclas: '2+3==', esperado: '8' },
  { nombre: '2+3=== repite dos veces', teclas: '2+3===', esperado: '11' },
  { nombre: '5*2== repite el producto', teclas: '5*2==', esperado: '20' },
  { nombre: '10-1=== repite la resta', teclas: '10-1===', esperado: '7' },
  { nombre: '= sin operación previa no hace nada', teclas: '7=', esperado: '7' },

  // --- cambio de signo
  { nombre: 'signo sobre lo tecleado', teclas: '5~', esperado: '-5' },
  { nombre: 'signo tras operador abre un negativo', teclas: '5+~3=', esperado: '2' },
  { nombre: 'signo sobre el operando derecho', teclas: '5+3~=', esperado: '2' },
  { nombre: 'signo dos veces vuelve al positivo', teclas: '5~~', esperado: '5' },

  // --- raíz cuadrada
  { nombre: 'raíz de 9', teclas: '9r', esperado: '3' },
  { nombre: 'raíz de 16', teclas: '16r', esperado: '4' },
  { nombre: 'raíz de 2', teclas: '2r', esperado: '1,4142135623731' },
  { nombre: 'raíz dentro de una operación', teclas: '2+9r=', esperado: '5' },
  { nombre: 'raíz y luego encadenar', teclas: '2+9r*3=', esperado: '15' },
  { nombre: 'raíz de negativo da Error', teclas: '9~r', esperado: 'Error' },

  // --- memoria
  { nombre: 'M+ y MR', teclas: '5MCR', esperado: '5' },
  { nombre: 'M+ acumula', teclas: '5M3MCR', esperado: '8' },
  { nombre: 'MC vacía la memoria', teclas: '5MLCR', esperado: '0' },
  { nombre: 'MR como operando', teclas: '5MC10+R=', esperado: '15' },
  { nombre: 'sin memoria el indicador está apagado', teclas: '5', esperado: 'false', campo: 'memoria' },
  { nombre: 'con memoria el indicador se enciende', teclas: '5M', esperado: 'true', campo: 'memoria' },

  // --- borrado
  { nombre: 'borrar un dígito', teclas: '123<', esperado: '12' },
  { nombre: 'borrar hasta cero', teclas: '5<', esperado: '0' },
  { nombre: 'AC lo reinicia todo', teclas: '12+3C', esperado: '0' },

  // --- errores
  { nombre: 'división entre cero', teclas: '5/0=', esperado: 'Error' },
  { nombre: 'recuperación con AC', teclas: '5/0=C7', esperado: '7' },
  { nombre: 'recuperación tecleando un dígito', teclas: '5/0=7', esperado: '7' },

  // --- línea de expresión
  { nombre: 'expresión tras el igual', teclas: '2+3=', esperado: '2 + 3 =', campo: 'expresion' },
  { nombre: 'expresión al elegir operador', teclas: '2+', esperado: '2 +', campo: 'expresion' },
  { nombre: 'expresión de la raíz', teclas: '9r', esperado: '√9 =', campo: 'expresion' },

  // --- historial
  { nombre: 'el historial registra la operación', teclas: '2+3=', esperado: '2 + 3 = 5', campo: 'historial' },
  {
    nombre: 'el historial registra también los encadenados',
    teclas: '2+3+4=',
    esperado: '5 + 4 = 9 | 2 + 3 = 5',
    campo: 'historial',
  },
  { nombre: 'el historial empieza vacío', teclas: '12', esperado: '', campo: 'historial' },
];

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CASOS, reproducir, leer };
}
