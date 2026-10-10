# Live sync + question tutor upgrade

This upgrade preserves the existing Firebase + Supabase architecture and does not change the print workflow.

## What changed

- Question answer statistics are refreshed through Supabase Realtime Broadcast when another student submits an answer.
- Global fastest/longest timing is recorded at answer submission time, not when a later status button is clicked.
- Timing values are shown to 0.1 second for a precise shared display.
- A student who already has a first answer saved does not have that answer replaced by retries.
- Reactions broadcast a refresh to other students viewing the same question.
- Comments broadcast a refresh to other students viewing the same discussion.
- The database remains authoritative. Realtime events only trigger a fresh read, so a forged broadcast cannot change stored data.
- The tutor receives exact question text extracted from the corresponding PDF crop, the indexed answer, metadata, and the GateOverflow page text when available.
- Tutor responses are cached in memory for the current browser session so revisiting a question does not repeatedly call the AI service.

## Supabase

The existing Firebase-compatible answer/timing migration remains in `supabase/answer_and_global_timing_firebase_fix.sql`.

The live sync implementation uses Supabase Realtime Broadcast and does not require a new database table or a new publication for the selected-question channel.

## AI tutor

The recommended free starting point is Gemini API. The server accepts:

`GEMINI_API_KEY`

Optional model override:

`GEMINI_MODEL=gemini-2.5-flash-lite`

Do not put this key in a `VITE_*` variable. It must remain a Vercel server environment variable.

The existing `AI_API_KEY` / `AI_MODEL` / `AI_API_URL` path is still supported as a fallback.

Without an AI key, the tutor does not invent a solution. It shows question-specific guidance based on the exact PDF crop and indexed answer instead.

## Reliable live question synchronization

Run `supabase/realtime_question_sync.sql` once after the answer/timing, reaction, and comments tables exist. It uses database-triggered Supabase Realtime broadcasts, so another student's timing/answer/reaction/comment change causes the open question to refresh without relying on the submitting browser to broadcast the event.

## Email-only study reminders

The Vercel cron endpoint is `/api/daily-study-email`. It sends only email through Resend. Configure these Vercel environment variables: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and a random `CRON_SECRET`. The cron runs once daily and skips users who have disabled daily email or have no meaningful reminder condition.
