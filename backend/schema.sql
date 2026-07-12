-- CounselAI — Supabase schema (source of truth; run in the SQL Editor).
-- Idempotent: safe to run repeatedly. Mirrors what the backend code reads/writes.
--
-- Tables: workspaces, workspace_members, documents, document_chunks
-- Plus: auto-provision trigger (workspace + membership on signup).
-- RLS: enabled with policies; the backend uses the SERVICE ROLE key which
--      bypasses RLS, so these policies protect any direct client access.

-- ============================================================ TENANCY
create table if not exists workspaces (
  id         uuid primary key default gen_random_uuid(),
  name       text not null default 'My Workspace',
  created_at timestamptz not null default now()
);

create table if not exists workspace_members (
  workspace_id uuid not null references workspaces(id) on delete cascade,
  user_id      uuid not null references auth.users(id) on delete cascade,
  role         text not null default 'owner',
  created_at   timestamptz not null default now(),
  primary key (workspace_id, user_id)
);
create index if not exists idx_members_user on workspace_members(user_id);

-- ============================================================ DOCUMENTS
create table if not exists documents (
  id             uuid primary key default gen_random_uuid(),
  workspace_id   uuid not null references workspaces(id) on delete cascade,
  uploaded_by    uuid references auth.users(id),
  filename       text not null,
  storage_path   text not null,
  status         text not null default 'processing',  -- processing | ready | failed
  page_count     int,
  chunk_count    int,
  ocr_page_count int,
  error          text,
  created_at     timestamptz not null default now()
);
create index if not exists idx_docs_ws on documents(workspace_id);

-- Backfill columns if the table pre-existed without them:
alter table documents add column if not exists page_count     int;
alter table documents add column if not exists chunk_count    int;
alter table documents add column if not exists ocr_page_count int;
alter table documents add column if not exists error          text;

-- ============================================================ CHUNKS
-- NOTE: the ingest worker writes `content` (not `chunk_text`). If an older
-- `chunk_text NOT NULL` column exists, drop it — `content` is the source of truth.
create table if not exists document_chunks (
  id           uuid primary key default gen_random_uuid(),
  document_id  uuid not null references documents(id) on delete cascade,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  chunk_index  int  not null,
  page_number  int  not null,
  content      text not null,
  created_at   timestamptz not null default now()
);
create index if not exists idx_chunks_doc on document_chunks(document_id);

alter table document_chunks add column if not exists content text;
alter table document_chunks drop column if exists chunk_text;

-- ============================================================ AUTO-PROVISION
-- Every new auth user gets a workspace + owner membership, so get_current_user
-- can always resolve a workspace_id (otherwise every request 403s).
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
declare ws_id uuid;
begin
  insert into workspaces (name) values ('My Workspace') returning id into ws_id;
  insert into workspace_members (workspace_id, user_id, role)
    values (ws_id, new.id, 'owner');
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================================ RLS
alter table workspaces        enable row level security;
alter table workspace_members enable row level security;
alter table documents         enable row level security;
alter table document_chunks   enable row level security;

-- Members can see their own membership rows.
drop policy if exists members_self on workspace_members;
create policy members_self on workspace_members
  for select using (user_id = auth.uid());

-- Users can read workspaces they belong to.
drop policy if exists ws_member_read on workspaces;
create policy ws_member_read on workspaces
  for select using (
    exists (select 1 from workspace_members m
            where m.workspace_id = workspaces.id and m.user_id = auth.uid())
  );

-- Users can read documents in their workspaces.
drop policy if exists docs_member_read on documents;
create policy docs_member_read on documents
  for select using (
    exists (select 1 from workspace_members m
            where m.workspace_id = documents.workspace_id and m.user_id = auth.uid())
  );

-- Users can read chunks in their workspaces.
drop policy if exists chunks_member_read on document_chunks;
create policy chunks_member_read on document_chunks
  for select using (
    exists (select 1 from workspace_members m
            where m.workspace_id = document_chunks.workspace_id and m.user_id = auth.uid())
  );

notify pgrst, 'reload schema';
