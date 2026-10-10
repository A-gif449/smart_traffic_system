# Firebase + Supabase setup checklist

- [ ] Firebase Web App registered
- [ ] Firebase Email/Password enabled
- [ ] Firebase Google provider enabled
- [ ] Firebase Authorized Domains includes localhost
- [ ] Firebase Project ID copied into Supabase Authentication > Third-Party Auth > Firebase
- [ ] `.env.local` has all `VITE_FIREBASE_*` values
- [ ] `.env.local` has `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
- [ ] `supabase/firebase_migration.sql` run once
- [ ] `npm install`
- [ ] `npm run dev`

## Email OTP authentication
The app now supports 6-digit email OTP login/signup and Firebase password reset.

For the Vercel `/api/email-otp` function, add these as **server-only** Vercel Environment Variables:
- `FIREBASE_PROJECT_ID`
- `FIREBASE_CLIENT_EMAIL`
- `FIREBASE_PRIVATE_KEY` (store the service-account private key; never commit it)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`

Run `supabase/auth_otp_migration.sql` once in the Supabase SQL editor before using email OTP.
The browser only uses the Firebase web config and Supabase anon key. Never expose the service-role key, Firebase private key, or Resend key through `VITE_*` variables.


## Owner-approved private access
1. Run `supabase/access_control_migration.sql` in the Supabase SQL editor.
2. In Vercel Environment Variables, set server-only `OWNER_FIREBASE_UID`, `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`. The owner UID is the Firebase Authentication UID of your own account. Do not put these values in any `VITE_*` variable or commit them.
3. Deploy while Vercel Deployment Protection is enabled. Sign in using the owner account. The owner can then open **Access control**, approve existing Firebase accounts by email, and assign per-account permissions. New accounts are denied by default.
4. Keep the Vercel project paused until you have set the server variables and run the migration. The API intentionally fails closed if these are missing.

Question statements, answer keys, and scanned PDF crops have been removed from the distributed question bank. The app retains question metadata and direct source links instead. Attribution or changing screenshots into text is not a substitute for permission to reproduce protected content.
