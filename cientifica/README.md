# Calculadora científica (motor en Python)

Calculadora científica completa cuyo cálculo lo hace **Python ejecutándose en el
navegador**, mediante [Pyodide](https://pyodide.org). La interfaz es HTML y CSS;
JavaScript sólo dibuja el teclado y traslada órdenes en JSON al motor.

**En vivo:** https://fr4nkl1n20.github.io/calculadora-web/cientifica/

## Por qué está partida así

`motor.py` no importa nada del navegador. Esa frontera es deliberada:

- El mismo archivo se ejecuta en CPython, así que **el CI lo prueba sin
  navegador** — 74 pruebas en menos de un segundo.
- La interfaz puede cambiar por completo sin tocar una línea de matemáticas.
- Toda la comunicación pasa por una sola función, `ejecutar(json) -> json`, lo
  que evita conversiones de objetos entre Python y JavaScript.

## Qué sabe hacer

**Expresiones**
Prioridad de operadores, paréntesis, multiplicación implícita (`2π`, `3(4+5)`),
menos unario con la precedencia de las fx (`−2² = −4`), potencias asociativas
por la derecha (`2^3^2 = 512`), porcentaje contextual (`200+10% = 220`),
notación científica y sufijo de grados (`45°`).

**Aritmética exacta**
Los literales se leen como fracciones, así que `0,1 + 0,2` da exactamente
`3/10` y no `0,30000000000000004`. El resultado se muestra como fracción, con
su decimal al lado. Las funciones que no pueden ser exactas devuelven decimal.

**Funciones**

| Familia | Disponible |
| --- | --- |
| Trigonometría | `sin cos tan sec csc cot` y sus inversas, en DEG, RAD y GRA |
| Hiperbólicas | `sinh cosh tanh asinh acosh atanh` |
| Logaritmos | `ln log log2 logab(base, x) exp` |
| Raíces y potencias | `√ ∛ sqrt cbrt root(n, x) x² x³ x^y x⁻¹` |
| Enteros | `fact n! nCr nPr gcd lcm mod floor ceil int frac round abs sign` |
| Complejos | `i`, `re im conj arg`, y raíces de negativos |
| Aleatorios | `rand randint(a, b)` |
| Coordenadas | `pol rec atan2` |

**Herramientas** (pestañas)

- **Estadística** de una variable (n, Σx, Σx², media, σ y s, cuartiles, mediana,
  rango) y de dos variables con regresión **lineal, logarítmica, exponencial,
  potencial e inversa**, con r y r².
- **Ecuaciones**: raíces de polinomios de cualquier grado (Durand-Kerner,
  incluidas las complejas), sistemas lineales n×n (Gauss con pivoteo) y
  resolución numérica de `f(X) = 0` (Newton con respaldo por bisección).
- **Cálculo**: derivada en un punto (Richardson) e integral definida (Simpson).
- **Tabla** de valores de una función.
- **Base-N**: conversión entre binario, octal, decimal y hexadecimal, y
  operaciones lógicas AND, OR, XOR, XNOR, NOT y NEG en 32 bits. Además,
  factorización en primos con número de divisores.
- **Unidades**: longitud, masa, volumen, energía, presión, velocidad y
  temperatura.
- **Constantes**: 18 constantes físicas del SI, insertables en la expresión.

**Memoria y estado**
Variables A–F, X, Y y M; `Ans` con el último resultado; historial de 40
operaciones reutilizables con un clic; modos angulares DEG/RAD/GRA y formatos
NORM/FIX/SCI/ENG.

## Teclado

`SHIFT` activa la función escrita en dorado sobre cada tecla. `AC` limpia la
pantalla pero **conserva** las variables y el historial; `SHIFT` + `AC` (RESET)
los borra. También puedes escribir la expresión directamente y pulsar `Enter`.

## Pruebas

```bash
cd cientifica
python -m unittest discover -s pruebas -p "test_*.py" -v
```

Son 74 pruebas de Python puro y las ejecuta GitHub Actions en cada push. Además
hay dos páginas que comprueban lo que Python no puede ver, y que necesitan un
servidor (`python -m http.server` desde la raíz del proyecto):

| Página | Qué verifica |
| --- | --- |
| `pruebas/navegador.html` | Que el motor se comporta igual bajo Pyodide que en CPython |
| `pruebas/interfaz.html` | Maneja la calculadora real en un iframe: pulsa teclas y lee la pantalla |

## Limitaciones que conviene conocer

- **Necesita conexión la primera vez.** Pyodide son unos 12 MB desde un CDN y
  tarda varios segundos en arrancar. Por eso queda fuera del service worker de
  la calculadora básica, que sí funciona sin conexión.
- **La multiplicación implícita tiene la misma prioridad que la explícita**, así
  que `1÷2π` es `(1÷2)·π`. Algunos modelos Casio resuelven `1÷(2π)`. Se eligió
  la regla estándar por ser más predecible; si prefieres la otra, hay que
  cambiar el nivel de `termino()` en el analizador.
- La derivada y la integral son **numéricas**, no simbólicas: dan un valor, no
  una fórmula.
