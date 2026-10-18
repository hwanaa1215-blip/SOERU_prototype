# Decisions

## 2026-10-18 — Prepare a public synthetic demo without local identity reuse

Project/billing verification authorizes preparation; provisioning/public serving still requires the owner's explicit `DEPLOY` confirmation. Bundle a single React/FastAPI Cloud Run service using anonymous Firebase/Identity Platform identities, server token verification, Firestore compare-and-swap owner aggregates, private GCS originals and Secret Manager. Never ship the workstation token or Gemini key. Synthetic clock controls remain per user and visibly labelled for recording. Bound expensive operations globally while documenting that quotas do not cap total charges. Keep existing SOERU untouched and local mode compatible.

## 2026-10-18 — Owner-authorized live Gemini connection

The owner requested live connection and supplied a private local credential. This authorizes bounded synthetic-image connectivity calls; public deployment and billable resource provisioning remain separate. Runtime API verification showed the old default model unavailable to new users. Select the available `gemini-3.8-flash`, low thinking, 90-second timeout, no retries and 4096-token cap. Keep unverified extraction separate from confirmation; no automatic reminder activation. Verify through the authenticated application API and record actual success/failures in the development log.

## 2026-10-17 — Isolated local submission prototype

Owner authorization: create a new folder implementing photo input for medication guides and supplement labels, confirmed times, reminders and self-reported completion. Preserve the existing SOERU project.

- Keep all application sources, samples, runtime files and documents inside `dose-timer/`. Reuse libraries and technical patterns, without importing or editing SOERU sources/data. No Git history rewrite or new remote.
- React/TypeScript/Vite/Tailwind and FastAPI, with an independent SQLite database for this synthetic local milestone. No caregiver, subscription or clinical judgment features.
- Use a verified loopback development bearer identity, private local persistence and owner-scoped queries. This is not Firebase/cloud release authentication. Production migration is outside the authorized milestone.
- Preserve original image, unverified/failed attempts, human-confirmed routines and self-report records separately. Exact bundled samples are clearly simulated. Arbitrary photo reading requires Gemini; failed reading permits genuine manual entry.
- Never infer schedule times or dosage. Users explicitly enter dates and fixed Seoul daily times, review details and confirm activation. Duplicate confirmation retries replay their original result; changed payload under the same key conflicts. Repeated taken reports replay the saved report.
- Open-page polling and optional browser notifications only; no closed-page/watch alarm claim. Synthetic clock controls are clearly labelled, and real audit timestamps remain separate.
- No paid call, public deployment, contest submission or external sharing is authorized by this milestone. A separate folder does not change pre-existing code disclosure obligations.
