-- GATE PYQ Command Center: persistent timing + per-user Important collection.
-- Safe/additive migration. Existing progress is preserved.
begin;

alter table if exists public.question_progress
  add column if not exists min_time_ms bigint,
  add column if not exists max_time_ms bigint,
  add column if not exists last_time_ms bigint,
  add column if not exists attempt_count integer not null default 0,
  add column if not exists is_important boolean not null default false;

-- Preserve the legacy Important status before separating it from solve status.
update public.question_progress
set is_important = true
where status = 'important' and coalesce(is_important, false) = false;

update public.question_progress
set status = 'unsolved'
where status = 'important';

create index if not exists question_progress_user_important_idx
  on public.question_progress(user_id, is_important)
  where is_important = true;

create index if not exists question_progress_user_time_idx
  on public.question_progress(user_id, updated_at desc);

notify pgrst, 'reload schema';
commit;
