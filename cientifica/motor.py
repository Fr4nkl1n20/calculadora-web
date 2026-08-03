"""Motor de la calculadora científica.

Python puro, sin dependencias externas: se ejecuta igual en CPython (donde lo
prueba el CI) y dentro del navegador sobre Pyodide.

La interfaz con JavaScript es una única función, `ejecutar`, que recibe y
devuelve JSON. Mantenerla así evita tener que convertir objetos de Python a
JavaScript y hace que todo el motor sea probable desde Python sin navegador.

Arquitectura:
  1. `tokenizar`  -> lista de tokens
  2. `Analizador` -> árbol sintáctico (AST)
  3. `evaluar`    -> valor, con un contexto (modo angular, variables)

Se construye un AST en lugar de evaluar sobre la marcha porque las tablas de
valores, la derivada y la integral necesitan evaluar la misma expresión muchas
veces cambiando X.
"""

from __future__ import annotations

import cmath
import json
import math
import random
import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

CONSTANTES = {
    'π': math.pi,
    'pi': math.pi,
    'e': math.e,
    'φ': (1 + math.sqrt(5)) / 2,
    'phi': (1 + math.sqrt(5)) / 2,
}

# Constantes físicas del sistema internacional, como en los modelos fx.
CONSTANTES_FISICAS = {
    'c0': (299792458.0, 'm/s', 'Velocidad de la luz en el vacío'),
    'g': (9.80665, 'm/s²', 'Aceleración de la gravedad'),
    'G': (6.67430e-11, 'm³/(kg·s²)', 'Constante gravitacional'),
    'h': (6.62607015e-34, 'J·s', 'Constante de Planck'),
    'hbar': (1.054571817e-34, 'J·s', 'Constante de Planck reducida'),
    'NA': (6.02214076e23, '1/mol', 'Número de Avogadro'),
    'k': (1.380649e-23, 'J/K', 'Constante de Boltzmann'),
    'R': (8.314462618, 'J/(mol·K)', 'Constante de los gases'),
    'qe': (1.602176634e-19, 'C', 'Carga elemental'),
    'me': (9.1093837015e-31, 'kg', 'Masa del electrón'),
    'mp': (1.67262192369e-27, 'kg', 'Masa del protón'),
    'mn': (1.67492749804e-27, 'kg', 'Masa del neutrón'),
    'u': (1.66053906660e-27, 'kg', 'Unidad de masa atómica'),
    'eps0': (8.8541878128e-12, 'F/m', 'Permitividad del vacío'),
    'mu0': (1.25663706212e-6, 'N/A²', 'Permeabilidad del vacío'),
    'F': (96485.33212, 'C/mol', 'Constante de Faraday'),
    'sigma': (5.670374419e-8, 'W/(m²·K⁴)', 'Constante de Stefan-Boltzmann'),
    'atm': (101325.0, 'Pa', 'Atmósfera estándar'),
}

# Conversiones de unidades: factor hacia la unidad base de cada familia.
UNIDADES = {
    'longitud': {
        'base': 'm',
        'unidades': {'m': 1.0, 'km': 1000.0, 'cm': 0.01, 'mm': 0.001,
                     'mi': 1609.344, 'yd': 0.9144, 'ft': 0.3048, 'in': 0.0254,
                     'nmi': 1852.0, 'ly': 9.4607304725808e15},
    },
    'masa': {
        'base': 'kg',
        'unidades': {'kg': 1.0, 'g': 0.001, 'mg': 1e-6, 't': 1000.0,
                     'lb': 0.45359237, 'oz': 0.028349523125},
    },
    'volumen': {
        'base': 'L',
        'unidades': {'L': 1.0, 'mL': 0.001, 'm3': 1000.0, 'gal': 3.785411784,
                     'qt': 0.946352946, 'floz': 0.0295735295625},
    },
    'energia': {
        'base': 'J',
        'unidades': {'J': 1.0, 'kJ': 1000.0, 'cal': 4.184, 'kcal': 4184.0,
                     'Wh': 3600.0, 'kWh': 3600000.0, 'eV': 1.602176634e-19,
                     'BTU': 1055.05585262},
    },
    'presion': {
        'base': 'Pa',
        'unidades': {'Pa': 1.0, 'kPa': 1000.0, 'bar': 100000.0, 'atm': 101325.0,
                     'mmHg': 133.322387415, 'psi': 6894.757293168},
    },
    'velocidad': {
        'base': 'm/s',
        'unidades': {'m/s': 1.0, 'km/h': 1 / 3.6, 'mph': 0.44704, 'kn': 0.514444,
                     'ft/s': 0.3048},
    },
}

# Las de temperatura no son un factor: llevan desplazamiento.
TEMPERATURAS = ('C', 'F', 'K')


class ErrorCalculo(Exception):
    """Error previsto del usuario: sintaxis, dominio, división entre cero…"""


# ---------------------------------------------------------------------------
# Tokenizador
# ---------------------------------------------------------------------------

_NUMERO = re.compile(r'(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?')
_IDENT = re.compile(r'[A-Za-zΑ-Ωα-ω_][A-Za-zΑ-Ωα-ω_0-9]*')

# Símbolos que se escriben de varias formas segun el teclado.
_ALIAS = {'×': '*', '·': '*', '÷': '/', '−': '-', '–': '-', '—': '-',
          '⁄': '/', '（': '(', '）': ')', '，': ','}

_POSFIJOS = {'!', '²', '³', '%', '°', '⁻'}
_PREFIJOS_RAIZ = {'√': 'sqrt', '∛': 'cbrt'}


