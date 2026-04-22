import type { Credentials } from './types'

export const API_BASE = '/api'
export const STORAGE_KEY = 'suz_frontend_credentials'

export function buildAuthHeader(credentials: Credentials) {
  return `Basic ${btoa(`${credentials.login}:${credentials.password}`)}`
}

export async function apiFetch<T>(
  path: string,
  credentials: Credentials,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {})
  headers.set('Authorization', buildAuthHeader(credentials))

  if (!(options.body instanceof FormData) && !headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function parseTags(raw: string): string[] {
  return raw
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export async function apiFetchBlob(
  path: string,
  credentials: Credentials,
  options: RequestInit = {}
): Promise<Blob> {
  const headers = new Headers(options.headers || {})
  headers.set('Authorization', buildAuthHeader(credentials))

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }

  return response.blob()
}