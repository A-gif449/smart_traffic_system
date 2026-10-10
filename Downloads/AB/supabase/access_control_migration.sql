-- Owner-controlled approvals for the GATE PYQ Command Center.
-- This table is accessed only by server API endpoints using SUPABASE_SERVICE_ROLE_KEY.
create table if not exists public.approved_members (
  uid text primary key,
  email text not null,
  approved boolean not null default false,
  permissions jsonb not null default '{"view_questions": false, "print_questions": false, "download_files": false, "copy_text": false, "export_data": false}'::jsonb,
  approved_by text,
  approved_at timestamptz,
  revoked_by text,
  revoked_at timestamptz,
  updated_by text,
  updated_at timestamptz,
  created_at timestamptz not null default now(),
  constraint approved_members_permissions_object check (jsonb_typeof(permissions) = 'object')
);
alter table public.approved_members enable row level security;
revoke all on public.approved_members from anon, authenticated;
-- No client-side policies by design. The service-role key must never be exposed to VITE_* variables.

-- Restrict existing browser-facing tables too, not only the React UI.
-- The function is SECURITY DEFINER so members do not need direct SELECT access to approved_members.
create or replace function public.is_approved_gate_pyq_member()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.approved_members m
    where m.uid = coalesce(auth.jwt()->>'sub', '')
      and m.approved = true
      and coalesce(m.permissions->>'view_questions', 'false') = 'true'
  );
$$;
revoke all on function public.is_approved_gate_pyq_member() from public;
grant execute on function public.is_approved_gate_pyq_member() to anon, authenticated;

do $$
declare
  t text;
  guarded_tables text[] := array[
    'profiles','questions','question_progress','question_reactions','question_comments',
    'question_answer_votes','question_timing_aggregates','question_confidence','study_goals',
    'notification_preferences','notifications','question_reaction_counts','question_answer_stats'
  ];
begin
  foreach t in array guarded_tables loop
    if exists (select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relname=t and c.relkind in ('r','p')) then
      execute format('drop policy if exists %I on public.%I', 'gate pyq approved members only', t);
      execute format(
        'create policy %I on public.%I as restrictive for all to anon, authenticated using (public.is_approved_gate_pyq_member()) with check (public.is_approved_gate_pyq_member())',
        'gate pyq approved members only', t
      );
    end if;
  end loop;
end $$;

-- Remove previously seeded answer keys from an existing question index, if present.
do $$
begin
  if exists (select 1 from information_schema.columns where table_schema='public' and table_name='questions' and column_name='answer') then
    execute 'update public.questions set answer = null where answer is not null';
  end if;
end $$;
