alter table public.ipos
    add column if not exists ipo_slug text;

create index if not exists idx_ipos_source_slug
    on public.ipos (source, ipo_slug);
