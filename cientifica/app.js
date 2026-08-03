// Interfaz de la calculadora científica.
//
// Todo el cálculo ocurre en motor.py, ejecutándose sobre Pyodide. Este archivo
// sólo dibuja el teclado, recoge lo que pulsa el usuario y le pasa órdenes en
// JSON al motor. Mantener la frontera así hace que la lógica sea la misma que
// se prueba en CI con Python, sin navegador de por medio.

const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v314.0.3/full/';

const $ = (id) => document.getElementById(id);

const entrada = $('entrada');
const resultado = $('resultado');
const alterno = $('alterno');
const estado = $('ind-estado');

let ejecutarPython = null;   // función de Python, disponible tras cargar
let shift = false;
let alpha = false;

// ---------------------------------------------------------------------------
// Definición del teclado
// ---------------------------------------------------------------------------
//
// ins        texto que se inserta al pulsar
// sup        etiqueta secundaria (lo que hace con SHIFT)
// insShift   texto que se inserta con SHIFT activo
// accion     comportamiento especial en lugar de insertar texto

const TECLAS = [
  { et: 'SHIFT', clase: 'shift', accion: 'shift' },
  { et: 'ALPHA', clase: 'alpha', accion: 'alpha' },
  { et: '◀', clase: 'flecha', accion: 'izquierda' },
  { et: '▶', clase: 'flecha', accion: 'derecha' },
  { et: 'DEL', clase: 'borrar', accion: 'borrar' },
  { et: 'AC', clase: 'borrar', accion: 'limpiar', sup: 'RESET' },

  { et: 'x²', ins: '²', sup: 'x³', insShift: '³' },
  { et: 'xʸ', ins: '^' },
  { et: '√', ins: '√(', sup: '∛', insShift: '∛(' },
  { et: 'ˣ√y', ins: 'root(' },
  { et: 'x⁻¹', ins: '^-1', sup: 'x!', insShift: '!' },
  { et: '|x|', ins: 'abs(' },

  { et: 'log', ins: 'log(', sup: '10ˣ', insShift: '10^(' },
  { et: 'ln', ins: 'ln(', sup: 'eˣ', insShift: 'exp(' },
  { et: 'logab', ins: 'logab(' },
  { et: 'nCr', ins: 'nCr(' },
  { et: 'nPr', ins: 'nPr(' },
  { et: 'mod', ins: 'mod(' },

  { et: 'sin', ins: 'sin(', sup: 'sin⁻¹', insShift: 'asin(' },
  { et: 'cos', ins: 'cos(', sup: 'cos⁻¹', insShift: 'acos(' },
  { et: 'tan', ins: 'tan(', sup: 'tan⁻¹', insShift: 'atan(' },
  { et: 'sinh', ins: 'sinh(', sup: 'sinh⁻¹', insShift: 'asinh(' },
  { et: 'cosh', ins: 'cosh(', sup: 'cosh⁻¹', insShift: 'acosh(' },
  { et: 'tanh', ins: 'tanh(', sup: 'tanh⁻¹', insShift: 'atanh(' },

  { et: '(', ins: '(' },
  { et: ')', ins: ')' },
  { et: ',', ins: ',' },
  { et: 'π', ins: 'π', sup: 'e', insShift: 'e' },
  { et: 'i', ins: 'i' },
  { et: 'Ans', ins: 'Ans' },

  { et: '7', clase: 'numero', ins: '7' },
  { et: '8', clase: 'numero', ins: '8' },
  { et: '9', clase: 'numero', ins: '9' },
  { et: '÷', clase: 'operador', ins: '÷' },
  { et: 'X', ins: 'X', sup: 'Y', insShift: 'Y' },
  { et: '°', ins: '°' },

  { et: '4', clase: 'numero', ins: '4' },
  { et: '5', clase: 'numero', ins: '5' },
  { et: '6', clase: 'numero', ins: '6' },
  { et: '×', clase: 'operador', ins: '×' },
  { et: 'gcd', ins: 'gcd(' },
  { et: 'lcm', ins: 'lcm(' },

  { et: '1', clase: 'numero', ins: '1' },
  { et: '2', clase: 'numero', ins: '2' },
  { et: '3', clase: 'numero', ins: '3' },
  { et: '−', clase: 'operador', ins: '-' },
  { et: 'STO', accion: 'guardar', sup: 'RCL' },
  { et: 'A→F', accion: 'variables' },

  { et: '0', clase: 'numero', ins: '0' },
  { et: '.', clase: 'numero', ins: '.' },
  { et: 'EXP', ins: 'e' },
  { et: '+', clase: 'operador', ins: '+' },
  { et: '%', ins: '%' },
  { et: '=', clase: 'igual', accion: 'evaluar' },
];

