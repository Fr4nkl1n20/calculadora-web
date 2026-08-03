// Service worker: guarda la aplicación en caché para que funcione sin conexión.
//
// Al cambiar cualquier archivo hay que subir VERSION, si no los navegadores
// seguirán sirviendo la copia antigua desde la caché.
const VERSION = 'calculadora-v1';

const RECURSOS = [
  './',
  './index.html',
  './styles.css',
  './calculadora.js',
  './app.js',
  './manifest.webmanifest',
  './assets/escena.svg',
  './assets/bate-h.svg',
  './assets/bate-v.svg',
  './assets/icono.svg',
  './assets/icono-192.png',
  './assets/icono-512.png',
];

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches.open(VERSION)
      .then((cache) => cache.addAll(RECURSOS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(
        claves.filter((c) => c !== VERSION).map((c) => caches.delete(c))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (evento) => {
  const peticion = evento.request;
  if (peticion.method !== 'GET') return;

  evento.respondWith(
    caches.match(peticion).then((enCache) => {
      if (enCache) return enCache;

      return fetch(peticion)
        .then((respuesta) => {
          // Guarda lo que se descargue con éxito para la próxima vez.
          if (respuesta.ok && new URL(peticion.url).origin === self.location.origin) {
            const copia = respuesta.clone();
            caches.open(VERSION).then((cache) => cache.put(peticion, copia));
          }
          return respuesta;
        })
        .catch(() => {
          // Sin red: para una navegación devolvemos la página principal.
          if (peticion.mode === 'navigate') return caches.match('./index.html');
          return Response.error();
        });
    })
  );
});
