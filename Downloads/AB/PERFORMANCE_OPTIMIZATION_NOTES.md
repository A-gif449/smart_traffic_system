# Performance optimization notes

## Changes in this pass

- Removed the 2.6 MB question-bank JSON from the eagerly bundled application module.
- Load `/questions.json` asynchronously after the initial React render, so the homepage can paint before the question data is downloaded and parsed.
- Build the subject, topic, search, and question indexes once after the data arrives, retaining the existing question IDs and metadata.
- Recompute question-dependent derived data when the question bank becomes ready.
- Added a visible loading label and a recoverable reload message if the question bank cannot be fetched.
- Kept the existing TanStack Virtual implementation, PDF lazy-loading behavior, Firebase/Supabase calls, timer logic, and database migrations unchanged.

## Verification status

- Source-level inspection completed.
- The source ZIP's dependencies could not be installed in this environment because npm registry access timed out; a production build and automated browser regression suite therefore could not be run here.
- Do not deploy this ZIP until `npm ci` and `npm run build` pass locally or in CI and the timer/auth/progress/reactions/comments flows are smoke-tested.
- No Lighthouse improvement is claimed until the optimized version is deployed and measured under the same test conditions as the baseline.

## Suggested verification

1. `npm ci`
2. `npm run build`
3. `npm run preview` and test home, question search, filters, direct `?question=...` links, timer/global timing, progress, reactions, comments, dashboard, and mobile layout.
4. Run three clean Mobile Lighthouse audits and compare median Performance, FCP, LCP, TBT, and CLS against the prior deployment.
