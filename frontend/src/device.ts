const KEY = 'magic-device-id';

export function getOrCreateDeviceId(): string {
  const existing = localStorage.getItem(KEY);
  if (existing) return existing;
  const created = crypto.randomUUID();
  localStorage.setItem(KEY, created);
  return created;
}
