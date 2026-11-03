-- Run as a Supabase database administrator, after migrations:
-- psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/tests/cloud_rls.sql
-- All fixture data is rolled back. Failures abort the transaction.
begin;
insert into auth.users(id, email) values
 ('11111111-1111-4111-8111-111111111111', 'cloud-rls-a@example.invalid'),
 ('22222222-2222-4222-8222-222222222222', 'cloud-rls-b@example.invalid');
insert into public.cloud_profiles(user_id,data) values
 ('11111111-1111-4111-8111-111111111111', '{"full_name":"A"}'),
 ('22222222-2222-4222-8222-222222222222', '{"full_name":"B"}');
insert into public.cloud_jobs(id,user_id,title) values
 ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111','A job'),
 ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','22222222-2222-4222-8222-222222222222','B job');
set local role authenticated;
select set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
do $$
declare affected integer;
begin
 if (select count(*) from public.cloud_profiles) <> 1 then raise exception 'Profile read isolation failed'; end if;
 if (select count(*) from public.cloud_jobs) <> 1 then raise exception 'Job read isolation failed'; end if;
 update public.cloud_jobs set title='stolen' where id='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
 get diagnostics affected = row_count;
 if affected <> 0 then raise exception 'Cross-owner update allowed'; end if;
 delete from public.cloud_jobs where id='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
 get diagnostics affected = row_count;
 if affected <> 0 then raise exception 'Cross-owner delete allowed'; end if;
 begin
  insert into public.cloud_jobs(user_id,title) values ('22222222-2222-4222-8222-222222222222','forged');
  raise exception 'Cross-owner insert allowed';
 exception when insufficient_privilege then null;
 end;
 update public.cloud_profiles set data='{"full_name":"A updated"}' where user_id=auth.uid();
 if not found then raise exception 'Owner update denied'; end if;
end $$;
select set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
do $$
begin
 if (select count(*) from public.cloud_jobs) <> 1 or (select title from public.cloud_jobs limit 1) <> 'B job' then
  raise exception 'Second-user isolation failed';
 end if;
 if (select data->>'full_name' from public.cloud_profiles limit 1) <> 'B' then raise exception 'Second profile isolation failed'; end if;
end $$;
rollback;
