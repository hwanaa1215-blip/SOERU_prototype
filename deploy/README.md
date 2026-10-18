# Cloud Shell deployment

Target project: `stunning-surge-443909-e4`; region: Tokyo (`asia-northeast1`).

The owner must explicitly authorize provisioning/public deployment by typing `DEPLOY` when running the script. Billing verification alone is not deployment authorization. The script creates Cloud Run, source-build artifacts, two service accounts, Firestore, a private image bucket, anonymous Firebase/Identity Platform authentication, an authentication-only public web API key and a Gemini Secret Manager secret.

1. Upload `dose-timer-cloud.zip` using Cloud Shell's three-dot menu → Upload.
2. Run `unzip -q dose-timer-cloud.zip` then `cd dose-timer`.
3. Run `bash deploy/cloud-shell.sh` and review the printed target/cost scope.
4. Type `DEPLOY` to authorize. When asked, paste your existing Gemini key into the hidden prompt. Do not paste the key into a command or send it in chat.
5. Wait for build/deploy. Open the final `https://...run.app` URL.
6. Verify a real synthetic-photo extraction, confirmation, reminder, taken persistence after reload, and isolation from a private-window session. Confirm no `.local` files or API keys are downloadable.

Cloud build can take several minutes; IAM propagation, organizational policies, quota or project configuration can require additional steps. Local checks do not verify these external conditions. Report the command error without including credentials.

## Runtime design and limits

- Public HTML and configuration; each data API verifies a Firebase ID token. Anonymous browser identities persist through a private refresh token in browser storage. Clearing that storage or changing browser creates a different identity and does not recover the old data.
- Server-only Firestore IAM, one bounded aggregate per hashed UID, 800,000-byte bound and compare-and-swap version checks. Conflicting writers return 409. GCS images are private, create-only and read at pinned generation with SHA-256 verification. An interrupted metadata commit can retain an orphan private image; no automated cleanup service is included.
- Project-wide UTC daily limits: 100 uploads and 100 extraction attempts, reserved transactionally. These bound those operations, not total spending or anonymous account creation. Auth, storage, builds, reads and traffic can still incur charges. Create a budget alert in the console; it is not a spending cap.
- Single instance, minimum zero; open-page reminders only. Cloud demo clock remains explicitly labelled for recording. Synthetic data only; no real patient use or production compliance claim.
- Gemini credentials are supplied through Secret Manager, never browser config/build arguments. The public web key is limited to authentication APIs and is not the Gemini credential.

Keep the app available through evaluation. To stop public serving after evaluation (separate intentional action): `gcloud run services delete dose-timer --region=asia-northeast1`. Other resources and stored data remain and can continue to incur costs; review them separately before deletion. Do not close the judging URL immediately after submission.
