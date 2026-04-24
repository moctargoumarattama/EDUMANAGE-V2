const STATIC_CACHE_NAME = "arabic-static-v12";
const RUNTIME_CACHE_NAME = "arabic-runtime-v12";
const OFFLINE_URL = "/offline";
const CACHEABLE_NAVIGATION_PATHS = [
  "/",
  OFFLINE_URL,
  "/choix-langue",
  "/courses",
  "/lecons",
  "/placement",
  "/progression",
  "/quiz",
  "/request_reset_password",
  "/reset_password"
];
const BLOCKED_NAVIGATION_PREFIXES = [
  "/admin",
  "/login",
  "/logout",
  "/maintenance",
  "/notifications",
  "/placement/admin",
  "/profile"
];
const STATIC_ASSETS = [
  "/",
  OFFLINE_URL,
  "/static/css/main.css",
  "/static/css/lesson.css",
  "/static/js/lesson.js",
  "/static/js/pwa.js",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

function isCacheableResponse(response) {
  return Boolean(response && response.ok && (response.type === "basic" || response.type === "default"));
}

function pathMatchesPrefix(pathname, prefix) {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

function isCacheableNavigationRequest(url) {
  if (BLOCKED_NAVIGATION_PREFIXES.some((prefix) => pathMatchesPrefix(url.pathname, prefix))) {
    return false;
  }

  return CACHEABLE_NAVIGATION_PATHS.some((prefix) => pathMatchesPrefix(url.pathname, prefix));
}

function shouldCacheNavigationResponse(request, url, response) {
  return (
    request.mode === "navigate"
    && isCacheableNavigationRequest(url)
    && response.headers.get("X-Cacheable-Navigation") === "1"
    && isCacheableResponse(response)
  );
}

function shouldBypass(request, url) {
  if (request.method !== "GET") {
    return true;
  }

  if (url.origin !== self.location.origin) {
    return true;
  }

  return [
    "/logout",
    "/login",
    "/notifications/",
    "/progression/stream"
  ].some((prefix) => url.pathname === prefix || url.pathname.startsWith(prefix));
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => ![STATIC_CACHE_NAME, RUNTIME_CACHE_NAME].includes(key))
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (shouldBypass(event.request, url)) {
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) {
          return cached;
        }

        return fetch(event.request)
          .then((response) => {
            if (isCacheableResponse(response)) {
              const clone = response.clone();
              caches.open(STATIC_CACHE_NAME).then((cache) => cache.put(event.request, clone).catch(() => null));
            }
            return response;
          })
          .catch(() => {
            if (event.request.destination === "image") {
              return caches.match("/static/icons/icon-192.png");
            }
            return new Response("", { status: 504, statusText: "Offline" });
          });
      })
    );
    return;
  }

  if (event.request.mode === "navigate") {
    event.respondWith(
      (async () => {
        const isCacheableNavigation = isCacheableNavigationRequest(url);

        try {
          const response = await fetch(event.request);
          if (shouldCacheNavigationResponse(event.request, url, response)) {
            const clone = response.clone();
            caches.open(RUNTIME_CACHE_NAME).then((cache) => cache.put(event.request, clone).catch(() => null));
          }
          return response;
        } catch (_) {
          if (isCacheableNavigation) {
            const cachedPage = await caches.match(event.request);
            if (cachedPage) {
              return cachedPage;
            }
          }

          const offlinePage = await caches.match(OFFLINE_URL);
          if (offlinePage) {
            return offlinePage;
          }

          return new Response("Offline", {
            status: 503,
            statusText: "Offline",
            headers: { "Content-Type": "text/plain; charset=utf-8" }
          });
        }
      })()
    );
    return;
  }

  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request).then((cached) => cached || new Response("", { status: 504, statusText: "Offline" })))
  );
});

self.addEventListener("push", (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || "LabeeB Arabic";
  const options = {
    body: data.body || "C'est l'heure de votre cours d'arabe !",
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/icon-192.png",
    vibrate: [200, 100, 200],
    data: { url: data.url || "/courses/" },
    actions: [
      { action: "open", title: "Commencer" },
      { action: "close", title: "Plus tard" }
    ]
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  if (event.action === "close") {
    return;
  }

  const url = event.notification.data?.url || "/courses/";
  event.waitUntil(clients.openWindow(url));
});
