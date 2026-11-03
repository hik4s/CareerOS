-- Apply in the Supabase SQL editor or via the Supabase migration CLI.
create table public.cloud_profiles (
 user_id uuid primary key references auth.users(id) on delete cascade,
 data jsonb not null default '{}'
);
create table public.cloud_jobs (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 title text not null, company text not null default '', description text not null default '',
 url text not null default '', location text not null default '', work_model text not null default '',
 status text not null default 'saved', fit_score numeric, analysis jsonb,
 created_at timestamptz not null default now()
);
create table public.cloud_ai_runs (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 request_hash text not null, provider text not null, model text not null, task text not null,
 result text not null, input_tokens integer, output_tokens integer, estimated_input_tokens integer,
 estimated_cost numeric, cache_hit boolean not null default false,
 created_at timestamptz not null default now()
);
create table public.cloud_resumes (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 filename text not null, storage_path text not null unique, text text not null default '',
 created_at timestamptz not null default now(),
 constraint resume_owner_path check (split_part(storage_path, '/', 1) = user_id::text)
);
create index cloud_jobs_owner_idx on public.cloud_jobs(user_id, created_at desc);
create index cloud_ai_cache_idx on public.cloud_ai_runs(user_id, request_hash, created_at desc);
create index cloud_resumes_owner_idx on public.cloud_resumes(user_id);

alter table public.cloud_profiles enable row level security;
alter table public.cloud_jobs enable row level security;
alter table public.cloud_ai_runs enable row level security;
alter table public.cloud_resumes enable row level security;
create policy owner_only on public.cloud_profiles for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy owner_only on public.cloud_jobs for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy owner_only on public.cloud_ai_runs for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy owner_only on public.cloud_resumes for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
grant select, insert, update, delete on public.cloud_profiles, public.cloud_jobs, public.cloud_ai_runs, public.cloud_resumes to authenticated;
revoke all on public.cloud_profiles, public.cloud_jobs, public.cloud_ai_runs, public.cloud_resumes from anon;

-- Serialize per-user inserts so concurrent requests cannot exceed ten resumes.
create function public.limit_cloud_resumes() returns trigger language plpgsql set search_path = public as $$
begin
 perform pg_advisory_xact_lock(hashtextextended(new.user_id::text, 0));
 if (select count(*) from public.cloud_resumes where user_id = new.user_id) >= 10 then
   raise exception 'Resume limit reached';
 end if;
 return new;
end $$;
create trigger cloud_resume_limit before insert on public.cloud_resumes for each row execute function public.limit_cloud_resumes();

insert into storage.buckets(id, name, public, file_size_limit, allowed_mime_types)
values ('career-resumes', 'career-resumes', false, 5242880, array['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'])
on conflict (id) do update set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;
create policy career_resume_owner on storage.objects for all to authenticated
using (bucket_id = 'career-resumes' and (storage.foldername(name))[1] = (select auth.uid())::text)
with check (bucket_id = 'career-resumes' and (storage.foldername(name))[1] = (select auth.uid())::text and name ~ '^[0-9a-f-]+/[0-9a-f-]+\.(pdf|docx)$');
