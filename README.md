# IPO Pulse

Cloud-based IPO tracking and GMP prediction pipeline for Indian IPOs.

## Current Status

| Phase | Status | Current result |
| --- | --- | --- |
| 1. Foundation | Complete | Typed IPO, GMP, prediction, and listing-result models with tests |
| 2. IPO Guru adapter | Complete | API key, GMP endpoint, readable output, and numeric normalization |
| 3. Supabase persistence | Complete | Schema migration verified and live GitHub Actions ingestion wrote 14 IPO rows and 14 GMP observations |
| 4. Prediction pipeline | Complete | Latest pre-listing GMP selection, prediction payload logic, and live persistence are implemented and validated |
| 5. Listing accuracy | Validation queued | Reconciliation completed without throttling; no listed IPOs were eligible for real outcomes yet |
| 6. Daily email dashboard | In progress | SMTP App Password delivery implemented; confirm a manual test email arrives and renders correctly |
| 7. GitHub Actions automation | Validation queued | Updated to 7:00 AM IST; validate the new SMTP delivery in the manual report workflow |
| 8. Dashboard | Complete | Deployed dashboard reads IPO Guru data through the versioned read-only Supabase policies |

## Goal

The system will:

- Fetch IPO and GMP data from IPO Guru.
- Store IPO metadata in Supabase PostgreSQL.
- Store each GMP observation as a separate append-only record in `ipo_gmp_history`.
- Record the GMP-based prediction used for an IPO.
- Store actual listing prices after an IPO lists.
- Calculate prediction error and direction accuracy.
- Send a daily dashboard email through Gmail SMTP with a Google App Password.
- Run automatically through GitHub Actions.

GMP is treated as a prediction input, not as a guaranteed listing price.

## Phase Plan

### Phase 1: Foundation - Complete

Deliverables:

- Typed domain models in `app/models/ipo_model.py`.
- Environment-based configuration in `app/config.py`.
- Prediction and listing-result formulas.
- Focused tests for the domain calculations.

Completion gate:

- Local tests pass.
- No credentials are stored in source code.

### Phase 2: IPO Guru API Adapter - Complete

Deliverables:

- IPO Guru client using `X-API-KEY`.
- GMP endpoint integration: `/api/v2/gmp?status=open`.
- Readable inspection script in `scripts/inspect_ipo_guru.py`.
- Numeric normalization for issue price, GMP, GMP percentage, and estimated listing price.
- Manual GitHub Actions API smoke test.

Current API limitation:

- The list endpoint currently used is `GET /api/v2/gmp?status=open`. It provides IPO name, issue price, price band, status, GMP, GMP percentage, and estimated listing price.
- The documented detail endpoint is `GET /api/v2/ipos/{slug}`. It provides open/close/allotment/refund/demat/listing dates, lot size, issue size, face value, minimum investment, exchanges, subscription summary, and listing information including actual listing price and listing gain percentage when available.
- The documented current-GMP endpoint is `GET /api/v2/ipos/{slug}/gmp`.
- We will use the Basic plan only. The `/{slug}` detail endpoint is the source for full IPO details, including lot size, IPO dates, listing date, subscription summary, and listing information when available.
- We will not call the paid `GET /api/v2/ipos/{slug}/gmp/history` endpoint. The daily pipeline will fetch the current GMP and append one dated observation to Supabase each day; our database will become the GMP history source.
- Standard/Pro-only day-wise or intraday GMP history and subscription-history endpoints are out of scope unless the project plan changes.
- We must not guess unavailable values. A missing Basic-plan field is stored as null and reported for later review.

Completion gate:

- Local API inspection succeeds.
- GitHub Actions API inspection succeeds.
- Response values are mapped without guessing unavailable fields.

### Phase 3: Supabase Persistence - Complete

Deliverables:

- Versioned SQL migration for `ipos`.
- Versioned SQL migration for `ipo_gmp_history`.
- Initial migration: `supabase/migrations/001_initial_schema.sql`.
- Repository for IPO upserts.
- Append-only GMP observation storage.
- Daily GMP snapshots from the Basic-plan current-GMP response.
- IPO Pulse-owned UUID identity in `ipos.ipo_id`.
- Same IPO/timestamp/source operation is idempotent.
- Previous GMP observations are never overwritten.
- Read-only GitHub Actions schema check in `.github/workflows/test-supabase.yml`.
- Manual ingestion workflow in `.github/workflows/ingest-ipo-guru.yml`.

Completion gate:

- Migrations apply successfully in Supabase.
- The manual Supabase workflow verifies both tables using `SUPABASE_URL` and `SUPABASE_KEY`.
- The manual ingestion workflow upserts IPO metadata and appends current GMP observations using all three configured secrets.
- Repository tests cover insert, update, duplicate, and historical-record behavior.
- A repeated daily run does not create duplicate GMP observations.
- Live validation passed: the GitHub Actions ingestion run wrote 14 IPO rows and 14 GMP observations.

