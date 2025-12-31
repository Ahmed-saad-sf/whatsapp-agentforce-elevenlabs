#!/bin/bash

# Heroku TTS Proxy - Deployment Script (Run after login)
# This script deploys the Heroku app after you've logged in

set -e

echo "🚀 Heroku TTS Proxy - Deployment"
echo ""

# Check if logged in
if ! heroku auth:whoami &> /dev/null; then
    echo "❌ Not logged in to Heroku."
    echo "   Please run: heroku login"
    echo "   Then run this script again."
    exit 1
fi

echo "✅ Logged in as: $(heroku auth:whoami)"
echo ""

# Set variables
APP_NAME="tts-proxy-$(date +%s)"
REGION="us"

echo "📦 Creating Heroku app..."
echo "   App Name: $APP_NAME"
echo "   Region: $REGION"
echo ""

# Generate API key
echo "1️⃣ Generating API key..."
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "   API Key: $API_KEY"
echo ""

# Create Heroku app
echo "2️⃣ Creating Heroku app..."
heroku create $APP_NAME --region $REGION

echo ""
echo "3️⃣ Setting environment variables..."
echo "   Please enter your Google Cloud TTS API Key:"
read -s GOOGLE_CLOUD_API_KEY
echo ""

# Set config vars
heroku config:set \
  GOOGLE_CLOUD_API_KEY="$GOOGLE_CLOUD_API_KEY" \
  API_KEY="$API_KEY" \
  --app $APP_NAME

echo ""
echo "4️⃣ Deploying application..."
cd "$(dirname "$0")"
git init 2>/dev/null || true
git add . 2>/dev/null || true
git commit -m "Initial deployment" 2>/dev/null || git commit --allow-empty -m "Initial deployment"
git push heroku main || git push heroku master

echo ""
echo "5️⃣ Scaling dyno..."
heroku ps:scale web=1 --app $APP_NAME

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Your credentials:"
APP_URL="https://${APP_NAME}.herokuapp.com"
echo "   App URL: $APP_URL"
echo "   API Key: $API_KEY"
echo ""
echo "🧪 Test the app:"
echo "   curl $APP_URL/health"
echo ""
echo "   curl -X POST $APP_URL/synthesize \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -H \"X-API-Key: $API_KEY\" \\"
echo "     -d '{\"text\":\"مرحبا\",\"return_type\":\"url\"}'"
echo ""
echo "📝 Next steps:"
echo "   1. Update Salesforce Remote Site Settings: $APP_URL"
echo "   2. Update Salesforce component properties:"
echo "      - Cloud Run TTS Service Url: $APP_URL/synthesize"
echo "      - Cloud Run TTS API Key: $API_KEY"
echo "   3. Test voice mode!"
echo ""
echo "💾 Save these credentials securely!"















