-- GATE PYQ Command Center: database-driven live question synchronization.
-- This replaces fragile client-to-client broadcast calls with database triggers.
-- It broadcasts only a tiny {questionId, kind} payload, never user identity or comment text.
-- Safe to run repeatedly.

begin;

-- Realtime Broadcast authorization for authenticated Firebase users.
-- The application uses public question topics, so no user data is exposed by these events.
do $$
begin
  if to_regclass('realtime.messages') is not null then
    execute 'drop policy if exists "gate pyq authenticated receive question broadcasts" on realtime.messages';
    execute 'create policy "gate pyq authenticated receive question broadcasts" on realtime.messages for select to authenticated using (true)';
  end if;
exception when insufficient_privilege then
  -- If the project does not allow editing realtime.messages policies, the normal
  -- database tables remain authoritative and the client still refreshes on selection.
  null;
end $$;

create or replace function public.broadcast_question_timing_change()
returns trigger
security definer
set search_path = public
language plpgsql
as $$
begin
  perform realtime.send(
    jsonb_build_object(
      'questionId', coalesce(new.question_id, old.question_id),
      'kind', 'timing'
    ),
    'question-updated',
    'question-live:' || coalesce(new.question_id, old.question_id),
    false
  );
  return coalesce(new, old);
end;
$$;

drop trigger if exists gate_pyq_timing_broadcast on public.question_timing_aggregates;
create trigger gate_pyq_timing_broadcast
after insert or update or delete on public.question_timing_aggregates
for each row execute function public.broadcast_question_timing_change();

create or replace function public.broadcast_question_answer_change()
returns trigger
security definer
set search_path = public
language plpgsql
as $$
begin
  perform realtime.send(
    jsonb_build_object(
      'questionId', coalesce(new.question_id, old.question_id),
      'kind', 'answer'
    ),
    'question-updated',
    'question-live:' || coalesce(new.question_id, old.question_id),
    false
  );
  return coalesce(new, old);
end;
$$;

drop trigger if exists gate_pyq_answer_broadcast on public.question_answer_votes;
create trigger gate_pyq_answer_broadcast
after insert or update or delete on public.question_answer_votes
for each row execute function public.broadcast_question_answer_change();

create or replace function public.broadcast_question_reaction_change()
returns trigger
security definer
set search_path = public
language plpgsql
as $$
begin
  perform realtime.send(
    jsonb_build_object(
      'questionId', coalesce(new.question_id, old.question_id),
      'kind', 'reaction'
    ),
    'question-updated',
    'question-live:' || coalesce(new.question_id, old.question_id),
    false
  );
  return coalesce(new, old);
end;
$$;

drop trigger if exists gate_pyq_reaction_broadcast on public.question_reactions;
create trigger gate_pyq_reaction_broadcast
after insert or update or delete on public.question_reactions
for each row execute function public.broadcast_question_reaction_change();

create or replace function public.broadcast_question_comment_change()
returns trigger
security definer
set search_path = public
language plpgsql
as $$
begin
  perform realtime.send(
    jsonb_build_object(
      'questionId', coalesce(new.question_id, old.question_id),
      'kind', 'comment'
    ),
    'question-updated',
    'question-live:' || coalesce(new.question_id, old.question_id),
    false
  );
  return coalesce(new, old);
end;
$$;

drop trigger if exists gate_pyq_comment_broadcast on public.question_comments;
create trigger gate_pyq_comment_broadcast
after insert or update or delete on public.question_comments
for each row execute function public.broadcast_question_comment_change();

notify pgrst, 'reload schema';
commit;
