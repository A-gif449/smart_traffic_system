import { createClient } from '@supabase/supabase-js'

type Pref = { user_id: string; email: string | null; daily_email_enabled: boolean; daily_goal: number; timezone: string }

function localDate(value: string | Date, timezone: string) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
}
function addDays(key: string, days: number) {
  const d = new Date(`${key}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}
function streak(dates: Set<string>, today: string) {
  let cursor = today
  let n = 0
  while (dates.has(cursor)) { n++; cursor = addDays(cursor, -1) }
  return n
}
function esc(value: unknown) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c] || c))
}

export default async function handler(req: any, res: any) {
  if (req.method !== 'GET' && req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' })
  const cronSecret = process.env.CRON_SECRET
  if (cronSecret && req.headers.authorization !== `Bearer ${cronSecret}`) return res.status(401).json({ error: 'Unauthorized' })

  const supabaseUrl = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  const resendKey = process.env.RESEND_API_KEY
  const fromEmail = process.env.RESEND_FROM_EMAIL
  if (!supabaseUrl || !serviceKey || !resendKey || !fromEmail) {
    return res.status(500).json({ error: 'Missing SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, RESEND_API_KEY or RESEND_FROM_EMAIL' })
  }

  const db = createClient(supabaseUrl, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } })
  const { data: prefs, error: prefError } = await db
    .from('notification_preferences')
    .select('user_id,email,daily_email_enabled,daily_goal,timezone')
    .eq('daily_email_enabled', true)
    .not('email', 'is', null)
  if (prefError) return res.status(500).json({ error: prefError.message })

  let sent = 0
  let skipped = 0
  const results: Array<{ user_id: string; sent: boolean; reason?: string }> = []

  for (const pref of (prefs ?? []) as Pref[]) {
    if (!pref.email) { skipped++; continue }
    const timezone = pref.timezone || 'Asia/Kolkata'
    const today = localDate(new Date(), timezone)
    const from = new Date(Date.now() - 30 * 86400000).toISOString()
    const { data: rows, error: rowsError } = await db
      .from('question_progress')
      .select('question_id,status,updated_at')
      .eq('user_id', pref.user_id)
      .gte('updated_at', from)
    if (rowsError) { results.push({ user_id: pref.user_id, sent: false, reason: rowsError.message }); continue }

    const solvedDates = new Set<string>()
    let todaySolved = 0
    let lastActivity = 0
    let wrongRedo = 0
    let important = 0
    let agingSolved = 0
    for (const row of rows ?? []) {
      const stamp = row.updated_at ? new Date(row.updated_at).getTime() : 0
      if (stamp > lastActivity) lastActivity = stamp
      const day = localDate(row.updated_at, timezone)
      if (row.status === 'solved') {
        solvedDates.add(day)
        if (day === today) todaySolved++
        if (stamp > 0 && (Date.now() - stamp) / 86400000 >= 3) agingSolved++
      }
      if (row.status === 'wrong' || row.status === 'redo') wrongRedo++
      if (row.status === 'important') important++
    }

    const currentStreak = streak(solvedDates, today)
    const goal = Math.max(1, Number(pref.daily_goal || 10))
    const inactiveDays = lastActivity ? Math.floor((Date.now() - lastActivity) / 86400000) : 0
    const revisionDue = wrongRedo + important + agingSolved
    const reasons: string[] = []
    if (revisionDue > 0) reasons.push(`${revisionDue} PYQs are waiting for revision`)
    if (inactiveDays >= 3) reasons.push(`you have been away for ${inactiveDays} days`)
    if (todaySolved < goal && inactiveDays < 3) reasons.push(`${goal - todaySolved} questions remain in today's goal`)
    if (!reasons.length) { skipped++; continue }

    const subject = revisionDue > 0 ? 'Your GATE revision queue is waiting 📚' : inactiveDays >= 3 ? 'Ready for a quick GATE PYQ session?' : 'Your GATE study goal is still open 🎯'
    const preview = reasons.join(' · ')
    const html = `<div style="font-family:Inter,Arial,sans-serif;max-width:620px;margin:auto;padding:32px;color:#172033"><h2 style="margin:0 0 8px">${esc(subject)}</h2><p style="color:#5d6678">A quick study nudge from GATE PYQ Command Center.</p><div style="margin:22px 0;padding:18px;border:1px solid #e5e7eb;border-radius:14px"><b>${esc(preview)}</b><div style="margin-top:12px;color:#5d6678">Solved today: ${todaySolved}/${goal} · Streak: ${currentStreak} day${currentStreak === 1 ? '' : 's'}</div></div><p>Open your question library and tackle a small focused set. Consistency beats marathon sessions.</p></div>`
    const response = await fetch('https://api.resend.com/emails', { method: 'POST', headers: { Authorization: `Bearer ${resendKey}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ from: fromEmail, to: [pref.email], subject, html }) })
    if (response.ok) { sent++; results.push({ user_id: pref.user_id, sent: true }) }
    else results.push({ user_id: pref.user_id, sent: false, reason: `Resend HTTP ${response.status}` })
  }

  return res.status(200).json({ sent, skipped, checked: prefs?.length ?? 0, results })
}
