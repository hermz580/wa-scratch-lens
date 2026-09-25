// Offline support: app shell cache-first, game data network-first.
const SHELL = 'scratch-lens-shell-v5';
const DATA = 'scratch-lens-data';
const SHELL_FILES = ['./', 'index.html', 'app.js', 'slots.js', 'styles.css', 'manifest.webmanifest', 'icons/icon.svg', 'icons/icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== SHELL && k !== DATA).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.includes('/data/')) {
    const key = url.origin + url.pathname; // ignore cache-busting query
    e.respondWith(fetch(e.request).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(DATA).then(c => c.put(key, copy)); }
      return res;
    }).catch(() => caches.open(DATA).then(c => c.match(key)).then(hit => hit || Response.error())));
    return;
  }
  // Shell: serve cache fast, refresh it in the background.
  e.respondWith(caches.open(SHELL).then(c => c.match(e.request, {ignoreSearch: true}).then(hit => {
    const net = fetch(e.request).then(res => { if (res.ok) c.put(e.request, res.clone()); return res; }).catch(() => hit);
    return hit || net;
  })));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({type: 'window'}).then(list => list[0] ? list[0].focus() : self.clients.openWindow('./')));
});
