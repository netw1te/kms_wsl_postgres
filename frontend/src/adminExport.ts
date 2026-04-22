import type { Credentials } from './types'
import { buildAuthHeader } from './api'

export async function exportAllDatabases(credentials: Credentials): Promise<Blob> {
  const response = await fetch('/admin/export/all', {
    headers: { 'Authorization': buildAuthHeader(credentials) },
    credentials: 'include'
  })
  if (!response.ok) throw new Error('Ошибка экспорта')
  return response.blob()
}

export async function exportKmsDatabases(credentials: Credentials): Promise<Blob> {
  const response = await fetch('/admin/export/kms', {
    headers: { 'Authorization': buildAuthHeader(credentials) },
    credentials: 'include'
  })
  if (!response.ok) throw new Error('Ошибка экспорта')
  return response.blob()
}

export async function exportUserDatabase(credentials: Credentials, login: string): Promise<Blob> {
  const response = await fetch(`/admin/export/user/${encodeURIComponent(login)}`, {
    headers: { 'Authorization': buildAuthHeader(credentials) },
    credentials: 'include'
  })
  if (!response.ok) throw new Error('Ошибка экспорта')
  return response.blob()
}