#!/bin/bash
# Deploy to Cloud Run instead of Cloud Functions Gen2

set -e

echo "🚀 Deploying WhatsApp Agentforce Handler to Cloud Run..."
echo ""

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check required environment variables
REQUIRED_VARS=(
    "TWILIO_ACCOUNT_SID"
    "TWILIO_AUTH_TOKEN"
    "AGENTFORCE_AGENT_ID"
    "SALESFORCE_CONSUMER_KEY"
    "SALESFORCE_CONSUMER_SECRET"
    "SALESFORCE_INSTANCE_URL"
    "GOOGLE_CLOUD_API_KEY"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var is not set"
        exit 1
    fi
done

echo "✅ All required environment variables are set"
echo ""

# Build and deploy to Cloud Run
SERVICE_NAME="whatsapp-agentforce-handler"
REGION="us-central1"
PROJECT_ID="your-google-cloud-project-id"

echo "📦 Building and deploying to Cloud Run..."
echo ""

gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --timeout 540 \
  --memory 512Mi \
  --max-instances 10 \
  --set-env-vars "TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID},TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN},TWILIO_WHATSAPP_FROM=${TWILIO_WHATSAPP_FROM:-whatsapp:+14155238886},AGENTFORCE_AGENT_ID=${AGENTFORCE_AGENT_ID},SALESFORCE_CONSUMER_KEY=${SALESFORCE_CONSUMER_KEY},SALESFORCE_CONSUMER_SECRET=${SALESFORCE_CONSUMER_SECRET},SALESFORCE_INSTANCE_URL=${SALESFORCE_INSTANCE_URL},GOOGLE_CLOUD_API_KEY=${GOOGLE_CLOUD_API_KEY}" \
  --project $PROJECT_ID

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)' --project $PROJECT_ID)
echo ""
echo "✅ Service URL: $SERVICE_URL"
echo ""
echo "📋 Next steps:"
echo "1. Configure Twilio webhook:"
echo "   - Go to: https://console.twilio.com/"
echo "   - Navigate to: Messaging → Settings → WhatsApp Sandbox"
echo "   - Set Webhook URL: $SERVICE_URL"
echo "   - Set HTTP Method: POST"
echo "   - Save"
echo ""
echo "2. Test the webhook:"
echo "   curl -X POST $SERVICE_URL \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"From\":\"whatsapp:+971586672299\",\"Body\":\"Hello\",\"MessageSid\":\"test123\",\"NumMedia\":\"0\"}'"







