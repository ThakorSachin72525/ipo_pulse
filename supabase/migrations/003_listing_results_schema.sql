create table if not exists public.ipo_listing_results (
    listing_result_id uuid primary key default gen_random_uuid(),
    ipo_id uuid not null references public.ipos(ipo_id) on delete cascade,
    prediction_id uuid not null references public.ipo_predictions(prediction_id) on delete cascade,
    actual_listing_price numeric(12, 2),
    predicted_listing_price numeric(12, 2),
    actual_gain_percent numeric(8, 2),
    prediction_error numeric(12, 2),
    percentage_error numeric(8, 2),
    direction_accuracy boolean not null,
    created_at timestamptz not null default now(),
    unique (ipo_id, prediction_id)
);

create index if not exists idx_ipo_listing_results_ipo_created
    on public.ipo_listing_results (ipo_id, created_at desc);

alter table public.ipo_listing_results enable row level security;
