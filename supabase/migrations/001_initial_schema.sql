create extension if not exists pgcrypto;

create table if not exists public.ipos (
    ipo_id uuid primary key default gen_random_uuid(),
    ipo_name text not null,
    issue_price numeric(12, 2),
    lot_size integer,
    price_band text,
    ipo_type text,
    status text,
    open_date date,
    close_date date,
    allotment_date date,
    refund_date date,
    demat_date date,
    listing_date date,
    listing_price numeric(12, 2),
    issue_size numeric(14, 2),
    face_value numeric(12, 2),
    minimum_investment numeric(14, 2),
    subscription_total numeric(12, 2),
    source text not null default 'ipo_guru',
    source_updated_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.ipo_gmp_history (
    gmp_history_id uuid primary key default gen_random_uuid(),
    ipo_id uuid not null references public.ipos(ipo_id) on delete cascade,
    observation_at timestamptz not null,
    gmp numeric(12, 2),
    gmp_percent numeric(8, 2),
    estimated_listing_price numeric(12, 2),
    source text not null default 'ipo_guru',
    fetched_at timestamptz not null default now(),
    unique (ipo_id, observation_at, source)
);

create index if not exists idx_ipos_listing_date
    on public.ipos (listing_date);

create index if not exists idx_ipo_gmp_history_ipo_observation
    on public.ipo_gmp_history (ipo_id, observation_at desc);

alter table public.ipos enable row level security;
alter table public.ipo_gmp_history enable row level security;