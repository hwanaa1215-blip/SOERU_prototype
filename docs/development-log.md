# Development log

## 2026-10-18 — Three-minute deployed demonstration video

- Owner requested a video of the agent demonstrating the application. Used CUA to operate the actual public Cloud Run app with the two fictional source samples and real Gemini extraction. Reviewed extracted name/strength/dose, entered 21:00 and 21:30 explicitly, confirmed both routines, showed the combined timeline, advanced the labelled demo clock, self-reported one occurrence taken and displayed confirmed routines.
- Captured actual browser frames only; no application results were synthesized. Trimmed the long AI wait and input-recovery intervals, retained explicit edited-wait disclosure and DEMO TIME explanation. English captions are outside the application image; no narration/audio was generated. The browser's existing anonymous synthetic session now contains these two routines and one self-report.
- Created `outputs/Dose_Timer_Demo_3min.mp4` using `scripts/assemble-demo-video.py` and FFmpeg. Verified with ffprobe: **180.000 seconds**, H.264, 1280x960, 24 fps, **2,173,303 bytes**. Visually checked a composed frame for legibility. Edit timeline is `outputs/demo-video-edit.json`; raw frames remain ignored under `.local/video-capture/`.
- No contest upload/submission or external message was sent. Owner must review and upload the video according to submission rules, and provide the remaining prescribed deck, repository and description.

## 2026-10-18 — Public live Gemini smoke check passed after key replacement

- Owner reported Secret Manager version 2 and Cloud Run revision `dose-timer-00002-fsq` serving 100% traffic after replacing the invalid credential. Subsequent shell `command not found` lines came from re-entered output; the deployment success was independently checked through the public service.
- New isolated synthetic test identity: anonymous sign-in HTTP 200; private guide upload HTTP 200; actual extraction HTTP **200**, source **gemini**, status **unverified**, **1 item**, **12.3 seconds**. No key or ID token was printed; no routine was activated. This supersedes the earlier cloud Gemini permission failure, not the broader accuracy/production-readiness limitations.
- Public app URL remains `https://dose-timer-789776127504.asia-northeast1.run.app`. Owner can refresh and record the deployed photo-review-schedule-reminder journey. Video, prescribed deck, repository access and actual submission remain owner actions.

## 2026-10-18 — Owner executed public deployment; Gemini permission gate remains

- Owner explicitly typed `DEPLOY` in Cloud Shell. They reported successful revision `dose-timer-00001-tk8`, 100% traffic and `/health` OK in project `stunning-surge-443909-e4`. Public service URL: `https://dose-timer-789776127504.asia-northeast1.run.app` (also reported canonical alternate `https://dose-timer-4mnnm5rghq-an.a.run.app`).
- Remote smoke check from this workstation: page/health/config HTTP 200, cloud mode true, real anonymous authentication 200, authenticated state 200, synthetic image upload and owned original 200, original without authentication 401. Thus real Firebase, Firestore and private GCS paths were exercised for a synthetic test identity.
- Real deployed extraction returned HTTP 503 with sanitized Gemini access-denied error (provider 401/403 path). Live cloud AI is not verified and submission/demo readiness must not be claimed until the secret/API access is fixed. No routine was activated by the smoke check.
- During earlier Cloud Shell setup, authentication initialization lacked the `x-goog-user-project` header; adding it allowed setup to continue. Updated local script accordingly. A user-supplied Gemini credential was exposed in chat/shell command history; instructed owner to revoke and replace it, without recording its value here.

## 2026-10-18 — Cloud deployment package prepared

- Owner supplied project `stunning-surge-443909-e4` and verified `billingEnabled=True` in their Cloud Shell. This establishes project/billing readiness, not authorization to create resources or publish. No local gcloud/Docker was available, so prepared a source ZIP and a reviewable Cloud Shell script with a `DEPLOY` authorization prompt.
- Added isolated cloud mode: server-side Firebase/Identity Platform token verification before multipart parsing, per-request hashed UID context, anonymous browser sign-in/refresh through official Firebase REST APIs, no local token acceptance in cloud mode. Runtime public config contains only an authentication-restricted public web key; Gemini remains server-only.
- Extracted local persistence without changing the existing SQLite schema. Added bounded Firestore owner aggregates with compare-and-swap commits (800,000-byte bound), private create-only GCS originals with pinned generation/hash verification, deterministic metadata ordering, and transactional project-wide 100/day upload and extraction limits. A failed metadata commit may retain a private orphan object; automated cleanup is not implemented.
- Added multi-stage Dockerfile, strict source/container exclusions, Cloud Shell deployment script and documented target resources. Tokyo region; single Cloud Run instance, zero minimum, private image bucket, Firestore, separate runtime/build identities, scoped permissions and Secret Manager. The script performs remote provisioning only after the user types `DEPLOY`; reads the Gemini key at a hidden prompt. Daily limits/instance settings are not a monetary spending cap.
- Verification: local backend **9 passed, 1 emulator skip**; separate local Firestore emulator cloud checks **2 passed** (cloud auth isolation plus real SDK CAS/global quota checks). Existing Chromium journeys **2 passed** after authentication refactor. TypeScript/Vite build passed; Bash syntax check passed. No Docker container or real Firebase/GCS/IAM/Cloud Run deployment was executed here. Remote build, permissions and anonymous auth configuration remain unverified until the owner runs and tests the deployment.
- Prepared upload bundle contains source, synthetic samples and deployment/docs only. Explicitly excludes local credentials, data, environments, node_modules and generated frontend output. Original SOERU code/data were not changed.

