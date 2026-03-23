// This minimal service worker is required for PWA installation functionality
self.addEventListener('install', (e) => {
    console.log('[Service Worker] Installed');
});

self.addEventListener('fetch', (e) => {
    // Just pass through, no complex caching needed for free tier
});
