-- Nossa Carteira — esquema do banco (rode no Supabase: SQL Editor > New query > cole tudo > Run)

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  ativos text[] not null default '{}',
  perfil jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.purchases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  ticker text not null,
  quantidade numeric not null check (quantidade > 0),
  preco numeric not null check (preco > 0),
  data date not null,
  nota text,
  created_at timestamptz not null default now()
);
create index if not exists purchases_user_idx on public.purchases(user_id);

create table if not exists public.quotes (
  ticker text primary key,
  nome text,
  preco numeric,
  var_dia numeric,
  var_semana numeric,
  var_mes numeric,
  ultimo_pregao date,
  historico jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.summary (
  id text primary key,
  data jsonb,
  updated_at timestamptz not null default now()
);

-- Row Level Security
alter table public.profiles  enable row level security;
alter table public.purchases enable row level security;
alter table public.quotes    enable row level security;
alter table public.summary   enable row level security;

-- profiles: qualquer pessoa logada lê todos; cada um escreve só o seu
drop policy if exists "profiles_read"   on public.profiles;
drop policy if exists "profiles_insert" on public.profiles;
drop policy if exists "profiles_update" on public.profiles;
create policy "profiles_read"   on public.profiles for select to authenticated using (true);
create policy "profiles_insert" on public.profiles for insert to authenticated with check (id = auth.uid());
create policy "profiles_update" on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- purchases: todos logados leem; cada um escreve/apaga só as suas
drop policy if exists "purchases_read"   on public.purchases;
drop policy if exists "purchases_insert" on public.purchases;
drop policy if exists "purchases_update" on public.purchases;
drop policy if exists "purchases_delete" on public.purchases;
create policy "purchases_read"   on public.purchases for select to authenticated using (true);
create policy "purchases_insert" on public.purchases for insert to authenticated with check (user_id = auth.uid());
create policy "purchases_update" on public.purchases for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "purchases_delete" on public.purchases for delete to authenticated using (user_id = auth.uid());

-- quotes e summary: todos logados leem; só o robô (service key, que ignora RLS) escreve
drop policy if exists "quotes_read"  on public.quotes;
drop policy if exists "summary_read" on public.summary;
create policy "quotes_read"  on public.quotes  for select to authenticated using (true);
create policy "summary_read" on public.summary for select to authenticated using (true);

-- Realtime (para a tela atualizar sozinha quando o outro registra algo)
do $$ begin
  alter publication supabase_realtime add table public.profiles;
exception when duplicate_object then null; end $$;
do $$ begin
  alter publication supabase_realtime add table public.purchases;
exception when duplicate_object then null; end $$;
do $$ begin
  alter publication supabase_realtime add table public.quotes;
exception when duplicate_object then null; end $$;
do $$ begin
  alter publication supabase_realtime add table public.summary;
exception when duplicate_object then null; end $$;
