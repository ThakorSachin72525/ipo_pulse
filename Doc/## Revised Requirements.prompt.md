## Revised Requirements

Build an automation-first IPO tracking system:

- Fetch IPO and GMP data from IPO Guru.
- Use the IPO Guru Basic plan for the available IPO detail and current GMP fields.
- Store IPO metadata in Supabase PostgreSQL.
- Store GMP observations as append-only records in `ipo_gmp_history`.
- Build our own day-wise GMP history from daily snapshots; do not depend on the paid GMP-history endpoint.
- Record GMP-based predictions before listing.
- Store actual listing prices after listing.
- Calculate prediction errors and direction accuracy.
- Generate and email a dashboard-style HTML email with an inline PNG snapshot and link to the live Streamlit dashboard; retain a plain-text fallback. Send through Gmail SMTP using an App Password stored in GitHub Actions Secrets.
- Run automatically through GitHub Actions.
- Keep all credentials in GitHub Actions Secrets.
- Store `GMAIL_SENDER`, `GMAIL_APP_PASSWORD`, and `GMAIL_RECIPIENT` in GitHub Actions Secrets; never commit or log the App Password.
- Defer the existing PySide6 interface until the cloud pipeline is stable.

The existing PySide6 app remains operational but is not expanded during the initial pipeline phases.

## Development Plan

1. **Foundation**
   - Replace the sample model with typed IPO, GMP, prediction, and result models.
   - Add environment-based configuration.
   - Add pytest and initial unit tests.
   - No external credentials required.

2. **IPO Guru API Integration**
   - Build an API provider adapter.
   - Validate response fields, dates, prices, GMP, and missing data.
   - Use the Basic-plan IPO detail endpoint for lot size, dates, listing information, and other available fields.
   - Do not require Standard/Pro-only GMP history endpoints.
   - Add sanitized response fixtures and API error tests.

3. **Supabase Database**
   - Current status: Complete. The initial schema migration is `supabase/migrations/001_initial_schema.sql` and it has passed live GitHub Actions validation.
   - Add migrations for:
     - `ipos`
   - `ipo_gmp_history`
     - prediction records
     - evaluation results
   - Preserve GMP history without overwriting previous observations.
   - Append one daily GMP snapshot from the current GMP endpoint.
   - Add idempotent repository operations.
   - Add a read-only manual workflow to verify the Supabase connection and required tables.
   - Add a manual ingestion workflow that upserts IPO metadata and appends current GMP observations.
   - Live validation result: the ingestion workflow successfully wrote 14 IPO rows and 14 GMP observations to Supabase.

4. **Prediction Engine**
   - Current status: Complete. The latest pre-listing GMP selection, prediction payload logic, and live persistence path are implemented and validated locally.
   - Ignore GMP rows for other IPOs, and do not create predictions for invalid issue prices or dates on/after listing.
   - Calculate expected listing price, investment, profit, return, and predicted gain.
   - Store the GMP observation used for each prediction.

5. **Listing Accuracy**
   - Current status: Live result validation is pending. Listing detail fetching, persisted slug lookup, and per-prediction outcome reconciliation are implemented; reconciliation skips IPOs not yet listed and avoids detail requests when the stored listing price is available.
   - Keep synthetic Phase 5 rows out of the production database and dashboard. The temporary tagged validation record has been removed; wait for real IPO listings to validate live outcome accuracy.
   - Fetch actual listing price from the IPO Guru Basic-plan detail endpoint using each saved IPO slug.
   - Store a result for every saved prediction dated before listing without rewriting prediction records.
   - Add migrations for prediction rows, listing outcomes, and the IPO Guru slug; apply them in order before reconciliation.
   - Record actual listing prices.
   - Calculate absolute error, percentage error, actual gain, and direction accuracy.
   - Handle missing GMP or missing listing data safely.

6. **Daily Email Dashboard**
   - Current status: In progress. The dashboard-style HTML email, inline PNG snapshot, live Streamlit link, and plain-text fallback are implemented. Gmail SMTP with an App Password replaces Gmail API OAuth; validate a live test delivery.
   - Read `GMAIL_SENDER`, `GMAIL_APP_PASSWORD`, and `GMAIL_RECIPIENT` from environment variables or GitHub Actions Secrets. The sender must be the Gmail account that generated the App Password.
   - Use SMTP over SSL with `smtp.gmail.com` on port 465. Never commit or log the App Password.
   - Show current IPOs, recent listing outcomes, and overall statistics in the email dashboard.
   - Link the email to the interactive Streamlit dashboard.
   - Add Gmail SMTP delivery over SSL using the Google App Password.
   - Include a local dry-run mode.

7. **GitHub Actions**
   - Current status: Validation queued. Full manual send and dry-run pipeline runs succeeded on `main` (runs `36271478502` and `36271608004`); repeated ingestion returned the same 14 IPOs, GMP observations, and predictions. The daily schedule is now configured for 7:00 AM IST (`01:30 UTC`). Production scheduled runs have arrived hours late. Oct 3–7 runs also failed while exchanging the Gmail OAuth refresh token (HTTP 400); schema verification, IPO Guru ingestion, and listing reconciliation succeeded. The diagnostic script passed on manual dispatch but saw no event across three five-minute cron ticks; its frequent schedule is disabled. Investigate schedule delays and reauthorize Gmail OAuth.
   - Schedule the pipeline daily at 7:00 AM IST (`01:30 UTC`).
   - Add manual dispatch.
   - Wire secrets securely.
   - Add logging and failure reporting.
   - Keep the end-to-end workflow blocked on provider rate limits until the reconciliation run is confirmed.

8. **Dashboard**
   - Current status: Complete. The read-only Streamlit dashboard is deployed and reads Supabase data through migration 005.
   - Use Streamlit rather than extending the deferred PySide6 interface.
   - Add IPO overview, GMP history, actual-versus-predicted views, and charts.
   - Deploy through Streamlit Community Cloud with `SUPABASE_URL` and `SUPABASE_KEY` configured as app secrets.

## First Step

We begin with the foundation in [app/models/ipo_model.py](app/models/ipo_model.py), configuration, and tests. The existing [app/services/ipo_service.py](app/services/ipo_service.py) will remain a compatibility boundary while the domain model becomes real.

Verification will be limited to local tests and import/type checks. No database, API, or email credentials are needed yet.

The complete persistent plan is recorded in `/memories/session/plan.md`.

Reply with approval to begin Step 1.
