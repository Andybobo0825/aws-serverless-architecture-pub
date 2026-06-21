import { config } from './config';
import { getOrCreateDeviceId } from './device';

export class ApiFetchError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'ApiFetchError';
  }
}

export async function apiFetch<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    ...init,
    headers: {
      'authorization': `Bearer ${token}`,
      'content-type': 'application/json',
      'x-device-id': getOrCreateDeviceId(),
      ...(init.headers ?? {})
    }
  });
  const text = await response.text();
  const payload = parseResponsePayload(text);
  if (!response.ok) {
    const message = typeof payload.message === 'string' ? payload.message : `API failed: ${response.status}`;
    throw new ApiFetchError(message, response.status);
  }
  return payload as T;
}

function parseResponsePayload(text: string): Record<string, unknown> {
  if (!text) return {};
  try {
    const payload = JSON.parse(text);
    return payload && typeof payload === 'object' ? payload as Record<string, unknown> : {};
  } catch {
    return {};
  }
}
