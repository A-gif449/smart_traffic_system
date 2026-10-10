-- GATE PYQ Command Center: Firebase-auth compatibility repair for answer/timing aggregates.
-- Run this AFTER answer_and_global_timing_migration.sql if that migration was already run.
-- The project uses Firebase UIDs in Supabase, not Supabase Auth UUIDs.

begin;

-- The first version of answer_and_global_timing_migration.sql created user_id as
-- uuid -> auth.users(id). Firebase users are identified by the JWT `sub` string,
-- so replace that column with a plain text Firebase UID.
alter table public.question_answer_votes
  drop constraint if exists question_answer_votes_user_id_fkey;

alter table public.question_answer_votes
  alter column user_id type text using user_id::text;

-- Firebase JWT subject is the stable user identifier for this application.
drop policy if exists "answer votes own insert" on public.question_answer_votes;
drop policy if exists "answer votes own read" on public.question_answer_votes;

create policy "answer votes own insert"
  on public.question_answer_votes
  for insert to authenticated
  with check ((auth.jwt()->>'sub') = user_id);

create policy "answer votes own read"
  on public.question_answer_votes
  for select to authenticated
  using ((auth.jwt()->>'sub') = user_id);

create or replace function public.submit_question_answer(p_question_id text, p_answer_key text)
returns table(answer_key text, count bigint, is_mine boolean)
language plpgsql
security definer
set search_path = public
as $$
declare
  firebase_uid text := auth.jwt()->>'sub';
  normalized text := upper(regexp_replace(trim(p_answer_key), '\\s+', '', 'g'));
begin
  if firebase_uid is null or firebase_uid = '' then
    raise exception 'authentication required';
  end if;
  if normalized !~ '^[ABCD](;[ABCD])*$' then
    raise exception 'invalid answer key';
  end if;

  insert into public.question_answer_votes(question_id, user_id, answer_key)
  values (p_question_id, firebase_uid, normalized)
  on conflict (question_id, user_id) do nothing;

  return query
  select v.answer_key,
         count(*)::bigint,
         bool_or(v.user_id = firebase_uid)
  from public.question_answer_votes v
  where v.question_id = p_question_id
  group by v.answer_key
  order by v.answer_key;
end;
$$;

grant select on public.question_answer_votes to authenticated;
grant execute on function public.submit_question_answer(text, text) to authenticated;

grant execute on function public.get_question_answer_stats(text) to authenticated;

create or replace function public.record_question_timing(p_question_id text, p_elapsed_ms bigint)
returns table(min_time_ms bigint, max_time_ms bigint, attempt_count bigint)
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.jwt()->>'sub' is null then
    raise exception 'authentication required';
  end if;
  if p_elapsed_ms < 1000 then
    return query select null::bigint, null::bigint, null::bigint;
    return;
  end if;

  insert into public.question_timing_aggregates(question_id, min_time_ms, max_time_ms, attempt_count, updated_at)
  values (p_question_id, p_elapsed_ms, p_elapsed_ms, 1, now())
  on conflict (question_id) do update set
    min_time_ms = least(public.question_timing_aggregates.min_time_ms, excluded.min_time_ms),
    max_time_ms = greatest(public.question_timing_aggregates.max_time_ms, excluded.max_time_ms),
    attempt_count = public.question_timing_aggregates.attempt_count + 1,
    updated_at = now();

  return query
  select a.min_time_ms, a.max_time_ms, a.attempt_count
  from public.question_timing_aggregates a
  where a.question_id = p_question_id;
end;
$$;

grant execute on function public.record_question_timing(text, bigint) to authenticated;

notify pgrst, 'reload schema';
commit;
