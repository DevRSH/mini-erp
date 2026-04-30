// service-worker.js — Fika PWA
const CACHE = 'fika-v5'; // Incrementar versión para forzar actualización

// Recursos del shell de la app que se cachean al instalar
const SHELL = [
  '/',
  '/manifest.json',
  '/css/styles.css',
  '/js/globals.js',
  '/js/scanner.js',
  '/js/main.js'
];

// Al instalar: cachear el shell
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(SHELL))
  );
  self.skipWaiting();
});

// Al activar: limpiar caches viejos
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Estrategia: Network First para todo (prioriza frescura)
// Si falla la red, intenta buscar en el cache.
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Ignorar peticiones que no sean GET
  if (e.request.method !== 'GET') return;

  // Estrategia: Network First
  e.respondWith(
    fetch(e.request)
      .then(response => {
        // Si la respuesta es válida, clonarla y guardarla en el cache
        if (response.ok && !url.pathname.startsWith('/api/')) {
          const clone = response.clone();
          caches.open(CACHE).then(cache => cache.put(e.request, clone));
        }
        return response;
      })
      .catch(() => {
        // Si falla la red, intentar buscar en el cache
        return caches.match(e.request).then(cached => {
          if (cached) return cached;
          // Si no está en cache y es la API, error JSON
          if (url.pathname.startsWith('/api/')) {
            return new Response(JSON.stringify({ detail: 'Sin conexión' }), {
              status: 503,
              headers: { 'Content-Type': 'application/json' }
            });
          }
          // Si no está en cache y es una página, etc...
        });
      })
  );
});