def tokenizar(texto: str) -> list[tuple[str, object]]:
    tokens: list[tuple[str, object]] = []
    i = 0
    n = len(texto)

    while i < n:
        c = texto[i]

        if c in ' \t\n':
            i += 1
            continue

        c = _ALIAS.get(c, c)

        if texto[i].isdigit() or c == '.':
            m = _NUMERO.match(texto, i)
            if m:
                # Decimal acepta «1.», «.5» y «1e3»; Fraction por sí sola no.
                try:
                    tokens.append(('num', Fraction(Decimal(m.group()))))
                except InvalidOperation:
                    raise ErrorCalculo(f'Número no válido: «{m.group()}»')
                i = m.end()
                continue

        if c in _PREFIJOS_RAIZ:
            tokens.append(('raiz', _PREFIJOS_RAIZ[c]))
            i += 1
            continue

        # Potencias escritas en superíndice: 5² 5³
        if c == '²':
            tokens.append(('pos', '²'))
            i += 1
            continue
        if c == '³':
            tokens.append(('pos', '³'))
            i += 1
            continue
        if c in ('!', '%', '°'):
            tokens.append(('pos', c))
            i += 1
            continue

        m = _IDENT.match(texto, i)
        if m:
            tokens.append(('ident', m.group()))
            i = m.end()
            continue

        if c in '+-*/^(),':
            tokens.append(('op', c), )
            i += 1
            continue

        raise ErrorCalculo(f'Carácter no reconocido: «{texto[i]}»')

    return tokens


# ---------------------------------------------------------------------------
# Analizador sintáctico
# ---------------------------------------------------------------------------
#
# Gramática (de menor a mayor prioridad):
#   expresion := termino (('+' | '-') termino)*
#   termino   := unario (('*' | '/') unario | implícito)*
#   unario    := ('-' | '+') unario | potencia
#   potencia  := posfijo ('^' unario)?          -- asociativa por la derecha
#   posfijo   := primario ('!' | '²' | '³' | '%' | '°')*
#   primario  := numero | constante | variable | funcion '(' args ')'
#              | '(' expresion ')' | raiz unario
#
# `unario` está por encima de `potencia` para que −2^2 dé −4, como en los fx.

