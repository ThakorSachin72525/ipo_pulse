# IPO Pulse

Cloud-based IPO tracking and GMP prediction pipeline for Indian IPOs.

## Current Status

| Phase | Status | Current result |
| --- | --- | --- |
| 1. Foundation | Complete | Typed IPO, GMP, prediction, and listing-result models with tests |
| 2. IPO Guru adapter | Complete | API key, GMP endpoint, readable output, and numeric normalization |
| 3. Supabase persistence | Complete | Schema migration verified and live GitHub Actions ingestion wrote 14 IPO rows and 14 GMP observations |
| 4. Prediction pipeline | Complete | Latest pre-listing GMP selection, prediction payload logic, and live persistence are implemented and validated |
| 5. Listing accuracy | In progress | Reconciliation and sample workflows are implemented; live Supabase validation remains |
| 6. Daily report | Next | Report, accuracy summary, Gmail sender, and dry-run CLI are implemented; live delivery validation remains |
| 7. GitHub Actions automation | In progress | Added a manual and scheduled end-to-end pipeline workflow |
| 8. Dashboard | Later | Add a dashboard after the pipeline is stable |

## Goal

The system will:

- Fetch IPO and GMP data from IPO Guru.
- Store IPO metadata in Supabase PostgreSQL.
- Store each GMP observation as a separate append-only record in `ipo_gmp_history`.
- Record the GMP-based prediction used for an IPO.
- Store actual listing prices after an IPO lists.
- Calculate prediction error and direction accuracy.
- Send a daily email report through the Gmail API.
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

### Phase 5: Listing Accuracy - In progress

Deliverables:

- Reconcile listed IPOs.
- Store actual listing price.
- Calculate absolute error and percentage error.
- Calculate predicted gain, actual gain, and direction accuracy.

Current implementation:

- Added the listing-result payload builder and repository write path for storing actual-versus-predicted metrics.
- Added regression tests covering the positive and negative direction cases and the expected accuracy math.
- The reconciliation implementation is complete locally; live Supabase validation remains pending.
- Added `supabase/migrations/003_listing_results_schema.sql` for prediction outcomes.
- Added `scripts/seed_listing_accuracy_sample.py` and a manual workflow to insert one idempotent synthetic IPO, GMP observation, prediction, and listing result, all tagged with source `ipo_pulse_phase5_sample`.
- Normal report queries exclude non-IPO-Guru sources so the synthetic row does not affect production report metrics.
- Added migration `004_ipo_guru_slug.sql` so the Basic-plan detail endpoint can be queried for tracked IPOs.
- Added `scripts/reconcile_listings.py` and `.github/workflows/reconcile-listings.yml` to fetch actual listing details and store a result for every saved prediction dated before listing.
- Incomplete listing detail is skipped; saved prediction rows are not rewritten.

Completion gate:

- Positive, negative, zero, and missing-result cases are tested.
- Existing predictions are not rewritten when new GMP values arrive.
- Listing-result rows remain tied to their original prediction.
- Migrations 002-004 are applied and the manual Supabase reconciliation workflow succeeds.

Apply `supabase/migrations/002_prediction_schema.sql`, `003_listing_results_schema.sql`, and `004_ipo_guru_slug.sql` in order in the Supabase SQL Editor before running the prediction ingestion or Phase 5 workflows.

### Phase 6: Daily Report - Next

Deliverables:

- Current IPO report section.
- Recently listed IPO report section.
- Overall accuracy statistics.
- HTML/text email rendering.
- Gmail API delivery.
- Local dry-run mode.

Current implementation:

- Added a Supabase-backed report query for current GMP snapshots and recent listing results.
- Added overall direction-accuracy and mean percentage-error statistics.
- Added HTML and plain-text email delivery through the Gmail API using a Google OAuth refresh token.
- Added `python -m scripts.send_daily_report`; it prints a dry run by default and sends only with `--send`.
- Maintains recipient addresses in `config/report_recipients.txt`, one address per line; delivery sends separate messages to protect recipient privacy.
- Added tests for report data, MIME content, Gmail API delivery, and the no-send dry-run default.
- Live database and Gmail delivery validation is pending configured secrets.

Completion gate:

- Dry-run report is readable without sending email.
- Credentials are read only from environment variables or GitHub Secrets.

### Phase 7: GitHub Actions Automation - In progress

Deliverables:

- Daily scheduled workflow.
- Manual workflow dispatch.
- Secret wiring.
- Failure logging and job summary.
- Complete pipeline execution.

Current implementation:

- Added `.github/workflows/daily-pipeline.yml` with schema verification, IPO Guru ingestion, listing reconciliation, and report generation.
- Added manual dispatch with `send_report` defaulting to false, so manual validation prints a dry run without sending email.
- Added a daily `03:30 UTC` schedule that sends the report through Gmail API OAuth credentials.
- Added concurrency protection and a GitHub Actions job summary.
- IPO Guru detail requests now use bounded `Retry-After` backoff when the provider returns HTTP 429.

Completion gate:

- Manual run succeeds end to end.
- Second run is idempotent.
- Scheduled workflow is enabled only after manual validation.
- Manual dry-run pipeline succeeds on the default branch.
- Scheduled or manual-send pipeline succeeds after listing reconciliation is no longer blocked by provider throttling.

### Phase 8: Dashboard - Later

Possible views:

- Current IPO overview.
- GMP history.
- Predicted versus actual listing price.
- Historical accuracy statistics.

Dashboard technology will be selected after the cloud pipeline is stable.

## Secrets

Current secret:

- `IPO_API_KEY`

Later secrets:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `EMAIL_SENDER`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REFRESH_TOKEN`

Secrets belong in GitHub repository settings under **Settings → Secrets and variables → Actions**. They must not be committed to the repository.
Recipient addresses are maintained in the tracked file `config/report_recipients.txt`, one per line. Edit and commit that file when the list changes; it is not an Actions secret.
The sender address identifies the Gmail mailbox; the Gmail API uses the OAuth refresh token, not the mailbox password. Google can revoke refresh tokens, so reauthorization may occasionally be needed.

## Google OAuth Setup

1. In Google Cloud Console, create a project, enable the Gmail API, and configure the OAuth consent screen.
2. Create an OAuth client. For OAuth Playground, use a Web application client and add `https://developers.google.com/oauthplayground` as an authorized redirect URI.
3. Open Google OAuth Playground settings, select **Use your own OAuth credentials**, and enter the client ID and client secret.
4. Authorize the scope `https://mail.google.com/` using the mailbox in `EMAIL_SENDER`, then exchange the authorization code for tokens. Keep the refresh token; the access token is short-lived and is fetched by the app when sending.
5. Add `EMAIL_SENDER`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `GOOGLE_OAUTH_REFRESH_TOKEN` as repository Actions secrets.
6. For an external OAuth consent screen, publish the app as required for long-lived refresh tokens. Google Testing mode may expire refresh tokens after seven days; restricted Gmail scopes may also require verification.

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