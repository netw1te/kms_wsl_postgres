import type { Credentials } from './types'
import { buildAuthHeader } from './api'

async function exportBlob(url: string, credentials: Credentials): Promise<Blob> {
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Authorization: buildAuthHeader(credentials),
    },
    credentials: 'include',
  })

  const blob = await response.blob()
  const contentType = response.headers.get('content-type') ?? ''

  if (!response.ok) {
    const text = await blob.text()
    throw new Error(text || `Ошибка экспорта: HTTP ${response.status}`)
  }

  if (!contentType.includes('application/zip')) {
    const text = await blob.text()
    throw new Error(
      `Сервер вернул не ZIP, а ${contentType || 'неизвестный тип'}: ${text.slice(0, 300)}`
    )
  }

  if (blob.size === 0) {
    throw new Error('Сервер вернул пустой файл экспорта')
  }

  return blob
}

export function exportAllDatabases(credentials: Credentials): Promise<Blob> {
  return exportBlob('/api/admin/export/all', credentials)
}

export function exportKmsDatabases(credentials: Credentials): Promise<Blob> {
  return exportBlob('/api/admin/export/kms', credentials)
}

export function exportUserDatabase(
  credentials: Credentials,
  login: string
): Promise<Blob> {
  return exportBlob(`/api/admin/export/user/${encodeURIComponent(login)}`, credentials)
}

export type ImportDatabaseResult = {
  users: number
  tags: number
  info_objects: number
  tag_links: number
  user_agreements: number
  search_queries: number
  deletion_requests: number
  media_files: number
  attachments: number
}

export async function importDatabaseZip(
  credentials: Credentials,
  file: File
): Promise<ImportDatabaseResult> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch('/api/admin/import/zip', {
    method: 'POST',
    headers: {
      Authorization: buildAuthHeader(credentials),
    },
    credentials: 'include',
    body: formData,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Ошибка импорта: HTTP ${response.status}`)
  }

  return response.json()
}