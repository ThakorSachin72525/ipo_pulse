# IPO Pulse

Cloud-based IPO tracking and GMP prediction pipeline for Indian IPOs.

## Current Status

| Phase | Status | Current result |
| --- | --- | --- |
| 1. Foundation | Complete | Typed IPO, GMP, prediction, and listing-result models with tests |
| 2. IPO Guru adapter | Complete | API key, GMP endpoint, readable output, and numeric normalization |
| 3. Supabase persistence | In progress | Initial schema migration created; apply and validate in Supabase |
| 4. Prediction pipeline | Not started | Persist predictions from daily GMP observations |
| 5. Listing accuracy | Not started | Compare predictions with actual listing prices |
| 6. Daily report | Not started | Build and send the email report |
| 7. GitHub Actions automation | Not started | Schedule and run the complete daily pipeline |
| 8. Dashboard | Later | Add a dashboard after the pipeline is stable |

## Goal

The system will:

- Fetch IPO and GMP data from IPO Guru.
- Store IPO metadata in Supabase PostgreSQL.
- Store each GMP observation as a separate append-only record in `ipo_gmp_history`.
- Record the GMP-based prediction used for an IPO.
- Store actual listing prices after an IPO lists.
- Calculate prediction error and direction accuracy.
- Send a daily email report through Gmail SMTP.
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

### Phase 3: Supabase Persistence - In progress

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

Completion gate:

- Migrations apply successfully in Supabase.
- The manual Supabase workflow verifies both tables using `SUPABASE_URL` and `SUPABASE_KEY`.
- Repository tests cover insert, update, duplicate, and historical-record behavior.
- A repeated daily run does not create duplicate GMP observations.

### Phase 4: Prediction Pipeline - Not Started

Deliverables:

- Select the latest pre-listing GMP observation.
- Calculate expected listing price.
- Calculate expected investment, profit, and return.
- Persist the prediction and the GMP observation used.

Completion gate:

- Formula tests pass with known values.
- Historical predictions remain tied to their original GMP observation.

### Phase 5: Listing Accuracy - Not Started

Deliverables:

- Reconcile listed IPOs.
- Store actual listing price.
- Calculate absolute error and percentage error.
- Calculate predicted gain, actual gain, and direction accuracy.

Completion gate:

- Positive, negative, zero, and missing-result cases are tested.
- Existing predictions are not rewritten when new GMP values arrive.

### Phase 6: Daily Report - Not Started

Deliverables:

- Current IPO report section.
- Recently listed IPO report section.
- Overall accuracy statistics.
- HTML/text email rendering.
- Gmail SMTP delivery.
- Local dry-run mode.

Completion gate:

- Dry-run report is readable without sending email.
- Credentials are read only from environment variables or GitHub Secrets.

### Phase 7: GitHub Actions Automation - Not Started

Deliverables:

- Daily scheduled workflow.
- Manual workflow dispatch.
- Secret wiring.
- Failure logging and job summary.
- Complete pipeline execution.

Completion gate:

- Manual run succeeds end to end.
- Second run is idempotent.
- Scheduled workflow is enabled only after manual validation.

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
- `EMAIL_USERNAME`
- `EMAIL_PASSWORD`

Secrets belong in GitHub repository settings under **Settings → Secrets and variables → Actions**. They must not be committed to the repository.

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