function dibujarTeclado() {
  const teclado = $('teclado');
  for (const tecla of TECLAS) {
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'tecla ' + (tecla.clase || '');
    if (tecla.sup) {
      boton.classList.add('tiene-shift');
      const sup = document.createElement('span');
      sup.className = 'sup';
      sup.textContent = tecla.sup;
      boton.append(sup);
    }
    boton.append(document.createTextNode(tecla.et));
    boton.addEventListener('click', () => pulsar(tecla, boton));
    teclado.append(boton);
  }
}

// ---------------------------------------------------------------------------
// Edición de la expresión
// ---------------------------------------------------------------------------

function insertar(texto) {
  const inicio = entrada.selectionStart ?? entrada.value.length;
  const fin = entrada.selectionEnd ?? entrada.value.length;
  entrada.value = entrada.value.slice(0, inicio) + texto + entrada.value.slice(fin);
  const cursor = inicio + texto.length;
  entrada.setSelectionRange(cursor, cursor);
  entrada.focus();
}

function borrarCaracter() {
  const inicio = entrada.selectionStart ?? entrada.value.length;
  const fin = entrada.selectionEnd ?? entrada.value.length;
  if (inicio !== fin) {
    entrada.value = entrada.value.slice(0, inicio) + entrada.value.slice(fin);
    entrada.setSelectionRange(inicio, inicio);
  } else if (inicio > 0) {
    entrada.value = entrada.value.slice(0, inicio - 1) + entrada.value.slice(inicio);
    entrada.setSelectionRange(inicio - 1, inicio - 1);
  }
  entrada.focus();
}

function moverCursor(delta) {
  const p = Math.max(0, Math.min(entrada.value.length,
    (entrada.selectionStart ?? 0) + delta));
  entrada.setSelectionRange(p, p);
  entrada.focus();
}

function pulsar(tecla, boton) {
  boton.classList.add('pulsada');
  setTimeout(() => boton.classList.remove('pulsada'), 90);

  if (tecla.accion === 'shift') { alternarShift(); return; }
  if (tecla.accion === 'alpha') { alternarAlpha(); return; }

  const conShift = shift;
  if (conShift) alternarShift(false);

  switch (tecla.accion) {
    // AC limpia la pantalla; SHIFT+AC (RESET) borra además variables e historial.
    // Separarlo importa: perder las variables al despejar la pantalla sería
    // exactamente lo que no hace una fx.
    case 'limpiar':   conShift ? reiniciarTodo() : limpiarPantalla(); return;
    case 'borrar':    borrarCaracter(); return;
    case 'izquierda': moverCursor(-1); return;
    case 'derecha':   moverCursor(1); return;
    case 'evaluar':   evaluarExpresion(); return;
    case 'guardar':   conShift ? recuperarVariable() : guardarVariable(); return;
    case 'variables': mostrarVariables(); return;
  }

  if (conShift && tecla.insShift !== undefined) insertar(tecla.insShift);
  else if (tecla.ins !== undefined) insertar(tecla.ins);
}

function alternarShift(valor) {
  shift = valor === undefined ? !shift : valor;
  $('ind-shift').hidden = !shift;
  $('teclado').classList.toggle('en-shift', shift);
  document.querySelectorAll('.tecla.shift')
    .forEach((b) => b.classList.toggle('encendida', shift));
}

function alternarAlpha(valor) {
  alpha = valor === undefined ? !alpha : valor;
  $('ind-alpha').hidden = !alpha;
  document.querySelectorAll('.tecla.alpha')
    .forEach((b) => b.classList.toggle('encendida', alpha));
}

// ---------------------------------------------------------------------------
// Puente con Python
// ---------------------------------------------------------------------------

