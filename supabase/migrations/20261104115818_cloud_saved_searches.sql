create table public.cloud_saved_searches (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    q text not null check (char_length(q) <= 120),
    location text not null check (char_length(location) <= 100),
    remote boolean not null,
    created_at timestamptz not null default now(),
    unique (user_id, q, location, remote)
);

alter table public.cloud_saved_searches enable row level security;
create policy owner_only on public.cloud_saved_searches for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

grant select, insert, delete on public.cloud_saved_searches to authenticated;
revoke all on public.cloud_saved_searches from anon;