class Analizador:
    def __init__(self, tokens: list[tuple[str, object]]):
        self.tokens = tokens
        self.i = 0

    def _mirar(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def _avanzar(self):
        t = self._mirar()
        self.i += 1
        return t

    def _es_op(self, *simbolos):
        tipo, valor = self._mirar()
        return tipo == 'op' and valor in simbolos

    def analizar(self):
        nodo = self.expresion()
        if self.i < len(self.tokens):
            tipo, valor = self._mirar()
            raise ErrorCalculo(f'Sobra «{valor}» al final de la expresión')
        return nodo

    def expresion(self):
        nodo = self.termino()
        while self._es_op('+', '-'):
            _, op = self._avanzar()
            nodo = ('op', op, nodo, self.termino())
        return nodo

    def termino(self):
        nodo = self.unario()
        while True:
            if self._es_op('*', '/'):
                _, op = self._avanzar()
                nodo = ('op', op, nodo, self.unario())
            elif self._empieza_primario():
                # Multiplicación implícita: 2π, 3(4+5), 2sin(30)
                nodo = ('op', '*', nodo, self.unario())
            else:
                return nodo

    def _empieza_primario(self):
        tipo, valor = self._mirar()
        if tipo in ('num', 'ident', 'raiz'):
            return True
        return tipo == 'op' and valor == '('

    def unario(self):
        if self._es_op('-'):
            self._avanzar()
            return ('neg', self.unario())
        if self._es_op('+'):
            self._avanzar()
            return self.unario()
        return self.potencia()

    def potencia(self):
        base = self.posfijo()
        if self._es_op('^'):
            self._avanzar()
            return ('op', '^', base, self.unario())
        return base

    def posfijo(self):
        nodo = self.primario()
        while True:
            tipo, valor = self._mirar()
            if tipo != 'pos':
                return nodo
            self._avanzar()
            if valor == '²':
                nodo = ('op', '^', nodo, ('num', Fraction(2)))
            elif valor == '³':
                nodo = ('op', '^', nodo, ('num', Fraction(3)))
            elif valor == '!':
                nodo = ('llamada', 'fact', [nodo])
            elif valor == '%':
                nodo = ('pct', nodo)
            elif valor == '°':
                nodo = ('grados', nodo)

    def primario(self):
        tipo, valor = self._avanzar()

        if tipo == 'num':
            return ('num', valor)

        if tipo == 'raiz':
            return ('llamada', valor, [self.unario()])

        if tipo == 'ident':
            if self._es_op('('):
                self._avanzar()
                args = []
                if not self._es_op(')'):
                    args.append(self.expresion())
                    while self._es_op(','):
                        self._avanzar()
                        args.append(self.expresion())
                if not self._es_op(')'):
                    raise ErrorCalculo('Falta cerrar un paréntesis')
                self._avanzar()
                return ('llamada', valor, args)
            return ('var', valor)

        if tipo == 'op' and valor == '(':
            nodo = self.expresion()
            if not self._es_op(')'):
                raise ErrorCalculo('Falta cerrar un paréntesis')
            self._avanzar()
            return nodo

        if tipo is None:
            raise ErrorCalculo('La expresión está incompleta')

        raise ErrorCalculo(f'No se esperaba «{valor}» aquí')


def analizar(texto: str):
    if not texto.strip():
        raise ErrorCalculo('No hay nada que calcular')
    return Analizador(tokenizar(texto)).analizar()


# ---------------------------------------------------------------------------
# Utilidades numéricas
# ---------------------------------------------------------------------------

def _es_exacto(v) -> bool:
    return isinstance(v, (int, Fraction))


def _a_real(v) -> float:
    if isinstance(v, complex):
        if abs(v.imag) > 1e-12:
            raise ErrorCalculo('Se esperaba un número real, no complejo')
        return float(v.real)
    return float(v)


def _a_entero(v) -> int:
    r = _a_real(v)
    if abs(r - round(r)) > 1e-9:
        raise ErrorCalculo('Se esperaba un número entero')
    return int(round(r))


def _limpiar(v):
    """Convierte un complejo sin parte imaginaria en real."""
    if isinstance(v, complex) and abs(v.imag) < 1e-15 * max(1.0, abs(v.real)):
        return v.real
    return v


def _potencia(a, b):
    if _es_exacto(a) and _es_exacto(b):
        be = Fraction(b)
        if be.denominator == 1:
            expo = int(be)
            if a == 0 and expo < 0:
                raise ErrorCalculo('No se puede dividir entre cero')
            if abs(expo) > 5000:
                return _limpiar(complex(a) ** complex(b))
            return Fraction(a) ** expo
    ar, br = complex(a), complex(b)
    if ar.imag == 0 and br.imag == 0:
        base, expo = ar.real, br.real
        if base < 0 and expo != int(expo):
            return _limpiar(ar ** br)
        if base == 0 and expo < 0:
            raise ErrorCalculo('No se puede dividir entre cero')
        try:
            return math.pow(base, expo)
        except (OverflowError, ValueError):
            return _limpiar(ar ** br)
    return _limpiar(ar ** br)


# ---------------------------------------------------------------------------
# Funciones disponibles en las expresiones
# ---------------------------------------------------------------------------

def _trig(fn_real, fn_complejo, convertir_entrada):
    def aplicar(ctx, x):
        if isinstance(x, complex):
            return _limpiar(fn_complejo(x))
        return fn_real(convertir_entrada(ctx, _a_real(x)))
    return aplicar


def _a_radianes(ctx, x):
    if ctx.angulo == 'DEG':
        return math.radians(x)
    if ctx.angulo == 'GRA':
        return x * math.pi / 200.0
    return x


def _de_radianes(ctx, x):
    if ctx.angulo == 'DEG':
        return math.degrees(x)
    if ctx.angulo == 'GRA':
        return x * 200.0 / math.pi
    return x


def _fact(x):
    n = _a_entero(x)
    if n < 0:
        raise ErrorCalculo('El factorial exige un entero no negativo')
    if n > 5000:
        raise ErrorCalculo('El factorial es demasiado grande')
    return math.factorial(n)


def _raiz(x):
    if isinstance(x, complex):
        return _limpiar(cmath.sqrt(x))
    r = _a_real(x)
    if r < 0:
        return _limpiar(cmath.sqrt(complex(r)))
    if _es_exacto(x):
        f = Fraction(x)
        rn = math.isqrt(f.numerator)
        rd = math.isqrt(f.denominator)
        if rn * rn == f.numerator and rd * rd == f.denominator:
            return Fraction(rn, rd)
    return math.sqrt(r)


def _cbrt(x):
    if isinstance(x, complex):
        return _limpiar(x ** (1 / 3))
    r = _a_real(x)
    return math.copysign(abs(r) ** (1 / 3), r)


def _log_base(base, x):
    b, v = _a_real(base), _a_real(x)
    if b <= 0 or b == 1:
        raise ErrorCalculo('La base del logaritmo debe ser positiva y distinta de 1')
    if v <= 0:
        return _limpiar(cmath.log(complex(v)) / cmath.log(complex(b)))
    return math.log(v) / math.log(b)


def _ln(x):
    if isinstance(x, complex) or _a_real(x) <= 0:
        z = complex(x)
        if z == 0:
            raise ErrorCalculo('El logaritmo de cero no existe')
        return _limpiar(cmath.log(z))
    return math.log(_a_real(x))


def _log10(x):
    if isinstance(x, complex) or _a_real(x) <= 0:
        z = complex(x)
        if z == 0:
            raise ErrorCalculo('El logaritmo de cero no existe')
        return _limpiar(cmath.log10(z))
    return math.log10(_a_real(x))


def _ncr(n, r):
    ni, ri = _a_entero(n), _a_entero(r)
    if ni < 0 or ri < 0 or ri > ni:
        raise ErrorCalculo('nCr exige 0 ≤ r ≤ n')
    return math.comb(ni, ri)


def _npr(n, r):
    ni, ri = _a_entero(n), _a_entero(r)
    if ni < 0 or ri < 0 or ri > ni:
        raise ErrorCalculo('nPr exige 0 ≤ r ≤ n')
    return math.perm(ni, ri)


def _redondear(x, n=None):
    if n is None:
        return round(_a_real(x))
    return round(_a_real(x), _a_entero(n))


def _inversa(ctx, x, fn_real, fn_complejo):
    """asin/acos: fuera de [-1, 1] el resultado es complejo, no un error."""
    if isinstance(x, complex):
        return _limpiar(fn_complejo(x))
    r = _a_real(x)
    if -1 <= r <= 1:
        return _de_radianes(ctx, fn_real(r))
    return _limpiar(fn_complejo(complex(r)))


def _polar(x, y):
    xr, yr = _a_real(x), _a_real(y)
    return (math.hypot(xr, yr), math.atan2(yr, xr))


FUNCIONES: dict[str, tuple] = {
    # trigonometría directa
    'sin':  (1, _trig(math.sin, cmath.sin, _a_radianes)),
    'cos':  (1, _trig(math.cos, cmath.cos, _a_radianes)),
    'tan':  (1, _trig(math.tan, cmath.tan, _a_radianes)),
    'sec':  (1, lambda ctx, x: 1 / math.cos(_a_radianes(ctx, _a_real(x)))),
    'csc':  (1, lambda ctx, x: 1 / math.sin(_a_radianes(ctx, _a_real(x)))),
    'cot':  (1, lambda ctx, x: 1 / math.tan(_a_radianes(ctx, _a_real(x)))),
    # trigonometría inversa: devuelve en la unidad angular activa
    'asin': (1, lambda ctx, x: _inversa(ctx, x, math.asin, cmath.asin)),
    'acos': (1, lambda ctx, x: _inversa(ctx, x, math.acos, cmath.acos)),
    'atan': (1, lambda ctx, x: _de_radianes(ctx, math.atan(_a_real(x)))),
    'atan2': (2, lambda ctx, y, x: _de_radianes(ctx, math.atan2(_a_real(y), _a_real(x)))),
    # hiperbólicas
    'sinh':  (1, lambda ctx, x: math.sinh(_a_real(x))),
    'cosh':  (1, lambda ctx, x: math.cosh(_a_real(x))),
    'tanh':  (1, lambda ctx, x: math.tanh(_a_real(x))),
    'asinh': (1, lambda ctx, x: math.asinh(_a_real(x))),
    'acosh': (1, lambda ctx, x: math.acosh(_a_real(x))),
    'atanh': (1, lambda ctx, x: math.atanh(_a_real(x))),
    # logaritmos y exponenciales
    'ln':    (1, lambda ctx, x: _ln(x)),
    'log':   (1, lambda ctx, x: _log10(x)),
    'log2':  (1, lambda ctx, x: _log_base(2, x)),
    'logab': (2, lambda ctx, b, x: _log_base(b, x)),
    'exp':   (1, lambda ctx, x: math.exp(_a_real(x)) if not isinstance(x, complex)
              else _limpiar(cmath.exp(x))),
    # raíces y potencias
    'sqrt': (1, lambda ctx, x: _raiz(x)),
    'cbrt': (1, lambda ctx, x: _cbrt(x)),
    'root': (2, lambda ctx, n, x: _potencia(x, Fraction(1, _a_entero(n)))),
    'inv':  (1, lambda ctx, x: _potencia(x, -1)),
    # redondeo y signo
    'abs':   (1, lambda ctx, x: abs(x)),
    'sign':  (1, lambda ctx, x: (_a_real(x) > 0) - (_a_real(x) < 0)),
    'floor': (1, lambda ctx, x: math.floor(_a_real(x))),
    'ceil':  (1, lambda ctx, x: math.ceil(_a_real(x))),
    'int':   (1, lambda ctx, x: math.trunc(_a_real(x))),
    'frac':  (1, lambda ctx, x: x - math.trunc(_a_real(x))),
    'round': ((1, 2), lambda ctx, x, n=None: _redondear(x, n)),
    # enteros y combinatoria
    'fact': (1, lambda ctx, x: _fact(x)),
    'nCr':  (2, lambda ctx, n, r: _ncr(n, r)),
    'nPr':  (2, lambda ctx, n, r: _npr(n, r)),
    'gcd':  (2, lambda ctx, a, b: math.gcd(_a_entero(a), _a_entero(b))),
    'lcm':  (2, lambda ctx, a, b: math.lcm(_a_entero(a), _a_entero(b))),
    'mod':  (2, lambda ctx, a, b: _a_entero(a) % _a_entero(b) if _a_entero(b) != 0
             else _error_div()),
    # extremos
    'min': ((1, 9), lambda ctx, *xs: min(xs, key=_a_real)),
    'max': ((1, 9), lambda ctx, *xs: max(xs, key=_a_real)),
    # conversiones angulares
    'deg': (1, lambda ctx, x: math.degrees(_a_real(x))),
    'rad': (1, lambda ctx, x: math.radians(_a_real(x))),
    # coordenadas
    'pol': (2, lambda ctx, x, y: _polar(x, y)[0]),
    'arg': ((1, 2), lambda ctx, x, y=None: _de_radianes(
        ctx, math.atan2(_a_real(y), _a_real(x)) if y is not None
        else cmath.phase(complex(x)))),
    # complejos
    're':   (1, lambda ctx, z: complex(z).real),
    'im':   (1, lambda ctx, z: complex(z).imag),
    'conj': (1, lambda ctx, z: _limpiar(complex(z).conjugate())),
    # aleatorios
    'rand':    (0, lambda ctx: random.random()),
    'randint': (2, lambda ctx, a, b: random.randint(_a_entero(a), _a_entero(b))),
}


def _error_div():
    raise ErrorCalculo('No se puede dividir entre cero')


# ---------------------------------------------------------------------------
# Evaluación
# ---------------------------------------------------------------------------

class Contexto:
    def __init__(self, angulo='DEG', variables=None):
        self.angulo = angulo
        self.variables = dict(variables or {})


def evaluar(nodo, ctx: Contexto):
    tipo = nodo[0]

    if tipo == 'num':
        return nodo[1]

    if tipo == 'var':
        nombre = nodo[1]
        if nombre in ctx.variables:
            return ctx.variables[nombre]
        if nombre in CONSTANTES:
            return CONSTANTES[nombre]
        if nombre in ('i', 'j'):
            return complex(0, 1)
        if nombre in CONSTANTES_FISICAS:
            return CONSTANTES_FISICAS[nombre][0]
        raise ErrorCalculo(f'No sé qué es «{nombre}»')

    if tipo == 'neg':
        return -evaluar(nodo[1], ctx)

    if tipo == 'pct':
        return evaluar(nodo[1], ctx) / 100

    if tipo == 'grados':
        # 45° significa 45 grados aunque el modo sea RAD.
        return math.radians(_a_real(evaluar(nodo[1], ctx))) \
            if ctx.angulo != 'DEG' else evaluar(nodo[1], ctx)

    if tipo == 'op':
        op = nodo[1]

        # El porcentaje es contextual, como en los fx: 200+10% = 220.
        if op in ('+', '-') and nodo[3][0] == 'pct':
            izq = evaluar(nodo[2], ctx)
            frac = evaluar(nodo[3][1], ctx) / 100
            return izq + izq * frac if op == '+' else izq - izq * frac

        a = evaluar(nodo[2], ctx)
        b = evaluar(nodo[3], ctx)

        if op == '+':
            return a + b
        if op == '-':
            return a - b
        if op == '*':
            return _limpiar(a * b)
        if op == '/':
            if b == 0:
                raise ErrorCalculo('No se puede dividir entre cero')
            if _es_exacto(a) and _es_exacto(b):
                return Fraction(a) / Fraction(b)
            return _limpiar(a / b)
        if op == '^':
            return _potencia(a, b)

    if tipo == 'llamada':
        nombre, args = nodo[1], nodo[2]
        if nombre not in FUNCIONES:
            raise ErrorCalculo(f'No conozco la función «{nombre}»')
        aridad, fn = FUNCIONES[nombre]
        valores = [evaluar(a, ctx) for a in args]

        if isinstance(aridad, tuple):
            minimo, maximo = aridad
            if not (minimo <= len(valores) <= maximo):
                raise ErrorCalculo(f'«{nombre}» no admite {len(valores)} argumentos')
        elif len(valores) != aridad:
            raise ErrorCalculo(
                f'«{nombre}» necesita {aridad} argumento(s), recibió {len(valores)}')

        try:
            return fn(ctx, *valores)
        except ErrorCalculo:
            raise
        except ZeroDivisionError:
            raise ErrorCalculo('No se puede dividir entre cero')
        except (ValueError, OverflowError) as exc:
            raise ErrorCalculo(f'«{nombre}» está fuera de su dominio ({exc})')

    raise ErrorCalculo('Expresión no válida')


def calcular(texto: str, ctx: Contexto):
    return evaluar(analizar(texto), ctx)


# ---------------------------------------------------------------------------
# Formato de salida
# ---------------------------------------------------------------------------

DIGITOS_MAXIMOS = 14


def _formatear_real(x: float, formato='NORM', decimales=10) -> str:
    if x != x:
        return 'No definido'
    if x in (float('inf'), float('-inf')):
        return '∞' if x > 0 else '-∞'

    if formato == 'FIX':
        return f'{x:.{decimales}f}'

    if formato == 'SCI':
        texto = f'{x:.{max(0, decimales - 1)}e}'
        mant, expo = texto.split('e')
        return f'{mant}×10^{int(expo)}'

    if formato == 'ENG':
        if x == 0:
            return '0×10^0'
        expo = int(math.floor(math.log10(abs(x))))
        expo -= expo % 3
        mant = x / (10 ** expo)
        return f'{round(mant, max(0, decimales - 1)):g}×10^{expo}'

    # NORM: notación científica sólo cuando el número se sale de rango.
    if x != 0 and (abs(x) >= 1e10 or abs(x) < 1e-9):
        texto = f'{x:.{DIGITOS_MAXIMOS - 1}e}'
        mant, expo = texto.split('e')
        mant = mant.rstrip('0').rstrip('.')
        return f'{mant}×10^{int(expo)}'

    texto = f'{x:.{DIGITOS_MAXIMOS}g}'
    if 'e' in texto or 'E' in texto:
        mant, expo = texto.lower().split('e')
        return f'{mant}×10^{int(expo)}'
    return texto


def formatear(valor, formato='NORM', decimales=10) -> dict:
    """Devuelve el valor listo para pintar: principal, alterno y exactitud."""
    if isinstance(valor, tuple):  # coordenadas polares/rectangulares
        return {
            'principal': ', '.join(_formatear_real(_a_real(v), formato, decimales)
                                   for v in valor),
            'alterno': '',
            'exacto': False,
        }

    if isinstance(valor, complex):
        re_, im_ = valor.real, valor.imag
        parte_re = _formatear_real(re_, formato, decimales)
        parte_im = _formatear_real(abs(im_), formato, decimales)
        signo = '-' if im_ < 0 else '+'
        if abs(re_) < 1e-15:
            principal = f'{"-" if im_ < 0 else ""}{parte_im}i'
        else:
            principal = f'{parte_re} {signo} {parte_im}i'
        modulo = _formatear_real(abs(valor), formato, decimales)
        angulo = _formatear_real(math.degrees(cmath.phase(valor)), formato, decimales)
        return {'principal': principal, 'alterno': f'módulo {modulo} ∠ {angulo}°',
                'exacto': False}

    if isinstance(valor, (int, Fraction)):
        f = Fraction(valor)
        if f.denominator == 1:
            entero = int(f)
            if abs(entero) < 10 ** DIGITOS_MAXIMOS:
                return {'principal': str(entero), 'alterno': '', 'exacto': True}
            return {'principal': _formatear_real(float(f), formato, decimales),
                    'alterno': '', 'exacto': False}
        decimal = _formatear_real(float(f), formato, decimales)
        # Sólo se muestra como fracción si es legible, como hacen los fx.
        if f.denominator <= 10 ** 6 and abs(f.numerator) <= 10 ** 10:
            entera, resto = divmod(abs(f.numerator), f.denominator)
            signo = '-' if f < 0 else ''
            mixta = f'{signo}{entera} {resto}/{f.denominator}' if entera else ''
            return {
                'principal': f'{f.numerator}/{f.denominator}',
                'alterno': decimal,
                'mixta': mixta,
                'exacto': True,
            }
        return {'principal': decimal, 'alterno': '', 'exacto': False}

    return {'principal': _formatear_real(float(valor), formato, decimales),
            'alterno': '', 'exacto': False}


# ---------------------------------------------------------------------------
# Estadística
# ---------------------------------------------------------------------------

def estadistica_1var(datos: list[float]) -> dict:
    xs = [float(v) for v in datos]
    n = len(xs)
    if n == 0:
        raise ErrorCalculo('No hay datos')

    suma = sum(xs)
    suma2 = sum(v * v for v in xs)
    media = suma / n
    var_p = suma2 / n - media * media
    var_p = max(var_p, 0.0)
    var_m = (suma2 - n * media * media) / (n - 1) if n > 1 else float('nan')
    ordenados = sorted(xs)

    def cuantil(p):
        if n == 1:
            return ordenados[0]
        pos = p * (n - 1)
        bajo = math.floor(pos)
        alto = math.ceil(pos)
        return ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (pos - bajo)

    return {
        'n': n, 'Σx': suma, 'Σx²': suma2, 'x̄': media,
        'σx (población)': math.sqrt(var_p),
        'sx (muestra)': math.sqrt(var_m) if n > 1 else float('nan'),
        'varianza (población)': var_p,
        'varianza (muestra)': var_m,
        'mínimo': ordenados[0], 'Q1': cuantil(0.25), 'mediana': cuantil(0.5),
        'Q3': cuantil(0.75), 'máximo': ordenados[-1],
        'rango': ordenados[-1] - ordenados[0],
    }


def _regresion_lineal(xs, ys):
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    syy = sum(y * y for y in ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    den = n * sxx - sx * sx
    if abs(den) < 1e-15:
        raise ErrorCalculo('Los valores de x no varían: no hay recta de regresión')
    b = (n * sxy - sx * sy) / den
    a = (sy - b * sx) / n
    den_r = math.sqrt(den * (n * syy - sy * sy))
    r = (n * sxy - sx * sy) / den_r if den_r > 0 else float('nan')
    return a, b, r, sx, sy, sxx, syy, sxy


def estadistica_2var(datos: list[list[float]], modelo='lineal') -> dict:
    if not datos:
        raise ErrorCalculo('No hay datos')
    xs = [float(p[0]) for p in datos]
    ys = [float(p[1]) for p in datos]
    n = len(xs)
    if n < 2:
        raise ErrorCalculo('Hacen falta al menos dos puntos')

    # Cada modelo se ajusta linealizando y luego aplicando regresión lineal.
    if modelo == 'lineal':
        ux, uy = xs, ys
    elif modelo == 'logaritmica':
        if any(x <= 0 for x in xs):
            raise ErrorCalculo('El modelo logarítmico exige x > 0')
        ux, uy = [math.log(x) for x in xs], ys
    elif modelo == 'exponencial':
        if any(y <= 0 for y in ys):
            raise ErrorCalculo('El modelo exponencial exige y > 0')
        ux, uy = xs, [math.log(y) for y in ys]
    elif modelo == 'potencial':
        if any(x <= 0 for x in xs) or any(y <= 0 for y in ys):
            raise ErrorCalculo('El modelo potencial exige x > 0 e y > 0')
        ux, uy = [math.log(x) for x in xs], [math.log(y) for y in ys]
    elif modelo == 'inversa':
        if any(x == 0 for x in xs):
            raise ErrorCalculo('El modelo inverso exige x ≠ 0')
        ux, uy = [1 / x for x in xs], ys
    else:
        raise ErrorCalculo(f'Modelo de regresión desconocido: {modelo}')

    a, b, r, sx, sy, sxx, syy, sxy = _regresion_lineal(ux, uy)

    if modelo == 'exponencial':
        formula = f'y = {math.exp(a):.10g}·e^({b:.10g}x)'
    elif modelo == 'potencial':
        formula = f'y = {math.exp(a):.10g}·x^{b:.10g}'
    elif modelo == 'logaritmica':
        formula = f'y = {a:.10g} + {b:.10g}·ln(x)'
    elif modelo == 'inversa':
        formula = f'y = {a:.10g} + {b:.10g}/x'
    else:
        formula = f'y = {a:.10g} + {b:.10g}x'

    return {
        'n': n, 'Σx': sum(xs), 'Σy': sum(ys),
        'Σx²': sum(x * x for x in xs), 'Σy²': sum(y * y for y in ys),
        'Σxy': sum(x * y for x, y in zip(xs, ys)),
        'x̄': sum(xs) / n, 'ȳ': sum(ys) / n,
        'modelo': modelo, 'A (ordenada)': a, 'B (pendiente)': b,
        'r (correlación)': r, 'r²': r * r if r == r else float('nan'),
        'fórmula': formula,
    }


# ---------------------------------------------------------------------------
# Ecuaciones
# ---------------------------------------------------------------------------

def raices_polinomio(coeficientes: list[float]) -> list[complex]:
    """Raíces por Durand-Kerner. Vale para cualquier grado, no sólo 2 y 3."""
    coef = [complex(c) for c in coeficientes]
    while coef and abs(coef[0]) < 1e-15:
        coef.pop(0)
    if len(coef) < 2:
        raise ErrorCalculo('No es una ecuación: falta el término principal')

    grado = len(coef) - 1
    normal = [c / coef[0] for c in coef]

    def polinomio(z):
        r = 0j
        for c in normal:
            r = r * z + c
        return r

    semilla = complex(0.4, 0.9)
    raices = [semilla ** k for k in range(grado)]

    for _ in range(500):
        maximo = 0.0
        nuevas = []
        for i, zi in enumerate(raices):
            den = 1 + 0j
            for j, zj in enumerate(raices):
                if i != j:
                    den *= (zi - zj)
            if abs(den) < 1e-300:
                den = 1e-300
            delta = polinomio(zi) / den
            nuevas.append(zi - delta)
            maximo = max(maximo, abs(delta))
        raices = nuevas
        if maximo < 1e-14:
            break

    limpias = []
    for z in raices:
        if abs(z.imag) < 1e-9 * max(1.0, abs(z.real)):
            z = complex(round(z.real, 12), 0.0)
        limpias.append(z)
    limpias.sort(key=lambda z: (round(z.real, 9), round(z.imag, 9)))
    return limpias


def resolver_sistema(matriz: list[list[float]]) -> list[float]:
    """Gauss con pivoteo parcial. Cada fila es [a1, a2, …, an, término]."""
    a = [[float(v) for v in fila] for fila in matriz]
    n = len(a)
    if any(len(fila) != n + 1 for fila in a):
        raise ErrorCalculo('Cada ecuación debe tener tantos coeficientes como incógnitas, más el término independiente')

    for col in range(n):
        pivote = max(range(col, n), key=lambda f: abs(a[f][col]))
        if abs(a[pivote][col]) < 1e-13:
            raise ErrorCalculo('El sistema no tiene solución única')
        a[col], a[pivote] = a[pivote], a[col]
        for fila in range(col + 1, n):
            factor = a[fila][col] / a[col][col]
            for k in range(col, n + 1):
                a[fila][k] -= factor * a[col][k]

    x = [0.0] * n
    for fila in range(n - 1, -1, -1):
        suma = sum(a[fila][k] * x[k] for k in range(fila + 1, n))
        x[fila] = (a[fila][n] - suma) / a[fila][fila]
    return x


def resolver_expresion(expr: str, ctx: Contexto, inicial=1.0) -> float:
    """Busca una raíz de expr(X)=0 con Newton y respaldo por bisección."""
    arbol = analizar(expr)

    def f(x):
        ctx.variables['X'] = x
        return _a_real(evaluar(arbol, ctx))

    x = float(inicial)
    for _ in range(200):
        fx = f(x)
        if abs(fx) < 1e-13:
            return x
        h = 1e-7 * max(1.0, abs(x))
        derivada = (f(x + h) - f(x - h)) / (2 * h)
        if abs(derivada) < 1e-14:
            break
        siguiente = x - fx / derivada
        if abs(siguiente - x) < 1e-14:
            return siguiente
        x = siguiente

    # Newton no convergió: se busca un cambio de signo y se bisecta.
    a, b = -1000.0, 1000.0
    paso = 0.5
    anterior_x, anterior_y = a, f(a)
    while anterior_x < b:
        actual_x = anterior_x + paso
        try:
            actual_y = f(actual_x)
        except ErrorCalculo:
            anterior_x, anterior_y = actual_x, float('nan')
            continue
        if anterior_y == anterior_y and actual_y == actual_y and anterior_y * actual_y <= 0:
            lo, hi = anterior_x, actual_x
            for _ in range(200):
                medio = (lo + hi) / 2
                if f(lo) * f(medio) <= 0:
                    hi = medio
                else:
                    lo = medio
            return (lo + hi) / 2
        anterior_x, anterior_y = actual_x, actual_y

    raise ErrorCalculo('No se encontró ninguna solución')


# ---------------------------------------------------------------------------
# Cálculo numérico
# ---------------------------------------------------------------------------

def derivada(expr: str, punto: float, ctx: Contexto) -> float:
    arbol = analizar(expr)

    def f(x):
        ctx.variables['X'] = x
        return _a_real(evaluar(arbol, ctx))

    x0 = float(punto)
    h = 1e-4 * max(1.0, abs(x0))
    # Richardson: combina dos diferencias centrales para cancelar el error de h².
    d1 = (f(x0 + h) - f(x0 - h)) / (2 * h)
    d2 = (f(x0 + h / 2) - f(x0 - h / 2)) / h
    return (4 * d2 - d1) / 3


def integral(expr: str, a: float, b: float, ctx: Contexto, divisiones=2000) -> float:
    arbol = analizar(expr)

    def f(x):
        ctx.variables['X'] = x
        return _a_real(evaluar(arbol, ctx))

    a, b = float(a), float(b)
    if a == b:
        return 0.0
    signo = 1.0
    if a > b:
        a, b, signo = b, a, -1.0

    n = divisiones if divisiones % 2 == 0 else divisiones + 1
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += f(a + i * h) * (4 if i % 2 else 2)
    return signo * total * h / 3


def tabla(expr: str, desde: float, hasta: float, paso: float, ctx: Contexto) -> list[dict]:
    if paso == 0:
        raise ErrorCalculo('El paso no puede ser cero')
    arbol = analizar(expr)
    filas = []
    x = float(desde)
    limite = float(hasta)
    contador = 0
    while (paso > 0 and x <= limite + 1e-12) or (paso < 0 and x >= limite - 1e-12):
        contador += 1
        if contador > 300:
            raise ErrorCalculo('La tabla tendría demasiadas filas (máximo 300)')
        ctx.variables['X'] = x
        try:
            y = evaluar(arbol, ctx)
            filas.append({'x': x, 'y': formatear(y)['principal']})
        except ErrorCalculo as exc:
            filas.append({'x': x, 'y': f'— ({exc})'})
        x += float(paso)
    return filas


# ---------------------------------------------------------------------------
# Base-N y teoría de números
# ---------------------------------------------------------------------------

BITS = 32
MASCARA = (1 << BITS) - 1


def _a_con_signo(v: int) -> int:
    v &= MASCARA
    return v - (1 << BITS) if v >> (BITS - 1) else v


def convertir_base(texto: str, desde: int, hacia: int) -> str:
    texto = texto.strip().upper()
    if not texto:
        raise ErrorCalculo('No hay ningún valor que convertir')
    try:
        valor = int(texto, desde)
    except ValueError:
        raise ErrorCalculo(f'«{texto}» no es un número válido en base {desde}')
    return _representar_base(valor, hacia)


def _representar_base(valor: int, base: int) -> str:
    if base == 10:
        return str(valor)
    v = valor & MASCARA
    digitos = '0123456789ABCDEF'
    if v == 0:
        return '0'
    salida = ''
    while v:
        salida = digitos[v % base] + salida
        v //= base
    return salida


def logica(operacion: str, a: int, b: int = 0) -> dict:
    a &= MASCARA
    b &= MASCARA
    operaciones = {
        'and': lambda: a & b,
        'or': lambda: a | b,
        'xor': lambda: a ^ b,
        'xnor': lambda: ~(a ^ b),
        'not': lambda: ~a,
        'neg': lambda: -a,
    }
    if operacion not in operaciones:
        raise ErrorCalculo(f'Operación lógica desconocida: {operacion}')
    r = operaciones[operacion]() & MASCARA
    return {
        'dec': _a_con_signo(r),
        'bin': _representar_base(r, 2),
        'oct': _representar_base(r, 8),
        'hex': _representar_base(r, 16),
    }


def factorizar(n: int) -> dict:
    n = int(n)
    if n < 2:
        raise ErrorCalculo('La factorización exige un entero mayor o igual que 2')
    if n > 10 ** 15:
        raise ErrorCalculo('El número es demasiado grande para factorizarlo aquí')

    original = n
    factores: dict[int, int] = {}
    for p in (2, 3, 5):
        while n % p == 0:
            factores[p] = factores.get(p, 0) + 1
            n //= p
    d = 7
    incrementos = (4, 2, 4, 2, 4, 6, 2, 6)
    k = 0
    while d * d <= n:
        while n % d == 0:
            factores[d] = factores.get(d, 0) + 1
            n //= d
        d += incrementos[k % len(incrementos)]
        k += 1
    if n > 1:
        factores[n] = factores.get(n, 0) + 1

    partes = [f'{p}^{e}' if e > 1 else str(p) for p, e in sorted(factores.items())]
    divisores = 1
    for e in factores.values():
        divisores *= e + 1

    return {
        'numero': original,
        'factores': {str(p): e for p, e in sorted(factores.items())},
        'expresion': ' × '.join(partes),
        'es_primo': len(factores) == 1 and sum(factores.values()) == 1,
        'numero_de_divisores': divisores,
    }


# ---------------------------------------------------------------------------
# Unidades
# ---------------------------------------------------------------------------

def convertir_unidad(valor: float, desde: str, hacia: str) -> float:
    valor = float(valor)

    if desde in TEMPERATURAS and hacia in TEMPERATURAS:
        kelvin = {'C': lambda v: v + 273.15,
                  'F': lambda v: (v - 32) * 5 / 9 + 273.15,
                  'K': lambda v: v}[desde](valor)
        return {'C': lambda v: v - 273.15,
                'F': lambda v: (v - 273.15) * 9 / 5 + 32,
                'K': lambda v: v}[hacia](kelvin)

    for familia in UNIDADES.values():
        u = familia['unidades']
        if desde in u and hacia in u:
            return valor * u[desde] / u[hacia]

    raise ErrorCalculo(f'No sé convertir de «{desde}» a «{hacia}»')


# ---------------------------------------------------------------------------
# Interfaz con JavaScript
# ---------------------------------------------------------------------------

class Sesion:
    """Guarda el estado entre pulsaciones: variables, Ans, modo angular."""

    def __init__(self):
        self.variables: dict[str, object] = {}
        self.angulo = 'DEG'
        self.formato = 'NORM'
        self.decimales = 10
        self.historial: list[dict] = []

    def contexto(self) -> Contexto:
        return Contexto(self.angulo, self.variables)


SESION = Sesion()


def _numero_json(v):
    """json.dumps no admite inf ni nan de forma portable."""
    if isinstance(v, float):
        if v != v:
            return None
        if v in (float('inf'), float('-inf')):
            return None
    return v


def _saneado(obj):
    if isinstance(obj, dict):
        return {k: _saneado(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_saneado(v) for v in obj]
    if isinstance(obj, complex):
        return {'re': _numero_json(obj.real), 'im': _numero_json(obj.imag)}
    if isinstance(obj, Fraction):
        return float(obj)
    return _numero_json(obj)


def ejecutar(peticion_json: str) -> str:
    """Punto de entrada único desde JavaScript. Recibe y devuelve JSON."""
    try:
        p = json.loads(peticion_json)
        cmd = p.get('cmd')

        if cmd == 'configurar':
            if 'angulo' in p:
                SESION.angulo = p['angulo']
            if 'formato' in p:
                SESION.formato = p['formato']
            if 'decimales' in p:
                SESION.decimales = int(p['decimales'])
            return json.dumps({'ok': True, 'angulo': SESION.angulo,
                               'formato': SESION.formato,
                               'decimales': SESION.decimales})

        if cmd == 'evaluar':
            ctx = SESION.contexto()
            valor = calcular(p['expr'], ctx)
            SESION.variables.update(ctx.variables)
            SESION.variables['Ans'] = valor
            salida = formatear(valor, SESION.formato, SESION.decimales)
            entrada = {'expr': p['expr'], **salida}
            SESION.historial.insert(0, entrada)
            del SESION.historial[40:]
            return json.dumps({'ok': True, **salida,
                               'historial': SESION.historial[:40]})

        if cmd == 'guardar_variable':
            ctx = SESION.contexto()
            valor = calcular(p['expr'], ctx) if p.get('expr') else SESION.variables.get('Ans', 0)
            SESION.variables[p['nombre']] = valor
            return json.dumps({'ok': True, 'nombre': p['nombre'],
                               **formatear(valor, SESION.formato, SESION.decimales)})

        if cmd == 'variables':
            return json.dumps({'ok': True, 'variables': {
                k: formatear(v, SESION.formato, SESION.decimales)['principal']
                for k, v in sorted(SESION.variables.items())}})

        if cmd == 'limpiar':
            SESION.variables.clear()
            SESION.historial.clear()
            return json.dumps({'ok': True})

        if cmd == 'estadistica':
            if p.get('tipo') == '2var':
                r = estadistica_2var(p['datos'], p.get('modelo', 'lineal'))
            else:
                r = estadistica_1var(p['datos'])
            return json.dumps({'ok': True, 'resultados': _saneado(r)})

        if cmd == 'polinomio':
            raices = raices_polinomio(p['coeficientes'])
            return json.dumps({'ok': True, 'raices': [
                formatear(_limpiar(z), SESION.formato, SESION.decimales)['principal']
                for z in raices]})

        if cmd == 'sistema':
            x = resolver_sistema(p['matriz'])
            nombres = ['x', 'y', 'z', 'w'][:len(x)]
            return json.dumps({'ok': True, 'soluciones': [
                {'nombre': n, 'valor': _formatear_real(v, SESION.formato, SESION.decimales)}
                for n, v in zip(nombres, x)]})

        if cmd == 'resolver':
            raiz = resolver_expresion(p['expr'], SESION.contexto(),
                                      float(p.get('inicial', 1)))
            return json.dumps({'ok': True,
                               'principal': _formatear_real(raiz, SESION.formato,
                                                            SESION.decimales)})

        if cmd == 'derivada':
            d = derivada(p['expr'], float(p['punto']), SESION.contexto())
            return json.dumps({'ok': True,
                               'principal': _formatear_real(d, SESION.formato,
                                                            SESION.decimales)})

        if cmd == 'integral':
            v = integral(p['expr'], float(p['a']), float(p['b']), SESION.contexto())
            return json.dumps({'ok': True,
                               'principal': _formatear_real(v, SESION.formato,
                                                            SESION.decimales)})

        if cmd == 'tabla':
            filas = tabla(p['expr'], float(p['desde']), float(p['hasta']),
                          float(p['paso']), SESION.contexto())
            return json.dumps({'ok': True, 'filas': _saneado(filas)})

        if cmd == 'base':
            return json.dumps({'ok': True, 'valor': convertir_base(
                p['valor'], int(p['desde']), int(p['hacia']))})

        if cmd == 'logica':
            return json.dumps({'ok': True, 'resultado': logica(
                p['op'], int(p['a']), int(p.get('b', 0)))})

        if cmd == 'factorizar':
            return json.dumps({'ok': True, 'resultado': _saneado(
                factorizar(int(p['n'])))})

        if cmd == 'unidad':
            v = convertir_unidad(float(p['valor']), p['desde'], p['hacia'])
            return json.dumps({'ok': True,
                               'principal': _formatear_real(v, SESION.formato,
                                                            SESION.decimales)})

        if cmd == 'constantes':
            return json.dumps({'ok': True, 'constantes': [
                {'simbolo': k, 'valor': _formatear_real(v[0]), 'unidad': v[1],
                 'descripcion': v[2]}
                for k, v in CONSTANTES_FISICAS.items()]})

        return json.dumps({'ok': False, 'error': f'Orden desconocida: {cmd}'})

    except ErrorCalculo as exc:
        return json.dumps({'ok': False, 'error': str(exc)})
    except ZeroDivisionError:
        return json.dumps({'ok': False, 'error': 'No se puede dividir entre cero'})
    except (KeyError, TypeError, ValueError) as exc:
        return json.dumps({'ok': False, 'error': f'Petición mal formada: {exc}'})
    except RecursionError:
        return json.dumps({'ok': False, 'error': 'La expresión es demasiado profunda'})
