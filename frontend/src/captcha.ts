export async function getCaptcha(): Promise<string> {
  const response = await fetch('/captcha/image', {
    credentials: 'include',
    cache: 'no-store',
  })

  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

export async function verifyCaptcha(
  code: string
): Promise<{ ok: boolean; error?: string }> {
  const response = await fetch('/captcha/check', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    credentials: 'include',
    body: new URLSearchParams({ code }),
  })

  return response.json()
}

export function refreshCaptcha(): Promise<string> {
  return getCaptcha()
}