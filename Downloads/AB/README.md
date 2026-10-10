# GATE PYQ Command Center

A polished React + TypeScript + Vite study workspace for the supplied GATE PYQ volumes.

## Stack

- React 19 + TypeScript + Vite
- Tailwind CSS + shadcn-style UI primitives
- Lucide icons
- Motion for transitions and micro-interactions
- TanStack Query for async/cache orchestration
- TanStack Virtual for the question list
- Recharts for study analytics
- Sonner for feedback/toasts
- cmdk for Ctrl/Cmd+K command search
- Vaul for the mobile navigation drawer
- React Hook Form + Zod for profile/forms
- React Dropzone + browser-image-compression for local profile photos
- react-fast-marquee for the top-solvers strip
- date-fns + use-debounce for activity and search UX
- Firebase Authentication (Google + email/password)
- Supabase PostgreSQL for questions, progress, reactions and notifications
- Supabase Firebase Third-Party Auth so Firebase ID tokens are verified by Supabase RLS
- PDF.js for lazy question rendering

## UX highlights

- Soft lavender SaaS-style light theme and focused dark theme
- Responsive desktop/mobile navigation
- Home, Questions, Dashboard, Leaderboard, Profile, Notifications and Settings
- Virtualized question list with lazy PDF crops and next-question warming
- Exact GateOverflow link stored with each question's source metadata
- One reaction per user per question, with optimistic UI and durable Supabase state
- Personal statuses: solved, wrong, redo, important and not attempted
- Cloud-backed progress plus a user-scoped local cache so refreshes do not wipe the visible study state while cloud data is loading
- Dashboard with coverage, accuracy, streak and subject performance
- Public aggregate leaderboard view
- Ctrl/Cmd+K command palette
- Local-only compressed profile photo
- Graceful error boundary instead of a full-page crash
- Question-level PDF segmentation so each viewer shows only one PYQ, including multi-page questions
- Responsive high-resolution question rendering with original aspect ratio preserved
- Animated orbiting neon beam around the home hero card, with reduced-motion support
- Question of the Day, revision queue, confidence tracking, goal tracking and achievement milestones
- Deep topic analytics, confidence map, shareable progress snapshot and stronger search token matching
- Security/performance foundation with RLS migration, confidence/goal tables, caching, virtualization and lazy rendering

## Run locally

Node 20+ is recommended.

```bash
npm install
npm run dev
```

The project intentionally keeps the generated `package-lock.json` from the previous build. Running `npm install` will reconcile it with the enhanced dependency set in `package.json`.

## Environment

Copy `.env.example` to `.env.local` and fill the Firebase web configuration and Supabase public key.

Never place a Firebase Admin/service-account key or Supabase secret/service-role key in browser code.

## Supabase migrations

Run these in the Supabase SQL editor in order where applicable:

1. The existing schema/question seed migrations.
2. `supabase/firebase_migration.sql` for Firebase-owned user state.
3. `supabase/reaction_sync_migration.sql` for the transaction-safe reaction RPC.
4. `supabase/notifications_migration.sql` for notifications/preferences.
5. `supabase/leaderboard_migration.sql` for the public aggregate leaderboard.
6. `supabase/comments_migration.sql` for question discussions.
7. `supabase/profile_comments_upgrade.sql` for public profile avatars/verification badges and owner-only comment editing/deletion.
8. `supabase/reliability_upgrade_migration.sql` to repair reaction syncing and profile/comment policies on an existing database.
9. `supabase/future_features_migration.sql` for confidence tracking and synced study goals.

The leaderboard view exposes only display name and aggregate study metrics. It does not expose Firebase UIDs.

## Important persistence note

Firebase is the identity provider. Supabase is the durable source of truth for authenticated study data. The browser's localStorage is only used for UI preferences and a user-scoped cache of already-synced progress/reactions, plus the local-only profile photo.

This means refreshing the page should no longer reset the visible solved/wrong/redo/important state while Firebase/Supabase reconnects.

## Reaction authentication note

Supabase Third-Party Auth must be configured for the Firebase project. Firebase ID tokens used with the Supabase Data API should carry the `role: authenticated` custom claim. The client already passes the current Firebase ID token through the Supabase `accessToken` callback.

For an existing Firebase project, assign the claim once with the Firebase Admin SDK. Never put the Admin SDK credentials in Vite/browser code.

```bash
npm install firebase-admin
# configure GOOGLE_APPLICATION_CREDENTIALS to point to your Firebase Admin service-account JSON
npm run set:firebase-role
```

