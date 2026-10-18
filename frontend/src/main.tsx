import { StrictMode, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import { authHeaders } from './cloudAuth'

type Kind = 'medication' | 'supplement'
type Document = { id: string; kind: Kind; created_at: string }
type Item = { name: string | null; strength: string | null; dose: string | null; instruction: string | null }
type Draft = { request_key: string; name: string; strength: string; dose: string; instruction: string; times: string[]; start_date: string; end_date: string; checked: boolean }
type Attempt = { id: string; status: string; source: string; result?: { items: Item[]; warnings: string[] }; error?: string }
type Routine = Draft & { id: string; kind: Kind; active: boolean; provenance: string }
type Occurrence = { id: string; routine_id: string; name: string; kind: Kind; dose: string; time: string; due: string; status: 'due' | 'upcoming' | 'taken' }
type State = { now: string; real_now: string; timezone: string; demo_enabled: boolean; mode: string; documents: Document[]; routines: Routine[]; occurrences: Occurrence[] }
async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, { ...init, headers: { ...await authHeaders(), ...(init.body instanceof FormData ? {} : {'Content-Type': 'application/json'}), ...init.headers } })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(typeof payload.detail === 'string' ? payload.detail : `Request failed (${response.status}). Check the fields and try again.`)
  }
  return response.json()
}
const localDate = (value: string) => new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date(value))
const clock = (value: string) => new Intl.DateTimeFormat('en-GB', {timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false}).format(new Date(value))
function blank(now: string, item?: Item): Draft {
  return {request_key: crypto.randomUUID(), name: item?.name || '', strength: item?.strength || '', dose: item?.dose || '', instruction: item?.instruction || '', times: [''], start_date: localDate(now), end_date: localDate(now), checked: false}
}

