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
- Generate and email daily reports through the Gmail API.
- Run automatically through GitHub Actions.
- Keep all credentials in GitHub Actions Secrets.
- Maintain report recipient addresses in the tracked file `config/report_recipients.txt`; store Google OAuth client credentials and refresh token in GitHub Actions Secrets, never the mailbox password.
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
   - Current status: In progress. Listing detail fetching, persisted slug lookup, and per-prediction outcome reconciliation are implemented and locally tested; live Supabase validation remains.
   - Add a manually dispatched, repeatable synthetic database sample tagged `ipo_pulse_phase5_sample` to validate the IPO/GMP/prediction/result relationship.
   - Fetch actual listing price from the IPO Guru Basic-plan detail endpoint using each saved IPO slug.
   - Store a result for every saved prediction dated before listing without rewriting prediction records.
   - Add migrations for prediction rows, listing outcomes, and the IPO Guru slug; apply them in order before reconciliation.
   - Record actual listing prices.
   - Calculate absolute error, percentage error, actual gain, and direction accuracy.
   - Handle missing GMP or missing listing data safely.

6. **Daily Email Report**
   - Current status: Next. Supabase-backed report data, overall accuracy summary, HTML/text email composition, Gmail API sender using Google OAuth refresh tokens, and dry-run CLI are implemented and tested locally; live credential-backed delivery validation remains.
   - Maintain recipient addresses in `config/report_recipients.txt`, one per line, and send separate messages per recipient.
   - Generate a Gmail-scoped refresh token with offline access; do not store the mailbox password.
   - Generate current IPO, historical result, and overall statistics sections.
   - Add Gmail API delivery.
   - Include a local dry-run mode.

7. **GitHub Actions**
   - Current status: In progress. Added `.github/workflows/daily-pipeline.yml` with manual dry-run, manual send, and a daily schedule.
   - Add daily scheduling.
   - Add manual dispatch.
   - Wire secrets securely.
   - Add logging and failure reporting.
   - Keep the end-to-end workflow blocked on provider rate limits until the reconciliation run is confirmed.

8. **Dashboard Later**
   - Current status: In progress. A read-only Streamlit dashboard is implemented.
   - Use Streamlit rather than extending the deferred PySide6 interface.
   - Add IPO overview, GMP history, actual-versus-predicted views, and charts.
   - Deploy through Streamlit Community Cloud with `SUPABASE_URL` and `SUPABASE_KEY` configured as app secrets.

## First Step

We begin with the foundation in [app/models/ipo_model.py](app/models/ipo_model.py), configuration, and tests. The existing [app/services/ipo_service.py](app/services/ipo_service.py) will remain a compatibility boundary while the domain model becomes real.

Verification will be limited to local tests and import/type checks. No database, API, or email credentials are needed yet.

The complete persistent plan is recorded in `/memories/session/plan.md`.

Reply with approval to begin Step 1.
