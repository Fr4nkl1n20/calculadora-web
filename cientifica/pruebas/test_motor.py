"""Pruebas del motor científico. Se ejecutan con `python -m unittest` y son
las que corre GitHub Actions."""

import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import motor  # noqa: E402


def ev(expr, angulo='DEG'):
    """Evalúa y devuelve el texto principal, como lo vería el usuario."""
    ctx = motor.Contexto(angulo)
    return motor.formatear(motor.calcular(expr, ctx))['principal']


def num(expr, angulo='DEG'):
    """Evalúa y devuelve el valor como float, para comparaciones con tolerancia."""
    ctx = motor.Contexto(angulo)
    return motor._a_real(motor.calcular(expr, ctx))


class Aritmetica(unittest.TestCase):
    def test_operaciones_basicas(self):
        self.assertEqual(ev('2+3'), '5')
        self.assertEqual(ev('9-12'), '-3')
        self.assertEqual(ev('7*8'), '56')
        self.assertEqual(ev('84/4'), '21')

    def test_prioridad(self):
        self.assertEqual(ev('2+3*4'), '14')
        self.assertEqual(ev('(2+3)*4'), '20')
        self.assertEqual(ev('2^3^2'), '512')  # asociativa por la derecha

    def test_menos_unario_frente_a_potencia(self):
        # Como en los fx: -2^2 es -(2^2)
        self.assertEqual(ev('-2^2'), '-4')
        self.assertEqual(ev('(-2)^2'), '4')

    def test_potencia_con_exponente_negativo(self):
        self.assertEqual(ev('2^-3'), '1/8')

    def test_aritmetica_exacta_sin_errores_de_coma_flotante(self):
        self.assertEqual(ev('0.1+0.2'), '3/10')
        self.assertEqual(ev('1/3*3'), '1')
        self.assertEqual(ev('0.1+0.7'), '4/5')

    def test_division_entre_cero(self):
        with self.assertRaises(motor.ErrorCalculo):
            ev('1/0')

    def test_multiplicacion_implicita(self):
        self.assertAlmostEqual(num('2π'), 2 * math.pi)
        self.assertEqual(ev('3(4+5)'), '27')
        self.assertEqual(ev('(1+2)(3+4)'), '21')

    def test_porcentaje_contextual(self):
        self.assertEqual(ev('200+10%'), '220')
        self.assertEqual(ev('200-10%'), '180')
        self.assertEqual(ev('50%'), '1/2')


class Trigonometria(unittest.TestCase):
    def test_grados(self):
        self.assertAlmostEqual(num('sin(30)'), 0.5)
        self.assertAlmostEqual(num('cos(60)'), 0.5)
        self.assertAlmostEqual(num('tan(45)'), 1.0)

    def test_radianes(self):
        self.assertAlmostEqual(num('sin(π/6)', 'RAD'), 0.5)
        self.assertAlmostEqual(num('cos(0)', 'RAD'), 1.0)

    def test_gradianes(self):
        self.assertAlmostEqual(num('sin(100)', 'GRA'), 1.0)

    def test_inversas_devuelven_en_la_unidad_activa(self):
        self.assertAlmostEqual(num('asin(0.5)'), 30.0)
        self.assertAlmostEqual(num('asin(0.5)', 'RAD'), math.pi / 6)
        self.assertAlmostEqual(num('atan(1)'), 45.0)

    def test_hiperbolicas(self):
        self.assertAlmostEqual(num('sinh(1)'), math.sinh(1))
        self.assertAlmostEqual(num('atanh(0.5)'), math.atanh(0.5))

    def test_sufijo_de_grados_en_modo_radianes(self):
        self.assertAlmostEqual(num('sin(45°)', 'RAD'), math.sin(math.radians(45)))


class Logaritmos(unittest.TestCase):
    def test_log_y_ln(self):
        self.assertAlmostEqual(num('log(1000)'), 3.0)
        self.assertAlmostEqual(num('ln(e)'), 1.0)
        self.assertAlmostEqual(num('log2(1024)'), 10.0)
        self.assertAlmostEqual(num('logab(3,81)'), 4.0)

    def test_exponencial(self):
        self.assertAlmostEqual(num('exp(1)'), math.e)