## 2026-10-18 — Live Gemini connection verified

- Owner supplied the credential in the ignored key file and requested connection. Read it without printing it; started the local app with `start.ps1 -LiveExtraction -NoOpen` on 5195/API 8035. No public/cloud deployment.
- Model-list access succeeded. The old default `gemini-2.5-flash` returned 404 (unavailable to new users). Verified `gemini-3.8-flash` in the actual API model list and changed the default. Default thinking exceeded the earlier timeout; minimal thinking was rejected with 400. Low thinking produced validated structured transcription. Set low thinking for Gemini 3 overrides and a 90-second request limit, retaining no retries and the 4096 output-token cap. Added sanitized 404/access/quota error messages without recording raw provider errors or credentials.
- Final authenticated application API: HTTP **200**, source **gemini**, status **unverified**, one synthetic item: Demo Medication A / 5 mg / 1 tablet, **15.5 seconds**. This was an actual model call, not sample-fixture substitution. No routine or schedule was activated by the test. A preceding direct low-thinking diagnosis also succeeded in 43.0 seconds; several earlier requests failed during model/setting diagnosis.
- Backend regression suite after model/error changes: **8 passed**, one existing TestClient dependency warning. Updated README configuration and timeout. Final low-thinking behavior was verified through the actual application API rather than another broad browser rerun.
- This establishes one-image connectivity only, not accuracy for arbitrary guides/supplements. Local preview remains running in Gemini mode; user should refresh the browser and see `Gemini image reading`. Public hosting, production identity/storage, video/deck/repository submission remain pending.

## 2026-10-18 — Live Gemini connection preparation

- Owner requested Gemini connection. Checked only credential presence: GEMINI_API_KEY/GOOGLE_API_KEY were absent, and no relevant .env file existed. No secret values were printed.
- Added optional ignored `.local/gemini-key.txt` input to `start.ps1 -LiveExtraction`, with environment credentials taking precedence and GOOGLE_API_KEY fallback. Created an empty local key file and requested opening it in the editor. No application changes to SOERU.
- PowerShell parser: passed. `git check-ignore`: key file is excluded. Existing structured transcription adapter remains in place. Actual live startup and one synthetic-image smoke call are pending the owner's credential; no live call or public deployment occurred.

## 2026-10-17 — Separate photo-to-reminder local prototype

### Completed

- Created this `dose-timer/` folder at the owner's request. Original SOERU application sources, configuration, historical documents and data were not edited.
- Added independent FastAPI/SQLite APIs for authenticated image upload/original retrieval, separate extraction attempts, explicit confirmed daily routines, derived due occurrences, idempotent taken reports and stopping reminders. All record queries are scoped to the verified local identity.
- Added JPEG/PNG signature/decode validation, 5 MiB/24-megapixel limits, request streaming bound, extraction serialization/20-attempt local limit and no-store responses. Credentials and local data are ignored by Git.
- Added bounded structured Gemini transcription and exact-hash, prominently labelled fictional sample mode. No automatic schedule activation or model-generated timing/dose advice. Genuine manual fallback preserves failed attempts.
- Added English responsive Today, photo review and My routines screens, optional browser notifications, open-page reminder polling and clearly separated synthetic/real clocks. Fixed decorative icons affecting accessible button names and explicitly anchored the desktop sidebar after visual inspection.
- Added two fictional sample PNGs/expected readings, a generator, standalone frontend package/lockfile, backend requirements, local launcher and three-minute recording guide in README.
- Started loopback preview on web 5195/API 8035 using `start.ps1 -NoOpen`; requested a right-side browser panel. The local launcher reuses this workstation's existing Python environment when no dedicated environment exists. The new source code itself has no parent-project imports.

### Executed checks

- Backend: **8 passed**, Python 3.12, one existing Starlette/TestClient dependency deprecation warning. Coverage includes two source types, no activation from extraction, validation, due-time reporting, retry replay, stop, original integrity, failed/manual provenance, authentication, cross-identity ownership and reading limits.
- Frontend: TypeScript and Vite production build **passed**.
- Chromium: **2 passed** (9.4 seconds): two photos → review/confirm → combined schedule → demo advance → reminder → taken → reload persistence → stop, and extraction failure → manual confirmation. Both journeys also check 390px mobile overflow. Captured and visually reviewed desktop/mobile screenshots under ignored frontend/test-results.
- First sandboxed pytest attempt was blocked by Windows temporary-directory access; approved execution completed. Offline npm install first failed in the sandbox's cache, then succeeded using the workstation cache with approved execution. The first browser run found an accessible-name mismatch caused by decorative icons; fixed the markup and reran both journeys successfully.

### Limitations and next actions

- Default preview uses simulated transcription of exact bundled samples. No live Gemini accuracy, paid call, Firebase/cloud storage, public hosting, closed-page alarm, smartwatch integration or contest eligibility has been verified.
- Fixed Asia/Seoul daily times only, 1–6 times/day, 1–90 date range, 40 images/100 routines/20 extraction attempts per local identity. Manual confirmation is still available after reading limits. SQLite stores synthetic data locally; cloud identity/retention and release hardening are future gates.
- Browser notifications are optional, can reveal item details to the device, and can be delayed by background throttling. The in-app due list remains available while connected/open. Reporting taken is a self-report, not clinical or ingestion verification.
- Owner actions: review the local UI, choose the submission name and rules, record the documented sample workflow, or separately approve/configure a live Gemini session. No API key is required for the sample demonstration. No submission was made.
