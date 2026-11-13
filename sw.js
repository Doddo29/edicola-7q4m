/* AutYG – service worker: fa aprire l'app subito e anche senza rete.
   La pagina arriva sempre dalla rete quando c'è (così gli aggiornamenti si vedono subito);
   se la rete manca o è lenta, usa la copia salvata. data.json lo gestisce la pagina. */
const V = 'autyg-shell-v1';
const SHELL = ['./', 'manifest.webmanifest', 'icon-192.png', 'apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).catch(() => {}).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k.startsWith('autyg-shell-') && k !== V).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function netFirst(req, key, ms) {
  const cache = await caches.open(V);
  const net = fetch(req).then(r => { if (r && r.ok) cache.put(key, r.clone()); return r; });
  const cached = await cache.match(key);
  if (!cached) return net;
  const slow = new Promise(res => setTimeout(() => res(null), ms));
  try { return (await Promise.race([net, slow])) || cached; } catch (e) { return cached; }
}
async function staleWhile(req) {
  const cache = await caches.open(V);
  const cached = await cache.match(req);
  const net = fetch(req).then(r => { if (r && (r.ok || r.type === 'opaque')) cache.put(req, r.clone()); return r; }).catch(() => cached);
  return cached || net;
}

self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET') return;
  const u = new URL(r.url);
  if (r.headers.has('range')) return;
  if (u.origin === location.origin) {
    if (r.mode === 'navigate' || u.pathname.endsWith('/') || u.pathname.endsWith('index.html')) {
      e.respondWith(netFirst(r, './', 3000)); return;
    }
    if (/\.(png|webmanifest)$/.test(u.pathname)) e.respondWith(staleWhile(r));
    return;
  }
  if (u.hostname === 'fonts.googleapis.com' || u.hostname === 'fonts.gstatic.com') e.respondWith(staleWhile(r));
});