class Raices(unittest.TestCase):
    def test_raiz_exacta(self):
        self.assertEqual(ev('√9'), '3')
        self.assertEqual(ev('sqrt(16)'), '4')

    def test_raiz_de_negativo_da_complejo(self):
        self.assertEqual(ev('√-4'), '2i')

    def test_raiz_cubica_y_enesima(self):
        self.assertAlmostEqual(num('cbrt(27)'), 3.0)
        self.assertAlmostEqual(num('cbrt(-8)'), -2.0)
        self.assertAlmostEqual(num('root(4,16)'), 2.0)

    def test_raiz_afecta_solo_a_lo_que_sigue(self):
        self.assertEqual(ev('√9+1'), '4')


class Combinatoria(unittest.TestCase):
    def test_factorial(self):
        self.assertEqual(ev('5!'), '120')
        self.assertEqual(ev('0!'), '1')

    def test_factorial_de_negativo(self):
        with self.assertRaises(motor.ErrorCalculo):
            ev('(-1)!')

    def test_combinaciones_y_permutaciones(self):
        self.assertEqual(ev('nCr(5,2)'), '10')
        self.assertEqual(ev('nPr(5,2)'), '20')

    def test_mcd_y_mcm(self):
        self.assertEqual(ev('gcd(12,18)'), '6')
        self.assertEqual(ev('lcm(4,6)'), '12')


class Complejos(unittest.TestCase):
    def test_unidad_imaginaria(self):
        self.assertEqual(ev('i^2'), '-1')

    def test_suma_de_complejos(self):
        self.assertEqual(ev('(3+4i)+(1-2i)'), '4 + 2i')

    def test_partes(self):
        self.assertAlmostEqual(num('re(3+4i)'), 3.0)
        self.assertAlmostEqual(num('im(3+4i)'), 4.0)
        self.assertAlmostEqual(num('abs(3+4i)'), 5.0)


class Variables(unittest.TestCase):
    def test_variables_y_ans(self):
        ctx = motor.Contexto('DEG', {'A': 7, 'Ans': 3})
        self.assertEqual(motor.formatear(motor.calcular('A*2', ctx))['principal'], '14')
        self.assertEqual(motor.formatear(motor.calcular('Ans+1', ctx))['principal'], '4')

    def test_variable_desconocida(self):
        with self.assertRaises(motor.ErrorCalculo):
            ev('Z+1')


class Formato(unittest.TestCase):
    def test_fraccion_y_decimal(self):
        r = motor.formatear(motor.calcular('1/4', motor.Contexto()))
        self.assertEqual(r['principal'], '1/4')
        self.assertEqual(r['alterno'], '0.25')
        self.assertTrue(r['exacto'])

    def test_notacion_cientifica_automatica_en_decimales(self):
        self.assertIn('×10^', motor.formatear(1.5e-12)['principal'])
        self.assertIn('×10^', motor.formatear(1.2e15)['principal'])

    def test_los_enteros_exactos_no_pasan_a_cientifica(self):
        # 1/0.0000000001 es exactamente 10^10: mostrarlo entero es lo correcto,
        # la notación científica se reserva para los valores aproximados.
        self.assertEqual(ev('1/0.0000000001'), '10000000000')

    def test_modo_ingenieria(self):
        r = motor.formatear(15000.0, 'ENG')
        self.assertEqual(r['principal'], '15×10^3')

    def test_modo_fijo(self):
        r = motor.formatear(math.pi, 'FIX', 3)
        self.assertEqual(r['principal'], '3.142')


class Estadistica(unittest.TestCase):
    def test_una_variable(self):
        r = motor.estadistica_1var([2, 4, 4, 4, 5, 5, 7, 9])
        self.assertEqual(r['n'], 8)
        self.assertAlmostEqual(r['x̄'], 5.0)
        self.assertAlmostEqual(r['σx (población)'], 2.0)
        self.assertAlmostEqual(r['mediana'], 4.5)

    def test_regresion_lineal(self):
        r = motor.estadistica_2var([[1, 2], [2, 4], [3, 6], [4, 8]])
        self.assertAlmostEqual(r['B (pendiente)'], 2.0)
        self.assertAlmostEqual(r['A (ordenada)'], 0.0)
        self.assertAlmostEqual(r['r (correlación)'], 1.0)

    def test_regresion_exponencial(self):
        datos = [[x, 3 * math.exp(0.5 * x)] for x in range(1, 6)]
        r = motor.estadistica_2var(datos, 'exponencial')
        self.assertAlmostEqual(r['B (pendiente)'], 0.5, places=6)


