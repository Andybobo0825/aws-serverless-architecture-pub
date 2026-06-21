let hasReloadedForServiceWorkerUpdate = false;

export function registerAppServiceWorker(): void {
  if (!('serviceWorker' in navigator)) return;

  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (hasReloadedForServiceWorkerUpdate) return;
    hasReloadedForServiceWorkerUpdate = true;
    window.location.reload();
  });

  void navigator.serviceWorker.register('/sw.js').then((registration) => {
    if (registration.waiting) registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    registration.addEventListener('updatefound', () => {
      const installingWorker = registration.installing;
      if (!installingWorker) return;
      installingWorker.addEventListener('statechange', () => {
        if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
          installingWorker.postMessage({ type: 'SKIP_WAITING' });
        }
      });
    });
  });
}