After the claim is assigned, sign out and sign back in so Firebase issues a fresh ID token. Supabase's current Firebase third-party-auth guidance requires the `role: authenticated` claim for authenticated Data API access.

## Question discussions

Run `supabase/comments_migration.sql` in Supabase SQL Editor to enable the compact discussion section under each question.

## Authentication upgrade
The current build supports Google sign-in, email/password, Firebase password-reset email, and 6-digit email OTP login/signup. Email OTP is delivered by the Vercel `/api/email-otp` server function through Resend and stores only hashed OTP material in Supabase. Run `supabase/auth_otp_migration.sql` before enabling OTP. Configure the server-only Firebase Admin, Supabase service-role, and Resend environment variables in Vercel; never expose those values through `VITE_*` variables.

## Question timing

`supabase/timing_and_print_migration.sql` adds per-user fastest/longest question timing and attempt count. The client also keeps a local timing cache, so the timer remains usable before the migration is applied; cloud timing syncs once the columns exist.

## Printing important questions

Mark questions as **Important**. Use the Important status in the question library, then choose **Print important**. The browser print dialog can save the collection as a PDF or send it to a printer.

## Latest study workspace upgrades

- Question timing is persisted per user with fastest, longest, last attempt and attempt count.
- Important questions are stored separately from solve status and appear in the personal dashboard.
- The print workflow lets users select, remove, add and print a practice set.
- The Question Bank uses subject-wise collapsible sections while retaining filters and virtualized rendering.
- Password fields include show/hide controls.
- Each question includes a lazy-loaded "Stuck? Get a suggestion" tutor panel. If `AI_API_KEY` (or `OPENAI_API_KEY`) is configured on Vercel, `/api/question-help` can generate question-specific guidance using the GateOverflow source page. Without an AI key, the feature remains safe and provides indexed-answer/topic-based fallback guidance.

Run `supabase/timing_and_print_migration.sql` in Supabase SQL Editor before using cloud timing/Important sync.
## Question answers + global timing

Run `supabase/answer_and_global_timing_migration.sql` after the existing migrations to enable first-answer-only option statistics and question-wide fastest/longest timing aggregates. The migration exposes only aggregate answer counts and aggregate timing values to the browser; individual users and their individual timings are not exposed.


## Live question sync and tutor suggestions
- The selected question uses Supabase Realtime Broadcast for low-latency cross-user updates to answer percentages, global fastest/longest timing, reactions and comments. The database remains authoritative and the client refetches after every live event.
- Question suggestions now receive the exact text extracted from the question's PDF crop, plus the indexed answer and optional GateOverflow page text. A server-side Gemini API key can provide question-specific tutoring; the API key is never exposed to the browser.
- `GEMINI_API_KEY` is optional. `GEMINI_MODEL` defaults to `gemini-2.5-flash-lite`.

## Reliability upgrades

- `supabase/realtime_question_sync.sql` moves question-level live synchronization to database-triggered Supabase Realtime broadcasts for timing, answer statistics, reactions, and comments.
- Answer statistics are also cached per signed-in user so a refresh does not visually erase a previously recorded first answer while the cloud query is reconnecting.
- `/api/daily-study-email` provides email-only study reminders through Resend and is scheduled once daily through Vercel Cron.


## Private access and source-content changes
- Access is denied by default. The owner approves accounts in the **Access control** view.
- Sharing the website URL does not transfer approval; access is tied to a verified Firebase UID.
- Per-member permissions include viewing the question index, printing, downloading, copying, and exporting. Printing and progress export/copy controls are checked in the UI; no question PDFs or question statements are bundled.
- The distributed question bank contains metadata and direct GateOverflow links only. It no longer includes question statements, answer keys, scan crops, or source PDFs.
- Apply `supabase/access_control_migration.sql` and configure server-only variables listed in `firebase-setup-checklist.md` before deploying. Keep deployment paused until configuration is complete.
- Browser restrictions cannot reliably block screenshots or photos of the screen.

### Private local run
- The private access API runs through Vercel Functions, so `vite preview` alone is not sufficient.
- Link this project folder once with `vercel link`, then configure a local `.env.local` with the required server-only values and Firebase web values.
- Run `Launch-GATE-PYQ-Private.ps1` or use `vercel dev --listen 127.0.0.1:4173`. The app listens on loopback and does not deploy.
- Keep `.env.local` and `.vercel/` out of shared archives.
