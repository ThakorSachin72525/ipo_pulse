---
description: "Commit independently completed IPO Pulse features after focused validation; complete phases only after their full gate passes."
applyTo: "**"
---

# Feature and phase commit workflow

When a main function or feature is complete and its focused validation passes:

- Update relevant documentation when behavior, scope, or usage changed.
- Stage only files belonging to that feature; do not use `git add -A` in a dirty worktree.
- Commit the feature as one logical change using a message shaped like:
  - `Feature: Prediction persistence`
  - `Feature: Listing accuracy`

When a phase is marked Complete in the project plan or README status table:

- Confirm every completion gate for the phase has passed.
- Update the README phase status and completion details in the same change.
- Stage only remaining files for the phase; feature work already committed does not need to be committed again.
- Commit the remaining phase work using a message shaped like:
  - `Phase 4: Prediction pipeline`
  - `Phase 5: Listing accuracy`

- Never commit partial or speculative work before its relevant validation passes.
- Keep every feature or phase commit focused; do not mix unrelated work.
- If validation fails, leave the feature uncommitted and keep the phase In progress.
