// service-worker.js — Mini ERP PWA
const CACHE = 'mini-erp-v2';

// Recursos del shell de la app que se cachean al instalar
const SHELL = [
  '/',
  '/manifest.json',
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

// Estrategia: Network First para la API, Cache First para el shell
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Peticiones a la API → siempre red (datos en tiempo real)
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({ detail: 'Sin conexión. Verifica tu red.' }),
          { status: 503, headers: { 'Content-Type': 'application/json' } })
      )
    );
    return;
  }

  // Shell de la app → cache first, fallback a red
  e.respondWith(
    caches.match(e.request).then(cached =>
      cached || fetch(e.request).then(response => {
        const clone = response.clone();
        caches.open(CACHE).then(cache => cache.put(e.request, clone));
        return response;
      })
    )
  );
});
