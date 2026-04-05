// COSH ERP Service Worker
const CACHE_NAME = 'cosh-erp-v3.2';
const STATIC_ASSETS = [
  '/static/css/main.css?v=20260405',
];

// ── 推播通知 ──────────────────────────────────
self.addEventListener('push', function(e) {
  const data = e.data ? e.data.json() : {};
  self.registration.showNotification(data.title || 'ERP 通知', {
    body: data.body || '',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/favicon-48x48.png',
    data: { url: data.url || '/' },
    actions: data.actions || []
  });
});

self.addEventListener('notificationclick', function(e) {
  e.notification.close();
  const url = e.notification.data.url;
  e.waitUntil(
    clients.matchAll({ type: 'window' }).then(function(clientList) {
      for (const client of clientList) {
        if (client.url.includes(url) && 'focus' in client)
          return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});

// ── 安裝：快取靜態資源 ────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// ── 啟動：清除舊版快取 ────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── 攔截請求：網路優先，失敗才用快取 ──────────
self.addEventListener('fetch', event => {
  // API 請求不快取
  if (event.request.url.includes('/api/')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // 靜態資源成功取得後更新快取
        if (response.ok && event.request.url.includes('/static/')) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
