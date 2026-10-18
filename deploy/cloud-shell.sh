#!/usr/bin/env bash
# Run from the dose-timer folder in Google Cloud Shell. Never enable shell tracing.
set -euo pipefail
PROJECT=stunning-surge-443909-e4
REGION=asia-northeast1
SERVICE=dose-timer
BUCKET="${PROJECT}-dose-timer-images"
RUNTIME="dose-timer-runtime@${PROJECT}.iam.gserviceaccount.com"
BUILDER="dose-timer-build@${PROJECT}.iam.gserviceaccount.com"
cd "$(dirname "$0")/.."
printf '\nProject: %s\nRegion: %s (Tokyo)\n' "$PROJECT" "$REGION"
printf 'This creates cloud resources and a PUBLIC synthetic demo URL. Usage can incur charges.\n'
printf 'Limits: 1 Cloud Run instance, 0 minimum; 100 image uploads/day and 100 Gemini attempts/day across the demo.\n'
printf 'These settings are not a monetary spending cap. Keep the service available for judging.\n'
read -r -p 'Type DEPLOY to authorize provisioning and public deployment: ' approval
[[ "$approval" == DEPLOY ]] || { echo 'No resources were created.'; exit 1; }
gcloud config set project "$PROJECT"
[[ "$(gcloud billing projects describe "$PROJECT" --format='value(billingEnabled)')" == True ]] || { echo 'Billing is not enabled.'; exit 1; }
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com storage.googleapis.com secretmanager.googleapis.com identitytoolkit.googleapis.com securetoken.googleapis.com apikeys.googleapis.com iam.googleapis.com

for name in dose-timer-runtime dose-timer-build; do
  gcloud iam service-accounts describe "${name}@${PROJECT}.iam.gserviceaccount.com" >/dev/null 2>&1 || gcloud iam service-accounts create "$name" --display-name="$name"
done
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$BUILDER" --role=roles/run.builder --condition=None --quiet >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$RUNTIME" --role=roles/datastore.user --condition=None --quiet >/dev/null
gcloud firestore databases describe --database='(default)' >/dev/null 2>&1 || gcloud firestore databases create --database='(default)' --location="$REGION" --type=firestore-native
gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 || gcloud storage buckets create "gs://$BUCKET" --location="$REGION" --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$RUNTIME" --role=roles/storage.objectAdmin >/dev/null

# Enable anonymous Firebase/Identity Platform authentication. OAuth access tokens
# remain in shell memory and are never echoed or written to a source file.
ACCESS_TOKEN="$(gcloud auth print-access-token)"
CONFIG_URL="https://identitytoolkit.googleapis.com/admin/v2/projects/$PROJECT/config"
status="$(curl -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $ACCESS_TOKEN" -H "x-goog-user-project: $PROJECT" "$CONFIG_URL")"
if [[ "$status" != 200 ]]; then
  curl -fsS -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H "x-goog-user-project: $PROJECT" -H 'Content-Type: application/json' -d '{}' "https://identitytoolkit.googleapis.com/v2/projects/$PROJECT/identityPlatform:initializeAuth" >/dev/null
fi
curl -fsS -X PATCH -H "Authorization: Bearer $ACCESS_TOKEN" -H "x-goog-user-project: $PROJECT" -H 'Content-Type: application/json' -d '{"signIn":{"anonymous":{"enabled":true}}}' "$CONFIG_URL?updateMask=signIn.anonymous.enabled" >/dev/null
unset ACCESS_TOKEN

KEY_NAME="$(gcloud services api-keys list --filter='displayName=dose-timer-web-auth' --format='value(name)' --limit=1)"
if [[ -z "$KEY_NAME" ]]; then
  gcloud services api-keys create --display-name=dose-timer-web-auth --api-target=service=identitytoolkit.googleapis.com --api-target=service=securetoken.googleapis.com --quiet >/dev/null
  KEY_NAME="$(gcloud services api-keys list --filter='displayName=dose-timer-web-auth' --format='value(name)' --limit=1)"
fi
WEB_KEY="$(gcloud services api-keys get-key-string "$KEY_NAME" --format='value(keyString)')"
[[ -n "$WEB_KEY" ]] || { echo 'Web authentication key was not created.'; exit 1; }

if ! gcloud secrets describe dose-timer-gemini >/dev/null 2>&1; then
  gcloud secrets create dose-timer-gemini --replication-policy=automatic >/dev/null
fi
if ! gcloud secrets versions describe latest --secret=dose-timer-gemini >/dev/null 2>&1; then
  read -r -s -p 'Paste your Gemini API key (hidden; press Enter): ' GEMINI_KEY
  printf '\n'
  [[ -n "$GEMINI_KEY" ]] || { echo 'No key provided.'; exit 1; }
  printf '%s' "$GEMINI_KEY" | gcloud secrets versions add dose-timer-gemini --data-file=- >/dev/null
  unset GEMINI_KEY
fi
gcloud secrets add-iam-policy-binding dose-timer-gemini --member="serviceAccount:$RUNTIME" --role=roles/secretmanager.secretAccessor --quiet >/dev/null

gcloud run deploy "$SERVICE" --source=. --region="$REGION" \
  --build-service-account="projects/$PROJECT/serviceAccounts/$BUILDER" \
  --service-account="$RUNTIME" --allow-unauthenticated \
  --min=0 --max=1 --concurrency=10 --cpu=1 --memory=512Mi --timeout=180 \
  --set-env-vars="CLOUD_MODE=true,FIREBASE_PROJECT_ID=$PROJECT,FIREBASE_WEB_API_KEY=$WEB_KEY,IMAGE_BUCKET=$BUCKET,EXTRACTION_MODE=gemini,DEMO_CLOCK=true,GEMINI_MODEL=gemini-3.8-flash" \
  --set-secrets=GEMINI_API_KEY=dose-timer-gemini:latest --quiet
URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
printf '\nDeployment URL: %s\n' "$URL"
curl -fsS "$URL/health"
printf '\nOpen the URL in a browser. Verify photos, extraction, confirmation, reminders, reload and a separate private window before recording.\n'
