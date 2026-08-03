// Ejecutor de Node. Se lanza con `npm test` y es lo que corre GitHub Actions
// en cada push.
//
// package.json apunta a este archivo por su ruta exacta, no con un patrón:
// los comodines en `node --test` sólo existen desde Node 22, y el shell de
// Windows tampoco los expande. Si añades otro archivo de pruebas, agrégalo
// también al script "test".

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
