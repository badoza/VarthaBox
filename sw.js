// This is the service worker that makes the app installable
self.addEventListener('install', (e) => {
    console.log('[VarthaBox] Service Worker Installed');
});

// We need a fetch event listener to satisfy Chrome's PWA requirements
self.addEventListener('fetch', (e) => {
    // Just pass the request through normally
});
