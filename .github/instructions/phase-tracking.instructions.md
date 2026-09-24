---
description: "Keep the IPO Pulse development plan current and mark phases complete only after their validation gate passes."
applyTo: "**"
---

# Phase tracking

Use `README.md` as the source of truth for the IPO Pulse development plan.

- Before coding, identify the current phase and its smallest next deliverable.
- Keep changes within the current phase unless the user explicitly changes scope.
- Add the smallest runnable check required by the phase.
- Do not mark a phase complete based on implementation alone.
- Mark a phase `Complete` only after every listed completion gate passes.
- When a phase is complete, update the README status table and completion notes in the same change.
- If validation fails, leave the phase `In progress` and report the blocking failure.
- Keep only one phase as `Next` or `In progress` at a time.