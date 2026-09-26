-- The public Streamlit dashboard only needs to read these IPO data tables.
-- Keep its publishable/anon key read-only; ingestion uses trusted GitHub secrets.

alter table public.ipos enable row level security;
alter table public.ipo_gmp_history enable row level security;
alter table public.ipo_predictions enable row level security;
alter table public.ipo_listing_results enable row level security;

revoke all on table
    public.ipos,
    public.ipo_gmp_history,
    public.ipo_predictions,
    public.ipo_listing_results
from anon, authenticated;

grant select on table
    public.ipos,
    public.ipo_gmp_history,
    public.ipo_predictions,
    public.ipo_listing_results
to anon;

-- Replace the policies entered manually during the initial dashboard setup.
drop policy if exists "Public dashboard read" on public.ipos;
drop policy if exists "Public dashboard read" on public.ipo_gmp_history;
drop policy if exists "Public dashboard read" on public.ipo_predictions;
drop policy if exists "Public dashboard read" on public.ipo_listing_results;

create policy "IPO Pulse dashboard read"
    on public.ipos for select to anon using (true);

create policy "IPO Pulse dashboard read"
    on public.ipo_gmp_history for select to anon using (true);

create policy "IPO Pulse dashboard read"
    on public.ipo_predictions for select to anon using (true);

create policy "IPO Pulse dashboard read"
    on public.ipo_listing_results for select to anon using (true);