class Ecuaciones(unittest.TestCase):
    def test_cuadratica(self):
        raices = motor.raices_polinomio([1, -3, 2])
        valores = sorted(z.real for z in raices)
        self.assertAlmostEqual(valores[0], 1.0)
        self.assertAlmostEqual(valores[1], 2.0)

    def test_cuadratica_sin_raices_reales(self):
        raices = motor.raices_polinomio([1, 0, 1])
        self.assertAlmostEqual(abs(raices[0].imag), 1.0)

    def test_cubica(self):
        # (x-1)(x-2)(x-3) = x³ - 6x² + 11x - 6
        raices = sorted(z.real for z in motor.raices_polinomio([1, -6, 11, -6]))
        for esperado, obtenido in zip([1.0, 2.0, 3.0], raices):
            self.assertAlmostEqual(obtenido, esperado, places=6)

    def test_sistema_2x2(self):
        x = motor.resolver_sistema([[2, 1, 5], [1, -1, 1]])
        self.assertAlmostEqual(x[0], 2.0)
        self.assertAlmostEqual(x[1], 1.0)

    def test_sistema_3x3(self):
        x = motor.resolver_sistema([[1, 1, 1, 6], [0, 2, 5, -4], [2, 5, -1, 27]])
        for esperado, obtenido in zip([5.0, 3.0, -2.0], x):
            self.assertAlmostEqual(obtenido, esperado, places=9)

    def test_sistema_sin_solucion_unica(self):
        with self.assertRaises(motor.ErrorCalculo):
            motor.resolver_sistema([[1, 1, 2], [2, 2, 4]])

    def test_resolver_expresion(self):
        r = motor.resolver_expresion('X^2-9', motor.Contexto(), 1)
        self.assertAlmostEqual(abs(r), 3.0, places=6)


class Calculo(unittest.TestCase):
    def test_derivada(self):
        d = motor.derivada('X^3', 2, motor.Contexto())
        self.assertAlmostEqual(d, 12.0, places=5)

    def test_derivada_de_seno(self):
        d = motor.derivada('sin(X)', 0, motor.Contexto('RAD'))
        self.assertAlmostEqual(d, 1.0, places=6)

    def test_integral(self):
        v = motor.integral('X^2', 0, 3, motor.Contexto())
        self.assertAlmostEqual(v, 9.0, places=6)

    def test_integral_invertida_cambia_de_signo(self):
        v = motor.integral('X^2', 3, 0, motor.Contexto())
        self.assertAlmostEqual(v, -9.0, places=6)

    def test_tabla(self):
        filas = motor.tabla('X^2', 1, 4, 1, motor.Contexto())
        self.assertEqual([f['y'] for f in filas], ['1', '4', '9', '16'])


class BaseN(unittest.TestCase):
    def test_conversiones(self):
        self.assertEqual(motor.convertir_base('255', 10, 16), 'FF')
        self.assertEqual(motor.convertir_base('FF', 16, 2), '11111111')
        self.assertEqual(motor.convertir_base('1010', 2, 10), '10')

    def test_base_invalida(self):
        with self.assertRaises(motor.ErrorCalculo):
            motor.convertir_base('2', 2, 10)

    def test_operaciones_logicas(self):
        self.assertEqual(motor.logica('and', 0b1100, 0b1010)['dec'], 0b1000)
        self.assertEqual(motor.logica('or', 0b1100, 0b1010)['dec'], 0b1110)
        self.assertEqual(motor.logica('xor', 0b1100, 0b1010)['dec'], 0b0110)
        self.assertEqual(motor.logica('not', 0)['dec'], -1)


class TeoriaDeNumeros(unittest.TestCase):
    def test_factorizacion(self):
        r = motor.factorizar(360)
        self.assertEqual(r['expresion'], '2^3 × 3^2 × 5')
        self.assertEqual(r['numero_de_divisores'], 24)
        self.assertFalse(r['es_primo'])

    def test_primo(self):
        self.assertTrue(motor.factorizar(97)['es_primo'])

    def test_numero_demasiado_pequeno(self):
        with self.assertRaises(motor.ErrorCalculo):
            motor.factorizar(1)