async function llamar(peticion) {
  if (!ejecutarPython) {
    return { ok: false, error: 'El motor de Python todavía se está cargando' };
  }
  try {
    return JSON.parse(ejecutarPython(JSON.stringify(peticion)));
  } catch (error) {
    return { ok: false, error: 'Fallo inesperado del motor: ' + error.message };
  }
}

async function arrancar() {
  try {
    const py = await loadPyodide({ indexURL: PYODIDE_URL });
    estado.textContent = 'Cargando el motor…';

    const respuesta = await fetch('motor.py');
    if (!respuesta.ok) throw new Error('no se pudo descargar motor.py');
    py.runPython(await respuesta.text());
    ejecutarPython = py.globals.get('ejecutar');

    $('cargando').classList.add('oculto');
    // py.version es la versión de Pyodide; la de Python se pregunta a Python.
    const version = py.runPython('import sys; ".".join(map(str, sys.version_info[:3]))');
    estado.textContent = `Listo · Python ${version}`;
    estado.classList.add('listo');
    entrada.focus();
    cargarConstantes();
  } catch (error) {
    $('cargando-texto').textContent =
      'No se pudo cargar Python: ' + error.message +
      '. Comprueba tu conexión y recarga la página.';
    estado.textContent = 'Sin motor';
    estado.classList.add('error');
  }
}

// ---------------------------------------------------------------------------
// Acciones principales
// ---------------------------------------------------------------------------

function mostrarError(mensaje) {
  resultado.textContent = mensaje;
  resultado.classList.add('error');
  alterno.textContent = '';
}

function mostrarValor(r) {
  resultado.classList.remove('error');
  resultado.textContent = r.principal;
  alterno.textContent = r.mixta ? `${r.alterno}  ·  ${r.mixta}` : (r.alterno || '');
}

async function evaluarExpresion() {
  const expr = entrada.value.trim();
  if (!expr) return;
  const r = await llamar({ cmd: 'evaluar', expr });
  if (!r.ok) { mostrarError(r.error); return; }
  mostrarValor(r);
  pintarHistorial(r.historial);
}

function limpiarPantalla() {
  entrada.value = '';
  resultado.textContent = '0';
  resultado.classList.remove('error');
  alterno.textContent = '';
  entrada.focus();
}

async function reiniciarTodo() {
  limpiarPantalla();
  await llamar({ cmd: 'limpiar' });
  pintarHistorial([]);
  alterno.textContent = 'Variables e historial borrados';
}

async function guardarVariable() {
  const nombre = prompt('Guardar el resultado en la variable (A–F, X, Y, M):');
  if (!nombre) return;
  const r = await llamar({ cmd: 'guardar_variable', nombre: nombre.trim(),
                           expr: entrada.value.trim() });
  if (!r.ok) mostrarError(r.error);
  else alterno.textContent = `${r.nombre} = ${r.principal}`;
}

function recuperarVariable() {
  const nombre = prompt('Insertar el valor de la variable:');
  if (nombre) insertar(nombre.trim());
}

async function mostrarVariables() {
  const r = await llamar({ cmd: 'variables' });
  if (!r.ok) { mostrarError(r.error); return; }
  const lineas = Object.entries(r.variables);
  alterno.textContent = lineas.length
    ? lineas.map(([k, v]) => `${k}=${v}`).join('   ')
    : 'No hay variables guardadas';
}

function pintarHistorial(historial) {
  const lista = $('registro');
  lista.replaceChildren();
  $('registro-vacio').hidden = historial && historial.length > 0;
  for (const item of historial || []) {
    const li = document.createElement('li');
    const izq = document.createElement('span');
    izq.textContent = item.expr;
    const der = document.createElement('span');
    der.textContent = item.principal;
    li.append(izq, der);
    li.title = 'Pulsa para reutilizar esta expresión';
    li.addEventListener('click', () => { entrada.value = item.expr; entrada.focus(); });
    lista.append(li);
  }
}

// ---------------------------------------------------------------------------
// Indicadores de modo
// ---------------------------------------------------------------------------

const ANGULOS = ['DEG', 'RAD', 'GRA'];
const FORMATOS = ['NORM', 'FIX', 'SCI', 'ENG'];

