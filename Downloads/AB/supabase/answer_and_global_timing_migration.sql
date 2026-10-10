-- GATE PYQ Command Center: first-answer voting + question-wide timing aggregates.
-- Additive migration. Existing per-user progress/timing is preserved.
begin;

create table if not exists public.question_answer_votes (
  question_id text not null references public.questions(id) on delete cascade,
  user_id text not null,
  answer_key text not null check (answer_key ~ '^[ABCD](;[ABCD])*$'),
  created_at timestamptz not null default now(),
  primary key (question_id, user_id)
);

create index if not exists question_answer_votes_question_idx
  on public.question_answer_votes(question_id);

alter table public.question_answer_votes enable row level security;

-- No direct row reads/writes are exposed. The SECURITY DEFINER RPCs below return
-- only anonymous aggregate counts and whether the current user has submitted.
drop policy if exists "answer votes own insert" on public.question_answer_votes;
create policy "answer votes own insert"
  on public.question_answer_votes
  for insert
  with check ((auth.jwt()->>'sub') = user_id);

drop policy if exists "answer votes own read" on public.question_answer_votes;
create policy "answer votes own read"
  on public.question_answer_votes
  for select
  using ((auth.jwt()->>'sub') = user_id);

create table if not exists public.question_timing_aggregates (
  question_id text primary key references public.questions(id) on delete cascade,
  min_time_ms bigint not null check (min_time_ms >= 1000),
  max_time_ms bigint not null check (max_time_ms >= min_time_ms),
  attempt_count bigint not null default 1 check (attempt_count > 0),
  updated_at timestamptz not null default now()
);

alter table public.question_timing_aggregates enable row level security;
drop policy if exists "timing aggregate public read" on public.question_timing_aggregates;
create policy "timing aggregate public read"
  on public.question_timing_aggregates
  for select
  using (true);

create or replace function public.submit_question_answer(p_question_id text, p_answer_key text)
returns table(answer_key text, count bigint, is_mine boolean)
language plpgsql
security definer
set search_path = public
as $$
declare
  normalized text := upper(regexp_replace(trim(p_answer_key), '\\s+', '', 'g'));
begin
  if auth.jwt()->>'sub' is null then
    raise exception 'authentication required';
  end if;
  if normalized !~ '^[ABCD](;[ABCD])*$' then
    raise exception 'invalid answer key';
  end if;

  insert into public.question_answer_votes(question_id, user_id, answer_key)
  values (p_question_id, auth.jwt()->>'sub', normalized)
  on conflict (question_id, user_id) do nothing;

  return query
  select v.answer_key,
         count(*)::bigint,
         bool_or(v.user_id = auth.jwt()->>'sub')
  from public.question_answer_votes v
  where v.question_id = p_question_id
  group by v.answer_key
  order by v.answer_key;
end;
$$;

create or replace function public.get_question_answer_stats(p_question_id text)
returns table(answer_key text, count bigint, is_mine boolean)
language sql
security definer
set search_path = public
as $$
  select v.answer_key,
         count(*)::bigint,
         bool_or(v.user_id = auth.jwt()->>'sub')
  from public.question_answer_votes v
  where v.question_id = p_question_id
  group by v.answer_key
  order by v.answer_key;
$$;

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

grant execute on function public.submit_question_answer(text, text) to authenticated;
grant execute on function public.get_question_answer_stats(text) to anon, authenticated;
grant execute on function public.record_question_timing(text, bigint) to authenticated;
grant select on public.question_timing_aggregates to anon, authenticated;

notify pgrst, 'reload schema';
commit;
