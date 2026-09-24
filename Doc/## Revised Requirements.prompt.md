## Revised Requirements

Build an automation-first IPO tracking system:

- Fetch IPO and GMP data from IPO Guru.
- Store IPO metadata in Supabase PostgreSQL.
- Store GMP observations as append-only daily records.
- Record GMP-based predictions before listing.
- Store actual listing prices after listing.
- Calculate prediction errors and direction accuracy.
- Generate and email daily reports through Gmail SMTP.
- Run automatically through GitHub Actions.
- Keep all credentials in GitHub Actions Secrets.
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
   - Add sanitized response fixtures and API error tests.

3. **Supabase Database**
   - Add migrations for:
     - `ipos`
     - `gmp_history`
     - prediction records
     - evaluation results
   - Preserve GMP history without overwriting previous observations.
   - Add idempotent repository operations.

4. **Prediction Engine**
   - Calculate expected listing price, investment, profit, return, and predicted gain.
   - Store the GMP observation used for each prediction.

5. **Listing Accuracy**
   - Record actual listing prices.
   - Calculate absolute error, percentage error, actual gain, and direction accuracy.
   - Handle missing GMP or missing listing data safely.

6. **Daily Email Report**
   - Generate current IPO, historical result, and overall statistics sections.
   - Add Gmail SMTP delivery.
   - Include a local dry-run mode.

7. **GitHub Actions**
   - Add daily scheduling.
   - Add manual dispatch.
   - Wire secrets securely.
   - Add logging and failure reporting.

8. **Dashboard Later**
   - Decide between extending PySide6 or using Streamlit.
   - Add IPO overview, GMP history, actual-versus-predicted views, and charts.

## First Step

We begin with the foundation in [app/models/ipo_model.py](app/models/ipo_model.py), configuration, and tests. The existing [app/services/ipo_service.py](app/services/ipo_service.py) will remain a compatibility boundary while the domain model becomes real.

Verification will be limited to local tests and import/type checks. No database, API, or email credentials are needed yet.

The complete persistent plan is recorded in `/memories/session/plan.md`.

Reply with approval to begin Step 1.