$('ind-angulo').addEventListener('click', async () => {
  const actual = $('ind-angulo').textContent;
  const siguiente = ANGULOS[(ANGULOS.indexOf(actual) + 1) % ANGULOS.length];
  const r = await llamar({ cmd: 'configurar', angulo: siguiente });
  if (r.ok) $('ind-angulo').textContent = r.angulo;
});

$('ind-formato').addEventListener('click', async () => {
  const actual = $('ind-formato').textContent;
  const siguiente = FORMATOS[(FORMATOS.indexOf(actual) + 1) % FORMATOS.length];
  const r = await llamar({ cmd: 'configurar', formato: siguiente });
  if (r.ok) $('ind-formato').textContent = r.formato;
});

// ---------------------------------------------------------------------------
// Navegación entre modos
// ---------------------------------------------------------------------------

$('modos').addEventListener('click', (evento) => {
  const boton = evento.target.closest('.modo');
  if (!boton) return;
  document.querySelectorAll('.modo').forEach((b) => b.classList.remove('activo'));
  document.querySelectorAll('.panel').forEach((p) => p.classList.remove('activo'));
  boton.classList.add('activo');
  $('panel-' + boton.dataset.panel).classList.add('activo');
});

// ---------------------------------------------------------------------------
// Utilidades de presentación
// ---------------------------------------------------------------------------

function tablaDe(pares) {
  const tabla = document.createElement('table');
  for (const [clave, valor] of pares) {
    const tr = document.createElement('tr');
    const th = document.createElement('th');
    th.textContent = clave;
    const td = document.createElement('td');
    td.textContent = valor === null || valor === undefined ? '—' : valor;
    tr.append(th, td);
    tabla.append(tr);
  }
  return tabla;
}

function pintar(destino, contenido) {
  const caja = $(destino);
  caja.replaceChildren();
  if (typeof contenido === 'string') {
    const aviso = document.createElement('div');
    aviso.className = 'aviso';
    aviso.textContent = contenido;
    caja.append(aviso);
  } else {
    caja.append(contenido);
  }
}

function numeros(texto) {
  return texto.split(/[\s,;]+/).filter(Boolean).map((v) => {
    const n = Number(v.replace(',', '.'));
    if (Number.isNaN(n)) throw new Error(`«${v}» no es un número`);
    return n;
  });
}

// ---------------------------------------------------------------------------
// Panel: estadística
// ---------------------------------------------------------------------------

$('stat-tipo').addEventListener('change', () => {
  $('stat-modelo-campo').hidden = $('stat-tipo').value !== '2var';
});

$('stat-calcular').addEventListener('click', async () => {
  const tipo = $('stat-tipo').value;
  const texto = $('stat-datos').value.trim();
  if (!texto) { pintar('stat-salida', 'Introduce algunos datos'); return; }

  let peticion;
  try {
    if (tipo === '1var') {
      peticion = { cmd: 'estadistica', tipo: '1var', datos: numeros(texto) };
    } else {
      const datos = texto.split('\n').map((l) => l.trim()).filter(Boolean)
        .map((linea) => {
          const p = numeros(linea);
          if (p.length < 2) throw new Error(`la línea «${linea}» no tiene dos valores`);
          return [p[0], p[1]];
        });
      peticion = { cmd: 'estadistica', tipo: '2var', datos,
                   modelo: $('stat-modelo').value };
    }
  } catch (error) {
    pintar('stat-salida', 'Datos no válidos: ' + error.message);
    return;
  }

  const r = await llamar(peticion);
  if (!r.ok) { pintar('stat-salida', r.error); return; }
  pintar('stat-salida', tablaDe(Object.entries(r.resultados).map(
    ([k, v]) => [k, typeof v === 'number' ? formatearJS(v) : v])));
});

function formatearJS(v) {
  if (v === null) return '—';
  if (Number.isInteger(v) && Math.abs(v) < 1e15) return String(v);
  return Number(v.toPrecision(12)).toString();
}

// ---------------------------------------------------------------------------
// Panel: ecuaciones
// ---------------------------------------------------------------------------

$('eq-tipo').addEventListener('change', () => {
  const t = $('eq-tipo').value;
  $('eq-polinomio').hidden = t !== 'polinomio';
  $('eq-sistema').hidden = t !== 'sistema';
  $('eq-expresion').hidden = t !== 'expresion';
});

