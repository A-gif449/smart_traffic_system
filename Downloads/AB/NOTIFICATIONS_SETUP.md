# Email-only study reminders

The project uses **email only** for study reminders. It does not add SMS, web push, or mobile push.

## Provider

The email sender is **Resend**. Its current free transactional tier provides 3,000 emails/month with a 100-email/day limit.

## Required Vercel environment variables

Add these to the Vercel project. Keep them server-only, never `VITE_*`:

```text
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
RESEND_API_KEY=YOUR_RESEND_API_KEY
RESEND_FROM_EMAIL=Your Name <verified@your-domain.com>
CRON_SECRET=YOUR_RANDOM_SECRET
```

`RESEND_FROM_EMAIL` must use a sender/domain accepted by Resend.

## Database

Run these migrations in Supabase SQL Editor as applicable:

```text
supabase/firebase_migration.sql
supabase/notifications_migration.sql
supabase/smart_revision_notifications_migration.sql
supabase/answer_and_global_timing_firebase_fix.sql
supabase/realtime_question_sync.sql
```

Do **not** rerun the old UUID-based answer migration against the already-repaired Firebase answer table.

## Daily email

The Vercel function is:

```text
/api/daily-study-email
```

`vercel.json` schedules it once per day. Vercel Hobby cron jobs can run once per day, with invocation timing within the scheduled hour.

The function sends an email only when there is a useful reason, such as:

- revision questions waiting
- wrong/redo questions waiting
- important questions waiting
- solved questions that have aged for revision
- the student has been inactive for 3+ days
- the daily study goal is still incomplete

It skips users who have disabled daily email.

## In-app notification bell

The existing in-app notification bell remains separate from email. Supabase Realtime delivers newly created notification rows to the signed-in browser.

## Security

Never expose:

- `SUPABASE_SERVICE_ROLE_KEY`
- `RESEND_API_KEY`
- `CRON_SECRET`
- Firebase Admin service-account JSON

in browser code or `VITE_*` variables.
