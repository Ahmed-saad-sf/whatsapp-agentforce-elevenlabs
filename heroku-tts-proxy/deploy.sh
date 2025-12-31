#!/bin/bash

# Heroku TTS Proxy - Deployment Script
# This script automates the Heroku deployment

set -e

echo "🚀 Heroku TTS Proxy - Deployment Script"
echo ""

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI not found. Please install it first:"
    echo "   Mac: brew tap heroku/brew && brew install heroku"
    echo "   Or: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if logged in
if ! heroku auth:whoami &> /dev/null; then
    echo "🔐 Please login to Heroku..."
    heroku login
fi

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
git init
git add .
git commit -m "Initial deployment" || echo "Already committed"
git push heroku main || git push heroku master

echo ""
echo "5️⃣ Scaling dyno..."
heroku ps:scale web=1 --app $APP_NAME

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Your credentials:"
APP_URL=$(heroku info --app $APP_NAME --json | python3 -c "import sys, json; print(json.load(sys.stdin)['app']['web_url'])" 2>/dev/null || echo "https://${APP_NAME}.herokuapp.com")
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
echo "   2. Update Salesforce component properties"
echo "   3. Test voice mode!"
echo ""
echo "💾 Save these credentials securely!"















