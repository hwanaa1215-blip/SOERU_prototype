# Dose Timer

## Cloud deployment preparation

For project `stunning-surge-443909-e4`, see [Cloud Shell instructions](deploy/README.md). The prepared Docker container serves the React build and FastAPI together, verifies anonymous Firebase ID tokens, stores per-user metadata in Firestore and immutable originals in a private Cloud Storage bucket, and reads Gemini credentials from Secret Manager. Cloud provisioning/public deployment requires explicit owner authorization. Local verification does not establish real project IAM, auth configuration or successful deployment; validate the final deployed URL before recording.

A separate, English-language hackathon prototype for people managing multiple medication and supplement reminders. Temporary product name. Synthetic data only.

## Scope

1. Photograph/upload a medication guide or supplement label (JPEG/PNG).
2. Read visible names, strength, dose and directions using Gemini, or clearly labelled simulated samples.
3. Compare the original image, correct the reading and explicitly enter fixed daily times and dates.
4. Confirm to activate, see both types together in today's timeline, receive open-page reminders and report taken.

No interaction verdicts, dose advice, automatic timing recommendations, caregiver access, subscriptions or watch app. User-reported taken does not verify ingestion. Seoul timezone; fixed times only; at most six daily times and a 90-day date range. Do not convert unclear or meal-relative directions into a fixed time without appropriate confirmation.

## Run on Windows

Python 3.12+ and Node.js 22+ are recommended.

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ../frontend
npm ci
cd ..
.\start.ps1
```

On the original workstation the launcher can reuse the existing parent Python environment until a dedicated environment is installed. The source has no imports from SOERU. The frontend dependencies and runtime data are separate. Copy this entire `dose-timer` folder to work independently.

Open **http://127.0.0.1:5195/**. Keep the terminal running. No `.env` is required. The launcher creates a stable private local access token under ignored `.local/`, supplied only to the local development frontend. APIs validate it and partition all records by its derived identity. This is a single-user local prototype, not production authentication. Never expose the Vite server or API to the internet or a shared network.

### Actual Gemini reading

Default startup uses **sample mode**, recognizes only exact bundled fictional images, and labels the result as simulated. Other images can be entered manually. It does not claim to perform OCR on arbitrary images in sample mode.

For an owner-approved potentially billed live session, securely set `GEMINI_API_KEY` in the terminal environment and launch `./start.ps1 -LiveExtraction`. Default model: `gemini-3.8-flash`, with low thinking for transcription. Optional `GEMINI_MODEL` overrides the model ID. The adapter uses structured output, 90-second timeout, no retries and a 4096-token output cap. The local database limits extraction to 20 attempts; manual entry remains available. No key is put in frontend code; the launcher only reads your supplied credential. A live synthetic medication-image transcription was verified on 2026-10-18. This is a connectivity check, not a measurement of recognition accuracy.

For local setup without `.env`, you may instead paste only the API key into `.local/gemini-key.txt`. This ignored file contains a plaintext credential; keep it private and never share the `.local/` folder. `start.ps1 -LiveExtraction` reads it into the backend environment without printing its contents. The launcher also accepts an existing `GOOGLE_API_KEY` as a fallback. The sample-mode default is unchanged.

## Three-minute recording

- 0:00–0:25: explain the problem and show the empty Today screen.
- 0:25–1:10: Add from a photo → fictional medication guide → review → enter a future time today → check confirmation → activate.
- 1:10–1:55: add the supplement sample, enter a different future time, confirm.
- 1:55–2:35: Today → both items → **Jump to next reminder** → reminder due → **Mark as taken**.
- 2:35–3:00: show My routines and explain that information and times are reviewed by the user.

Recording controls explicitly show demo time and real time. Sample mode must be described as simulated; use a verified live Gemini run to demonstrate actual image analysis.

## Reminder delivery

The open page refreshes every three seconds. Due items remain visible until reported taken or the routine is stopped. Browser notifications are optional and permission-based; they show medication names/amounts on the device. They can be delayed by browser background throttling. Closing the tab stops reminder delivery. OS background alarms, service-worker push and smartwatch notifications are not implemented.

## Data and source

SQLite under ignored `data/` stores separate original image BLOBs, extraction attempts, confirmed routines and self-report records. A failed extraction remains failed even after manual confirmation. Stopping a routine disables pending reminders and retains history. No cloud resources or live health data are used. This demo has no production retention/deletion service or cloud identity.

This prototype reuses the original project's technical patterns and existing libraries. Creating a separate folder does not establish competition eligibility or new authorship. Disclose reuse according to the organizer's rules. No contest submission or public deployment has occurred.

## Checks

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ../frontend
npm run build
npm run test:e2e
```

See `docs/development-log.md` for actual executed results and limitations.
