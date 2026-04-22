let currentSessionId: string | null = null

export async function getCaptcha(): Promise<string> {
  const response = await fetch('/captcha/image', {
    credentials: 'include'
  })
  const sessionId = response.headers.get('set-cookie')
  if (sessionId) {
    const match = sessionId.match(/captcha_id=([^;]+)/)
    if (match) currentSessionId = match[1]
  }
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

export async function verifyCaptcha(code: string): Promise<{ ok: boolean; error?: string }> {
  if (!currentSessionId) {
    return { ok: false, error: 'Сессия капчи не найдена' }
  }
  const response = await fetch('/captcha/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    credentials: 'include',
    body: new URLSearchParams({ session_id: currentSessionId, code })
  })
  return response.json()
}

export function refreshCaptcha(): Promise<string> {
  return getCaptcha()
}