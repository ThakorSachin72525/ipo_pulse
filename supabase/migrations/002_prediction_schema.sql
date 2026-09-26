create table if not exists public.ipo_predictions (
    prediction_id uuid primary key default gen_random_uuid(),
    ipo_id uuid not null references public.ipos(ipo_id) on delete cascade,
    gmp_history_id uuid not null references public.ipo_gmp_history(gmp_history_id) on delete cascade,
    gmp_value numeric(12, 2),
    gmp_percent numeric(8, 2),
    issue_price numeric(12, 2),
    lot_size integer,
    expected_listing_price numeric(12, 2),
    expected_profit numeric(14, 2),
    expected_return numeric(8, 2),
    source text not null default 'ipo_guru',
    gmp_date date not null,
    created_at timestamptz not null default now(),
    unique (ipo_id, gmp_history_id, source)
);

create index if not exists idx_ipo_predictions_ipo_created
    on public.ipo_predictions (ipo_id, created_at desc);

alter table public.ipo_predictions enable row level security;
