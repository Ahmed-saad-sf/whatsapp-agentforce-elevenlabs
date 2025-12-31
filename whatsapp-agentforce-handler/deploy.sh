#!/bin/bash
# Deployment script for WhatsApp Agentforce Handler

set -e

echo "🚀 Deploying WhatsApp Agentforce Handler to Google Cloud Functions..."
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

# Build environment variables string
ENV_VARS="TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID},TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN},TWILIO_WHATSAPP_FROM=${TWILIO_WHATSAPP_FROM:-whatsapp:+14155238886},AGENTFORCE_AGENT_ID=${AGENTFORCE_AGENT_ID},SALESFORCE_CONSUMER_KEY=${SALESFORCE_CONSUMER_KEY},SALESFORCE_CONSUMER_SECRET=${SALESFORCE_CONSUMER_SECRET},SALESFORCE_INSTANCE_URL=${SALESFORCE_INSTANCE_URL},GOOGLE_CLOUD_API_KEY=${GOOGLE_CLOUD_API_KEY}"

# Deploy function
echo "📦 Deploying function..."
gcloud functions deploy whatsapp-agentforce-handler \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=. \
  --entry-point=handle_webhook \
  --trigger-http \
  --allow-unauthenticated \
  --timeout=540s \
  --memory=512MB \
  --set-env-vars="$ENV_VARS" \
  --max-instances=10

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Get your function URL:"
echo "   gcloud functions describe whatsapp-agentforce-handler --gen2 --region=us-central1 --format='value(serviceConfig.uri)'"
echo ""
echo "2. Configure Twilio webhook:"
echo "   - Go to: https://console.twilio.com/"
echo "   - Navigate to: Messaging → Settings → WhatsApp Sandbox"
echo "   - Set Webhook URL to your function URL"
echo "   - Set HTTP Method: POST"
echo "   - Save"