class Unidades(unittest.TestCase):
    def test_longitud(self):
        self.assertAlmostEqual(motor.convertir_unidad(1, 'km', 'm'), 1000.0)
        self.assertAlmostEqual(motor.convertir_unidad(1, 'in', 'cm'), 2.54)

    def test_temperatura(self):
        self.assertAlmostEqual(motor.convertir_unidad(100, 'C', 'F'), 212.0)
        self.assertAlmostEqual(motor.convertir_unidad(0, 'C', 'K'), 273.15)

    def test_unidad_desconocida(self):
        with self.assertRaises(motor.ErrorCalculo):
            motor.convertir_unidad(1, 'km', 'kg')


class Errores(unittest.TestCase):
    def test_parentesis_sin_cerrar(self):
        with self.assertRaises(motor.ErrorCalculo):
            ev('(1+2')

    def test_expresion_vacia(self):
        with self.assertRaises(motor.ErrorCalculo):
            ev('')

    def test_funcion_desconocida(self):
        with self.assertRaises(motor.ErrorCalculo):
            ev('inventada(2)')

    def test_argumentos_de_mas(self):
        with self.assertRaises(motor.ErrorCalculo):
            ev('sin(1,2)')

    def test_caracter_no_reconocido(self):
        with self.assertRaises(motor.ErrorCalculo):
            ev('2 & 3')


class InterfazJSON(unittest.TestCase):
    """La capa que consume JavaScript: nunca debe lanzar, siempre JSON."""

    def setUp(self):
        motor.SESION = motor.Sesion()

    def test_evaluar(self):
        r = json.loads(motor.ejecutar(json.dumps({'cmd': 'evaluar', 'expr': '2+3'})))
        self.assertTrue(r['ok'])
        self.assertEqual(r['principal'], '5')

    def test_error_no_lanza_excepcion(self):
        r = json.loads(motor.ejecutar(json.dumps({'cmd': 'evaluar', 'expr': '1/0'})))
        self.assertFalse(r['ok'])
        self.assertIn('cero', r['error'])

    def test_peticion_mal_formada(self):
        r = json.loads(motor.ejecutar('esto no es json'))
        self.assertFalse(r['ok'])

    def test_orden_desconocida(self):
        r = json.loads(motor.ejecutar(json.dumps({'cmd': 'volar'})))
        self.assertFalse(r['ok'])

    def test_ans_se_guarda_entre_llamadas(self):
        motor.ejecutar(json.dumps({'cmd': 'evaluar', 'expr': '2+3'}))
        r = json.loads(motor.ejecutar(json.dumps({'cmd': 'evaluar', 'expr': 'Ans*2'})))
        self.assertEqual(r['principal'], '10')

    def test_configurar_modo_angular(self):
        motor.ejecutar(json.dumps({'cmd': 'configurar', 'angulo': 'RAD'}))
        r = json.loads(motor.ejecutar(json.dumps({'cmd': 'evaluar', 'expr': 'sin(π/2)'})))
        self.assertEqual(r['principal'], '1')

    def test_guardar_variable(self):
        motor.ejecutar(json.dumps({'cmd': 'guardar_variable', 'nombre': 'A', 'expr': '7'}))
        r = json.loads(motor.ejecutar(json.dumps({'cmd': 'evaluar', 'expr': 'A^2'})))
        self.assertEqual(r['principal'], '49')

    def test_historial(self):
        motor.ejecutar(json.dumps({'cmd': 'evaluar', 'expr': '1+1'}))
        r = json.loads(motor.ejecutar(json.dumps({'cmd': 'evaluar', 'expr': '2+2'})))
        self.assertEqual(len(r['historial']), 2)
        self.assertEqual(r['historial'][0]['expr'], '2+2')

    def test_infinito_no_rompe_el_json(self):
        r = json.loads(motor.ejecutar(json.dumps(
            {'cmd': 'estadistica', 'tipo': '1var', 'datos': [5]})))
        self.assertTrue(r['ok'])
        self.assertIsNone(r['resultados']['sx (muestra)'])

    def test_polinomio(self):
        r = json.loads(motor.ejecutar(json.dumps(
            {'cmd': 'polinomio', 'coeficientes': [1, -3, 2]})))
        self.assertTrue(r['ok'])
        self.assertEqual(sorted(r['raices']), ['1', '2'])

    def test_factorizar_por_json(self):
        r = json.loads(motor.ejecutar(json.dumps({'cmd': 'factorizar', 'n': 100})))
        self.assertEqual(r['resultado']['expresion'], '2^2 × 5^2')


if __name__ == '__main__':
    unittest.main()