function App() {
  const [state, setState] = useState<State>()
  const [tab, setTab] = useState<'today' | 'add' | 'routines'>('today')
  const [kind, setKind] = useState<Kind>('medication')
  const [document, setDocument] = useState<Document>()
  const [attempt, setAttempt] = useState<Attempt>()
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [image, setImage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [notifications, setNotifications] = useState(typeof Notification !== 'undefined' ? Notification.permission : 'unsupported')
  const fileInput = useRef<HTMLInputElement>(null)
  const loaded = useRef(false)
  const refresh = async () => { const data = await api<State>('/state'); setState(data); loaded.current = true; return data }
  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setError(''); setNotice('')
    try { await fn() } catch (e) { setError(e instanceof Error ? e.message : 'Something went wrong.') } finally { setBusy(false) }
  }
  useEffect(() => {
    let active = true
    const poll = async () => {
      try { const data = await api<State>('/state'); if (active) {setState(data); loaded.current = true} }
      catch (e) { if (active) { setError(e instanceof Error ? e.message : 'Cannot reach the demo server. Refresh and try again.'); if (loaded.current) setState(undefined) } }
    }
    void poll(); const timer = setInterval(() => void poll(), 3000)
    return () => { active = false; clearInterval(timer) }
  }, [])
  useEffect(() => () => { if (image) URL.revokeObjectURL(image) }, [image])
  useEffect(() => {
    if (notifications !== 'granted' || !state) return
    for (const occurrence of state.occurrences.filter(v => v.status === 'due')) {
      const key = `dose-timer-notified:${occurrence.id}`
      if (!sessionStorage.getItem(key)) {
        try {
          new Notification('Dose Timer reminder', { body: `${occurrence.time} · ${occurrence.name} · ${occurrence.dose}`, tag: occurrence.id })
          sessionStorage.setItem(key, 'yes')
        } catch { setNotifications('unsupported') }
      }
    }
  }, [state, notifications])
  const read = async (doc: Document) => {
    setAttempt(undefined)
    setDrafts([blank(state?.now || new Date().toISOString())])
    const result = await api<Attempt>(`/documents/${doc.id}/extract`, {method: 'POST'})
    setAttempt(result)
    setDrafts(result.result?.items.length ? result.result.items.map(item => blank(state?.now || new Date().toISOString(), item)) : [blank(state?.now || new Date().toISOString())])
  }
  const upload = (file: File, selectedKind = kind) => run(async () => {
    setTab('add'); setDocument(undefined); setDrafts([]); setAttempt(undefined); setImage('')
    const data = new FormData(); data.append('file', file)
    const doc = await api<Document>(`/documents?kind=${selectedKind}`, {method: 'POST', body: data})
    setKind(selectedKind); setDocument(doc); setImage(URL.createObjectURL(file))
    await refresh(); await read(doc)
  })
  const sample = (selectedKind: Kind) => run(async () => {
    const response = await fetch(`/samples/${selectedKind}.png`)
    if (!response.ok) throw new Error('Sample image is unavailable.')
    const file = new File([await response.blob()], `${selectedKind}.png`, {type: 'image/png'})
    // Keep upload and reading inside the same busy lifecycle.
    setTab('add'); setKind(selectedKind); setDocument(undefined); setDrafts([]); setAttempt(undefined); setImage('')
    const form = new FormData(); form.append('file', file)
    const doc = await api<Document>(`/documents?kind=${selectedKind}`, {method: 'POST', body: form})
    setDocument(doc); setImage(URL.createObjectURL(file)); await refresh(); await read(doc)
  })
  const resume = (doc: Document) => run(async () => {
    setTab('add'); setKind(doc.kind); setDocument(doc); setAttempt(undefined); setDrafts([]); setImage('')
    const response = await fetch(`/api/documents/${doc.id}/image`, {headers: await authHeaders()})
    if (!response.ok) throw new Error('Cannot load the saved image.')
    setImage(URL.createObjectURL(await response.blob()))
    const results = await api<Attempt[]>(`/documents/${doc.id}/attempts`)
    const latest = results.at(-1)
    setAttempt(latest?.status === 'unverified' ? latest : undefined)
    setDrafts(latest?.result?.items.length ? latest.result.items.map(item => blank(state?.now || new Date().toISOString(), item)) : [blank(state?.now || new Date().toISOString())])
  })
  const change = (index: number, patch: Partial<Draft>) => setDrafts(values => values.map((value, i) => i === index ? {...value, ...patch} : value))
  const confirm = (index: number) => run(async () => {
    if (!document) return
    const {checked, ...draft} = drafts[index]
    if (!checked) throw new Error('Review the source and confirm the details first.')
    await api('/routines', {method: 'POST', body: JSON.stringify({...draft, kind: document.kind, document_id: document.id, attempt_id: attempt?.id || null, confirmed: true})})
    await refresh(); setDrafts(values => values.filter((_, i) => i !== index)); setNotice('Confirmed. Your daily reminders are now active.')
  })
  const due = state?.occurrences.filter(v => v.status === 'due') || []
  const done = state?.occurrences.filter(v => v.status === 'taken').length || 0
  const next = state?.occurrences.find(v => v.status === 'upcoming')
  const syntheticClock = state && Math.abs(new Date(state.now).getTime() - new Date(state.real_now).getTime()) > 5000
  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">◷</span><div>Dose Timer<small>A little less to remember.</small></div></div>
      <nav aria-label="Main navigation">
        <button className={tab === 'today' ? 'selected' : ''} onClick={() => setTab('today')}><span aria-hidden="true">◷</span><span>Today</span></button>
        <button className={tab === 'add' ? 'selected' : ''} onClick={() => setTab('add')}><span aria-hidden="true">＋</span><span>Add from a photo</span></button>
        <button className={tab === 'routines' ? 'selected' : ''} onClick={() => setTab('routines')}><span aria-hidden="true">☷</span><span>My routines</span></button>
      </nav>
      <div className="sidebar-note"><strong>Synthetic data only</strong><p>A hackathon prototype. Use fictional labels and medication guides.</p></div>
    </aside>
    <main>
      <header><span className="eyebrow">YOUR DAILY ROUTINE</span><div className="status-chip">{state?.mode === 'gemini' ? 'Gemini image reading' : 'Sample mode · simulated reading'}</div></header>
      {error && <div role="alert" className="alert error">{error}</div>}
      {notice && <div role="status" className="alert success">{notice}</div>}
      {busy && <div role="status" className="working">Working… Please keep this page open.</div>}
      {tab === 'today' && <>
        <div className="page-heading"><div><h1>One day. One clear plan.</h1><p>Your medication and supplement reminders, together.</p></div><button disabled={busy} onClick={() => setTab('add')}><span aria-hidden="true">＋ </span>Add a photo</button></div>
        <section className="hero"><div><span className="eyebrow">{syntheticClock ? 'DEMO TIME' : 'CURRENT TIME'} · SEOUL</span><div className="large-clock">{state ? clock(state.now) : '—'}</div><p>{state ? localDate(state.now) : 'Connecting…'} · Asia/Seoul</p></div><div className="hero-summary"><strong>{done}<span> / {state?.occurrences.length || 0}</span></strong><p>reported taken today</p></div></section>
        {due.length > 0 && <section className="due-banner" aria-label="Due reminders"><strong>It’s time to check your routine.</strong><p>{due.length} reminder{due.length === 1 ? '' : 's'} due. Follow your confirmed instructions.</p></section>}
        <section className="card"><div className="section-heading"><h2>Today’s timeline</h2><span className="muted">{state?.routines.filter(v => v.active).length || 0} active routines</span></div>
          {!state?.occurrences.length && <div className="empty"><span>◷</span><h3>Your day starts here.</h3><p>Add a medication guide or supplement label, then confirm your times.</p><button className="secondary" onClick={() => setTab('add')}>Add your first photo</button></div>}
          {state?.occurrences.map(v => <article className={`timeline-row ${v.status}`} key={v.id}><time>{v.time}</time><div className="timeline-dot"/><div className="timeline-info"><span className="kind">{v.kind}</span><h3>{v.name}</h3><p>{v.dose}</p></div><div className="timeline-action"><span className={`badge ${v.status}`}>{v.status === 'taken' ? 'Reported taken' : v.status === 'due' ? 'Reminder due' : 'Upcoming'}</span>{v.status === 'due' && <button disabled={busy} onClick={() => void run(async () => {await api(`/occurrences/${encodeURIComponent(v.id)}/taken`, {method: 'POST'}); await refresh(); setNotice('Reported taken. This is your own record, not a medical verification.')})}>Mark as taken</button>}</div></article>)}
        </section>
        <section className="card settings"><div><h2>Reminder settings</h2><p>In-app reminders work while this page is open. Browser alerts are optional; delivery can be delayed in the background. Closed-page alarms are not supported.</p></div><button className="secondary" disabled={notifications === 'unsupported' || notifications === 'granted' || notifications === 'denied'} onClick={() => void Notification.requestPermission().then(setNotifications).catch(() => setNotifications('unsupported'))}>{notifications === 'granted' ? 'Browser alerts enabled' : notifications === 'denied' ? 'Browser alerts blocked' : notifications === 'unsupported' ? 'In-app reminders only' : 'Enable browser alerts'}</button></section>
        {state?.demo_enabled && <section className="demo-controls"><strong>Recording controls</strong><span>{syntheticClock ? `Demo clock active · real time ${clock(state.real_now)}` : 'Real time is active'}</span><button className="secondary" disabled={busy || !next} onClick={() => void run(async () => {if(next) {await api('/demo/clock', {method: 'PUT', body: JSON.stringify({at: next.due})}); await refresh()}})}>Jump to next reminder</button><button className="text-button" disabled={busy || !syntheticClock} onClick={() => void run(async () => {await api('/demo/clock', {method: 'DELETE'}); await refresh()})}>Use real time</button></section>}
      </>}
      {tab === 'add' && <>
        <div className="page-heading"><div><h1>A photo. Then a quick check.</h1><p>Read the label, confirm the details, choose your reminder times.</p></div></div>
        <div className="review-grid"><section className="card source-card"><h2>1. Add your source</h2><div className="segmented"><button disabled={busy || !!document} className={kind === 'medication' ? 'selected' : ''} onClick={() => setKind('medication')}>Medication guide</button><button disabled={busy || !!document} className={kind === 'supplement' ? 'selected' : ''} onClick={() => setKind('supplement')}>Supplement label</button></div>
          <p className="muted">Use a clear photo showing the name and directions. JPEG or PNG, up to 5 MiB.</p>
          {image ? <img className="source-image" src={image} alt="Original uploaded source"/> : <div className="photo-placeholder"><span>▧</span><strong>Keep the whole label in view.</strong><p>Photos are stored privately for this demo.</p></div>}
          <input ref={fileInput} type="file" accept="image/jpeg,image/png" capture="environment" aria-label="Upload a source photo" onChange={e => {const f = e.target.files?.[0]; if (f) void upload(f); e.target.value = ''}}/>
          <button className="full-width" disabled={busy} onClick={() => fileInput.current?.click()}>Take or upload a photo</button>
          <div className="samples"><span>Try a fictional sample</span><button className="text-button" disabled={busy} onClick={() => void sample('medication')}>Medication guide</button><button className="text-button" disabled={busy} onClick={() => void sample('supplement')}>Supplement label</button></div>
          {document && <div className="source-tools"><button className="text-button" disabled={busy} onClick={() => void run(() => read(document))}>Read image again</button><button className="text-button" disabled={busy} onClick={() => {setAttempt(undefined); setDrafts([blank(state?.now || new Date().toISOString())]); setError('')}}>Enter manually</button></div>}
        </section><section className="card review-card"><h2>2. Review & set your times</h2><p className="muted">No reminder starts until you review and confirm. Times are entered by you, never recommended by AI.</p>
          {attempt && <div className="reading-label">{attempt.source === 'sample' ? 'SIMULATED SAMPLE READING' : 'GEMINI READING'} · UNVERIFIED</div>}
          {attempt?.result?.warnings.map((warning, i) => <p className="warning" key={i}>{warning}</p>)}
          {!drafts.length && <div className="empty"><h3>{document ? 'No items waiting for confirmation.' : 'Your source comes first.'}</h3><p>{document ? 'View Today to see your reminders, or add another photo.' : 'Add a photo on the left to begin. You can always enter the details manually.'}</p>{document && <button onClick={() => setTab('today')}>View today</button>}</div>}
          {drafts.map((draft, index) => <form className="review-form" key={`${document?.id}:${index}`} onSubmit={e => {e.preventDefault(); void confirm(index)}}><h3>{document?.kind === 'supplement' ? 'Supplement' : 'Medication'} {drafts.length > 1 ? index + 1 : ''}</h3>
            <label>Name<input required maxLength={160} value={draft.name} onChange={e => change(index, {name: e.target.value, checked: false})}/></label>
            <div className="form-pair"><label>Strength / concentration<input placeholder="As printed, if present" maxLength={160} value={draft.strength} onChange={e => change(index, {strength: e.target.value, checked: false})}/></label><label>Amount per dose<input required placeholder="e.g. 1 tablet" maxLength={160} value={draft.dose} onChange={e => change(index, {dose: e.target.value, checked: false})}/></label></div>
            <label>Original directions<textarea maxLength={1000} value={draft.instruction} onChange={e => change(index, {instruction: e.target.value, checked: false})}/></label>
            <div className="form-pair"><label>Start date<input type="date" required value={draft.start_date} onChange={e => change(index, {start_date: e.target.value, checked: false})}/></label><label>End date<input type="date" required min={draft.start_date} value={draft.end_date} onChange={e => change(index, {end_date: e.target.value, checked: false})}/></label></div>
            <fieldset><legend>Daily reminder times · Seoul</legend><p className="muted">Set times that match your existing instructions. For meal-based or unclear directions, confirm an appropriate fixed time with your pharmacist before saving.</p><div className="time-inputs">{draft.times.map((time, i) => <div key={i}><input type="time" aria-label={`Reminder time ${i + 1}`} required value={time} onChange={e => change(index, {times: draft.times.map((v, n) => n === i ? e.target.value : v), checked: false})}/>{draft.times.length > 1 && <button type="button" className="text-button" aria-label={`Remove reminder time ${i + 1}`} onClick={() => change(index, {times: draft.times.filter((_, n) => i !== n), checked: false})}>×</button>}</div>)}</div><button type="button" className="text-button" disabled={draft.times.length >= 6 || busy} onClick={() => change(index, {times: [...draft.times, ''], checked: false})}>＋ Add another time</button></fieldset>
            <label className="checkbox"><input type="checkbox" required checked={draft.checked} onChange={e => change(index, {checked: e.target.checked})}/><span>I checked the source, amount, dates and reminder times. These times match my existing instructions.</span></label>
            <button disabled={busy || !draft.checked} className="full-width">Confirm & activate reminders</button>
          </form>)}
        </section></div>
      </>}
      {tab === 'routines' && <>
        <div className="page-heading"><div><h1>Everything you’ve confirmed.</h1><p>Your original images and readings stay separate from your saved routines.</p></div></div>
        <section className="routine-grid">{state?.routines.map(r => <article className="card" key={r.id}><span className="kind">{r.kind} · {r.active ? 'Active' : 'Stopped'}</span><h2>{r.name}</h2><p>{r.strength || 'Strength not entered'} · {r.dose}</p><p className="directions">{r.instruction || 'No original directions entered'}</p><div className="time-chips">{r.times.map(t => <span key={t}>{t}</span>)}</div><p className="muted">{r.start_date} → {r.end_date} · Seoul</p><p className="muted">{r.provenance === 'manual' ? 'Manually entered & confirmed' : 'Reading reviewed & confirmed'}</p>{r.active && <button className="secondary" disabled={busy} onClick={() => void run(async () => {await api(`/routines/${r.id}/stop`, {method:'POST'}); await refresh(); setNotice('Routine stopped. Future reminders are disabled.')})}>Stop reminders</button>}</article>)}</section>
        {!state?.routines.length && <section className="card empty"><h3>No confirmed routines yet.</h3><button onClick={() => setTab('add')}>Add a photo</button></section>}
        <section className="card saved-sources"><h2>Saved source images</h2><p className="muted">Reopen an image to review its latest reading or add another item. Already confirmed routines stay unchanged.</p>{state?.documents.map((doc, i) => <button className="secondary" disabled={busy} key={doc.id} onClick={() => void resume(doc)}>Open {doc.kind} source {i + 1}</button>)}</section>
      </>}
      <footer>A reminder and self-report tool. It does not recommend doses, choose safe combinations or verify ingestion.</footer>
    </main>
  </div>
}

createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>)
