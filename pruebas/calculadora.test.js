// Ejecutor de Node. Se lanza con `npm test` (o `node --test pruebas/`) y es lo
// que corre GitHub Actions en cada push.

const test = require('node:test');
const assert = require('node:assert/strict');

const { crearCalculadora } = require('../calculadora.js');
const { CASOS, reproducir, leer } = require('./casos.js');

for (const caso of CASOS) {
  test(caso.nombre, () => {
    const calc = crearCalculadora();
    reproducir(calc, caso.teclas);
    assert.equal(leer(calc, caso.campo), caso.esperado);
  });
}