$('eq-calcular').addEventListener('click', async () => {
  const tipo = $('eq-tipo').value;
  let r;
  try {
    if (tipo === 'polinomio') {
      r = await llamar({ cmd: 'polinomio', coeficientes: numeros($('eq-coef').value) });
      if (!r.ok) { pintar('eq-salida', r.error); return; }
      pintar('eq-salida', tablaDe(r.raices.map((v, i) => [`x${i + 1}`, v])));
    } else if (tipo === 'sistema') {
      const matriz = $('eq-matriz').value.split('\n').map((l) => l.trim())
        .filter(Boolean).map(numeros);
      r = await llamar({ cmd: 'sistema', matriz });
      if (!r.ok) { pintar('eq-salida', r.error); return; }
      pintar('eq-salida', tablaDe(r.soluciones.map((s) => [s.nombre, s.valor])));
    } else {
      r = await llamar({ cmd: 'resolver', expr: $('eq-expr').value,
                         inicial: Number($('eq-inicial').value) || 1 });
      if (!r.ok) { pintar('eq-salida', r.error); return; }
      pintar('eq-salida', tablaDe([['X', r.principal]]));
    }
  } catch (error) {
    pintar('eq-salida', 'Entrada no válida: ' + error.message);
  }
});

// ---------------------------------------------------------------------------
// Panel: cálculo
// ---------------------------------------------------------------------------

$('cal-tipo').addEventListener('change', () => {
  const derivada = $('cal-tipo').value === 'derivada';
  $('cal-punto-campo').hidden = !derivada;
  $('cal-a-campo').hidden = derivada;
  $('cal-b-campo').hidden = derivada;
});

$('cal-calcular').addEventListener('click', async () => {
  const expr = $('cal-expr').value.trim();
  if (!expr) { pintar('cal-salida', 'Escribe una función de X'); return; }

  const r = $('cal-tipo').value === 'derivada'
    ? await llamar({ cmd: 'derivada', expr, punto: Number($('cal-punto').value) || 0 })
    : await llamar({ cmd: 'integral', expr, a: Number($('cal-a').value) || 0,
                     b: Number($('cal-b').value) || 0 });

  if (!r.ok) { pintar('cal-salida', r.error); return; }
  pintar('cal-salida', tablaDe([
    [$('cal-tipo').value === 'derivada' ? 'f′(x)' : '∫ f(x) dx', r.principal]]));
});

// ---------------------------------------------------------------------------
// Panel: tabla
// ---------------------------------------------------------------------------

$('tab-calcular').addEventListener('click', async () => {
  const r = await llamar({
    cmd: 'tabla', expr: $('tab-expr').value.trim(),
    desde: Number($('tab-desde').value) || 0,
    hasta: Number($('tab-hasta').value) || 0,
    paso: Number($('tab-paso').value) || 1,
  });
  if (!r.ok) { pintar('tab-salida', r.error); return; }

  const caja = document.createElement('div');
  caja.className = 'desplazable';
  caja.append(tablaDe(r.filas.map((f) => [`x = ${formatearJS(f.x)}`, f.y])));
  pintar('tab-salida', caja);
});

// ---------------------------------------------------------------------------
// Panel: base-N y factorización
// ---------------------------------------------------------------------------

$('bin-convertir').addEventListener('click', async () => {
  const valor = $('bin-valor').value.trim();
  const desde = Number($('bin-desde').value);
  const filas = [];
  for (const [nombre, base] of [['Decimal', 10], ['Binario', 2], ['Octal', 8], ['Hexadecimal', 16]]) {
    const r = await llamar({ cmd: 'base', valor, desde, hacia: base });
    if (!r.ok) { pintar('bin-salida', r.error); return; }
    filas.push([nombre, r.valor]);
  }
  pintar('bin-salida', tablaDe(filas));
});

$('bin-logica').addEventListener('click', async () => {
  const r = await llamar({ cmd: 'logica', op: $('bin-op').value,
                           a: Number($('bin-a').value) || 0,
                           b: Number($('bin-b').value) || 0 });
  if (!r.ok) { pintar('bin-salida', r.error); return; }
  pintar('bin-salida', tablaDe([
    ['Decimal', r.resultado.dec], ['Binario', r.resultado.bin],
    ['Octal', r.resultado.oct], ['Hexadecimal', r.resultado.hex]]));
});

