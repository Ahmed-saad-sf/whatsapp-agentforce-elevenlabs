#!/bin/bash

# Deploy Heroku App via Heroku Platform API
# This script uses Heroku Platform API to deploy without CLI

set -e

echo "🚀 Deploying Heroku TTS Proxy via Platform API"
echo "================================================"

# Configuration
APP_NAME="tts-proxy-1766485661"
HEROKU_API_KEY="${HEROKU_API_KEY:-}"  # Get from environment or prompt

if [ -z "$HEROKU_API_KEY" ]; then
    echo "❌ HEROKU_API_KEY environment variable not set"
    echo ""
    echo "To get your Heroku API key:"
    echo "1. Go to: https://dashboard.heroku.com/account"
    echo "2. Scroll to 'API Key' section"
    echo "3. Copy your API key"
    echo ""
    echo "Then run:"
    echo "  export HEROKU_API_KEY='your-api-key-here'"
    echo "  ./deploy-via-heroku-api.sh"
    exit 1
fi

# Check if git remote exists
if ! git remote | grep -q "^heroku$"; then
    echo "📦 Adding Heroku git remote..."
    git remote add heroku https://git.heroku.com/$APP_NAME.git 2>/dev/null || true
fi

# Method 1: Deploy via Git (recommended - uses Platform API under the hood)
echo ""
echo "📤 Method 1: Deploying via Git (uses Platform API)..."
echo "   This pushes to Heroku's git endpoint which uses Platform API"

# Check if we're on the right branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "master" ] && [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Warning: Not on master/main branch. Current branch: $CURRENT_BRANCH"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Push to Heroku
echo "   Pushing to Heroku..."
git push heroku master 2>&1 | tail -20

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ Deployment successful!"
else
    echo "❌ Deployment failed"
    exit 1
fi

# Method 2: Direct Platform API deployment (alternative)
echo ""
echo "📋 Method 2: Direct Platform API Deployment (Alternative)"
echo "   This method uses Platform API directly to create builds"
echo ""
echo "To use Platform API directly, you would:"
echo "1. Create a source blob (tarball of your code)"
echo "2. POST to /apps/{app_id}/builds endpoint"
echo "3. Monitor build status"
echo ""
echo "Example curl command:"
echo "  curl -X POST https://api.heroku.com/apps/$APP_NAME/builds \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -H 'Accept: application/vnd.heroku+json; version=3' \\"
echo "    -H 'Authorization: Bearer \$HEROKU_API_KEY' \\"
echo "    -d '{\"source_blob\":{\"url\":\"...\",\"version\":\"...\"}}'"
echo ""
echo "Note: Git push method (Method 1) is simpler and recommended."

# Verify deployment
echo ""
echo "🔍 Verifying deployment..."
sleep 3

HEALTH_URL="https://$APP_NAME-e2568b14da9b.herokuapp.com/health"
HEALTH_RESPONSE=$(curl -s "$HEALTH_URL" 2>/dev/null || echo "")

if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    echo "✅ Health check passed!"
    echo "   Response: $HEALTH_RESPONSE"
else
    echo "⚠️  Health check failed or app is still starting"
    echo "   Response: $HEALTH_RESPONSE"
    echo "   Check logs: heroku logs --tail --app $APP_NAME"
fi

echo ""
echo "=================================================================="
echo "✅ Deployment Complete!"
echo ""
echo "📋 App Information:"
echo "   App Name: $APP_NAME"
echo "   URL: https://$APP_NAME-e2568b14da9b.herokuapp.com"
echo ""
echo "📋 Useful Commands:"
echo "   View logs: heroku logs --tail --app $APP_NAME"
echo "   Check config: heroku config --app $APP_NAME"
echo "   Restart: heroku restart --app $APP_NAME"
echo ""
echo "=================================================================="















