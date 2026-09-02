/* Even Match service worker.
   Netwerk eerst, en alleen voor eigen bestanden de cache als terugval, zodat de
   site na één bezoek ook zonder netwerk opent. De versie komt mee in de
   registratie-URL (sw.js?v=...), dus APP_VERSION in app.js is de enige bron:
   een nieuwe versie is een nieuwe cache en de oude gaat weg bij activeren. */
"use strict";

const VERSION = new URL(self.location.href).searchParams.get("v") || "dev";
const CACHE = "evenmatch-" + VERSION;
const PRECACHE = [
  "./", "index.html", "app.js", "manifest.json",
  "icon-192.png", "icon-512.png", "apple-touch-icon.png", "favicon.svg",
  "fonts/archivo-400.woff2", "fonts/archivo-900.woff2",
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  e.respondWith((async () => {
    try {
      const resp = await fetch(req);
      if (resp.ok) (await caches.open(CACHE)).put(req, resp.clone());
      return resp;
    } catch (err) {
      const hit = await caches.match(req, { ignoreSearch: true });
      if (hit) return hit;
      if (req.mode === "navigate") {
        const index = await caches.match("index.html");
        if (index) return index;
      }
      throw err;
    }
  })());
});