$('fac-calcular').addEventListener('click', async () => {
  const r = await llamar({ cmd: 'factorizar', n: Number($('fac-n').value) || 0 });
  if (!r.ok) { pintar('fac-salida', r.error); return; }
  pintar('fac-salida', tablaDe([
    ['Número', r.resultado.numero],
    ['Factorización', r.resultado.expresion],
    ['¿Es primo?', r.resultado.es_primo ? 'Sí' : 'No'],
    ['Número de divisores', r.resultado.numero_de_divisores]]));
});

// ---------------------------------------------------------------------------
// Panel: unidades
// ---------------------------------------------------------------------------

const FAMILIAS_UNIDADES = {
  'Longitud': ['m', 'km', 'cm', 'mm', 'mi', 'yd', 'ft', 'in', 'nmi', 'ly'],
  'Masa': ['kg', 'g', 'mg', 't', 'lb', 'oz'],
  'Volumen': ['L', 'mL', 'm3', 'gal', 'qt', 'floz'],
  'Energía': ['J', 'kJ', 'cal', 'kcal', 'Wh', 'kWh', 'eV', 'BTU'],
  'Presión': ['Pa', 'kPa', 'bar', 'atm', 'mmHg', 'psi'],
  'Velocidad': ['m/s', 'km/h', 'mph', 'kn', 'ft/s'],
  'Temperatura': ['C', 'F', 'K'],
};

function rellenarUnidades() {
  for (const id of ['uni-desde', 'uni-hacia']) {
    const select = $(id);
    for (const [familia, unidades] of Object.entries(FAMILIAS_UNIDADES)) {
      const grupo = document.createElement('optgroup');
      grupo.label = familia;
      for (const u of unidades) {
        const op = document.createElement('option');
        op.value = u;
        op.textContent = u;
        grupo.append(op);
      }
      select.append(grupo);
    }
  }
  $('uni-desde').value = 'km';
  $('uni-hacia').value = 'mi';
}

$('uni-convertir').addEventListener('click', async () => {
  const r = await llamar({ cmd: 'unidad', valor: Number($('uni-valor').value) || 0,
                           desde: $('uni-desde').value, hacia: $('uni-hacia').value });
  if (!r.ok) { pintar('uni-salida', r.error); return; }
  pintar('uni-salida', tablaDe([
    [`${$('uni-valor').value} ${$('uni-desde').value}`,
     `${r.principal} ${$('uni-hacia').value}`]]));
});

// ---------------------------------------------------------------------------
// Panel: constantes
// ---------------------------------------------------------------------------

async function cargarConstantes() {
  const r = await llamar({ cmd: 'constantes' });
  if (!r.ok) return;
  const caja = $('const-salida');
  caja.replaceChildren();
  for (const c of r.constantes) {
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'constante';
    const linea = document.createElement('span');
    linea.innerHTML = '';
    const b = document.createElement('b');
    b.textContent = c.simbolo;
    const valor = document.createElement('span');
    valor.textContent = `  =  ${c.valor} ${c.unidad}`;
    const desc = document.createElement('small');
    desc.textContent = c.descripcion;
    boton.append(b, valor, desc);
    boton.addEventListener('click', () => {
      insertar(c.simbolo);
      document.querySelector('.modo[data-panel="calcular"]').click();
    });
    caja.append(boton);
  }
}

// ---------------------------------------------------------------------------
// Teclado físico
// ---------------------------------------------------------------------------

document.addEventListener('keydown', (evento) => {
  if (evento.ctrlKey || evento.altKey || evento.metaKey) return;
  if (evento.key === 'Enter' && document.activeElement === entrada) {
    evento.preventDefault();
    evaluarExpresion();
  } else if (evento.key === 'Escape') {
    evento.preventDefault();
    limpiarPantalla();
  }
});

entrada.addEventListener('keydown', (evento) => {
  if (evento.key === 'Enter') { evento.preventDefault(); evaluarExpresion(); }
});

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------

dibujarTeclado();
rellenarUnidades();
pintarHistorial([]);
arrancar();
