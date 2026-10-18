// Firebase anonymous identities are isolated by UID and verified by the backend.
const localToken = (import.meta as unknown as {env: Record<string, string>}).env.VITE_LOCAL_ACCESS_TOKEN || ''
let config: Promise<{cloud: boolean; firebase_api_key: string}> | undefined
let pending: Promise<string> | undefined
let current = ''
let expires = 0

async function sessionToken(): Promise<string> {
  config ||= fetch('/config').then(async r => {
    if (!r.ok || !r.headers.get('content-type')?.includes('application/json')) {
      if (localToken) return {cloud:false, firebase_api_key:''}
      throw new Error('Demo configuration is unavailable.')
    }
    return r.json()
  })
  const settings = await config
  if (!settings.cloud) return localToken
  if (current && Date.now() < expires) return current
  const key = encodeURIComponent(settings.firebase_api_key)
  let refresh = localStorage.getItem('dose-timer-firebase-refresh')
  let response: Response | undefined
  if (refresh) {
    response = await fetch(`https://securetoken.googleapis.com/v1/token?key=${key}`, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:new URLSearchParams({grant_type:'refresh_token', refresh_token:refresh})})
    if (!response.ok) {localStorage.removeItem('dose-timer-firebase-refresh'); refresh = null}
  }
  if (!refresh) response = await fetch(`https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=${key}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({returnSecureToken:true})})
  if (!response?.ok) throw new Error('Demo sign-in failed. Please check cloud authentication configuration.')
  const result = await response.json()
  current = result.idToken || result.id_token
  localStorage.setItem('dose-timer-firebase-refresh', result.refreshToken || result.refresh_token)
  expires = Date.now() + (Number(result.expiresIn || result.expires_in) - 60) * 1000
  if (!current) throw new Error('Demo sign-in did not return a session.')
  return current
}

export async function authHeaders() {
  pending ||= sessionToken().finally(() => {pending = undefined})
  return {Authorization:`Bearer ${await pending}`}
}