### Phase 4: Prediction Pipeline - Complete

Deliverables:

- Select the latest pre-listing GMP observation.
- Calculate expected listing price.
- Calculate expected investment, profit, and return.
- Persist the prediction and the GMP observation used.

Current implementation:

- Added `latest_pre_listing_gmp()` to choose the newest GMP before the IPO listing date.
- Added a prediction payload builder for the GMP-backed prediction record.
- Added `supabase/migrations/002_prediction_schema.sql` for persisted predictions.
- Added the live ingestion write path to call `upsert_prediction()` with the exact `gmp_history_id` it was derived from.
- Prediction ingestion skips missing/non-positive issue prices and GMP observations on or after the listing date.
- Added regression tests covering the latest-GMP selection, expected-value formulas, and live prediction persistence.

Completion gate:

- Formula tests pass with known values.
- Historical predictions remain tied to their original GMP observation.
- Live ingestion writes a prediction row for each GMP snapshot it persists.

### Phase 5: Listing Accuracy - Validation queued

Deliverables:

- Reconcile listed IPOs.
- Store actual listing price.
- Calculate absolute error and percentage error.
- Calculate predicted gain, actual gain, and direction accuracy.

Current implementation:

- Added the listing-result payload builder and repository write path for storing actual-versus-predicted metrics.
- Added regression tests covering the positive and negative direction cases and the expected accuracy math.
- The reconciliation implementation is complete locally; live Supabase validation remains pending. It skips IPOs whose listing date is unknown or in the future, uses stored listing prices when available, and requests detail only for listed IPOs that still need an actual price.
- Added `supabase/migrations/003_listing_results_schema.sql` for prediction outcomes.
- Removed the temporary synthetic Phase 5 database record and its related rows after using it to validate the IPO/GMP/prediction/result relationship. The dashboard now reads only IPO Guru production rows.
- Added migration `004_ipo_guru_slug.sql` so the Basic-plan detail endpoint can be queried for tracked IPOs.
- Added `scripts/reconcile_listings.py` and `.github/workflows/reconcile-listings.yml` to fetch actual listing details and store a result for every saved prediction dated before listing.
- Incomplete listing detail is skipped; saved prediction rows are not rewritten.

Completion gate:

- Positive, negative, zero, and missing-result cases are tested.
- Existing predictions are not rewritten when new GMP values arrive.
- Listing-result rows remain tied to their original prediction.
- Migrations 002-004 are applied and the manual Supabase reconciliation workflow succeeds.

Apply `supabase/migrations/002_prediction_schema.sql`, `003_listing_results_schema.sql`, and `004_ipo_guru_slug.sql` in order in the Supabase SQL Editor before running prediction ingestion or listing reconciliation.

### Phase 6: Daily Email Dashboard - In progress

Deliverables:

- Current IPO overview and recent listing outcomes.
- Overall accuracy statistics.
- Dashboard-style HTML email with a link to the live Streamlit dashboard.
- Inline PNG snapshot of the same dashboard data.
- Plain-text email fallback.
- Gmail SMTP delivery over SSL with a Google App Password.
- Local dry-run mode.

Current implementation:

- Added a Supabase-backed report query for current GMP snapshots and recent listing results.
- Added overall direction-accuracy and mean percentage-error statistics.
- Added a dashboard-style HTML email with KPI cards, IPO and listing tables, an inline PNG snapshot, a live-dashboard link, and a plain-text fallback. The user confirmed the Gmail rendering. Delivery now uses Gmail SMTP with an App Password; SMTP delivery still needs a manual validation run.
- Added `python -m scripts.send_daily_report`; it prints a dry run by default and sends only with `--send`.
- Reads the single report recipient from the `GMAIL_RECIPIENT` environment variable or GitHub Actions secret.
- Added tests for report data, MIME content, Gmail SMTP delivery, and the no-send dry-run default.
- Supabase report data and the email layout were previously validated. Validate the new SMTP delivery using the manual report workflow.

Completion gate:

- Dry-run output is readable without sending email.
- The user confirmed that a delivered test email renders the dashboard layout correctly and opens the live Streamlit dashboard. Confirm a report sent through Gmail SMTP.
- Credentials are read only from environment variables or GitHub Secrets.

### Phase 7: GitHub Actions Automation - Validation queued

Deliverables:

- Daily scheduled workflow.
- Manual workflow dispatch.
- Secret wiring.
- Failure logging and job summary.
- Complete pipeline execution.

Current implementation:

- Added `.github/workflows/daily-pipeline.yml` with schema verification, IPO Guru ingestion, listing reconciliation, and report generation.
- Added manual dispatch with `send_report` defaulting to false, so manual validation prints a dry run without sending email.
- Updated the daily schedule to `01:30 UTC` (7:00 AM IST) for the report pipeline. Full manual send and dry-run pipeline runs succeeded on `main` (runs `36271478502` and `36271608004`). The repeat ingestion returned the same 14 IPOs, 14 GMP observations, and 14 predictions without error.
- Added concurrency protection and a GitHub Actions job summary. Added `.github/workflows/test-schedule.yml` and `schedule.py` as an isolated schedule diagnostic. Its manual run succeeded, but GitHub created no schedule run across three expected five-minute ticks; the diagnostic workflow is disabled to avoid unnecessary Actions usage. The production workflow later ran with event `schedule` on Sep 27 at 5:39 PM IST (run `36318032760`) and Sep 28 at 7:34 PM IST (run `36433230260`), far after its previous configured 11:50 AM IST time. More recent Oct 3–7 scheduled runs also started 5–8 hours late and failed while exchanging the old Gmail OAuth refresh token (Google token endpoint HTTP 400); ingestion and reconciliation succeeded. The sender has since moved to Gmail SMTP and requires a new manual delivery check.
- IPO Guru detail requests now use bounded `Retry-After` backoff when the provider returns HTTP 429.

Completion gate:

- Full manual send pipeline succeeds on the default branch.
- Repeated ingestion succeeds with the same source rows.
- Daily schedule is configured for 7:00 AM IST (`01:30 UTC`); GitHub has previously delayed scheduled events by hours, so punctual schedule validation remains open. Historical runs failed during the now-removed Gmail OAuth token refresh; validate the SMTP delivery path.
- Manual dry-run pipeline succeeds on the default branch.
- GitHub creates scheduled runs for the diagnostic workflow when enabled.

### Phase 8: Dashboard - Complete

Current implementation:

- Added `dashboard.py` as a read-only Streamlit dashboard.
- Added current IPO overview, GMP history chart, prediction history chart, and predicted-versus-actual listing results.
- Added direction accuracy and mean percentage error metrics.
- Dashboard data is restricted to IPO Guru production rows.
- The dashboard never writes to Supabase.
- Live validation completed: Streamlit Community Cloud reads IPO records from Supabase using migration 005.

Run locally with:

```bash
SUPABASE_URL=... SUPABASE_KEY=... uv run streamlit run dashboard.py
```

Deploy with Streamlit Community Cloud:

1. Select the repository and branch to deploy.
2. Set the main file to `dashboard.py`.
3. Add these values in the app's **Secrets** panel using TOML syntax:

```toml
SUPABASE_URL = "..."
SUPABASE_KEY = "..."
```

4. Keep the app on the read-only dashboard path; it never writes to Supabase.

Apply `supabase/migrations/005_dashboard_read_policies.sql` after migrations 001-004. It grants the unauthenticated `anon` role read-only access to the four dashboard tables. This makes dashboard data publicly readable, so the Streamlit app must use the publishable/anon key, never a Supabase secret/service-role key.

The dashboard remains read-only. The email contains a point-in-time visual summary and links to the interactive dashboard.

## GitHub Actions Secrets

Configure these repository secrets under **Settings → Secrets and variables → Actions**:

- `IPO_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GMAIL_SENDER`
- `GMAIL_APP_PASSWORD`
- `GMAIL_RECIPIENT`

`GMAIL_SENDER` must be the Gmail account that created the App Password. `GMAIL_RECIPIENT` is the single recipient for the daily report. Keep the App Password in GitHub Secrets; never commit it or print it in logs.

## Gmail SMTP Setup

1. Turn on 2-Step Verification for the Gmail sender account.
2. In the Google Account security settings, create an App Password for IPO Pulse.
3. Save the Gmail address as `GMAIL_SENDER`, the generated App Password as `GMAIL_APP_PASSWORD`, and the report destination as `GMAIL_RECIPIENT` in GitHub Actions Secrets.
4. Use **Actions → Send Daily IPO Dashboard → Run workflow**. Leave `send` unchecked for a dry run; check it to send one live report to `GMAIL_RECIPIENT`.

The app sends through `smtp.gmail.com` over SSL on port 465. It strips whitespace from the App Password in memory to accommodate Google's grouped display format. The App Password is not stored in the repository.

## Development Checks

Run the local checks with:

```bash
PYTHONPATH=. uv run pytest -q
uv run python -m compileall -q app scripts
```

Before marking a phase complete:

1. Implement only that phase's deliverables.
2. Add the smallest runnable check for the new behavior.
3. Run the phase's validation gate.
4. Update the status table and completion gate in this README.
5. Commit the phase separately.