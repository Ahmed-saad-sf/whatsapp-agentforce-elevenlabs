#!/bin/bash
# Deploy to Heroku

set -e

echo "🚀 Deploying WhatsApp Agentforce Handler to Heroku..."
echo ""

APP_NAME="whatsapp-agentforce-handler"

# Check if Heroku app exists
if ! heroku apps:info $APP_NAME &>/dev/null; then
    echo "📦 Creating Heroku app: $APP_NAME"
    heroku create $APP_NAME
else
    echo "✅ Heroku app exists: $APP_NAME"
fi

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env..."
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        
        # Extract key=value
        key=$(echo "$line" | cut -d'=' -f1)
        value=$(echo "$line" | cut -d'=' -f2-)
        
        if [ ! -z "$key" ] && [ ! -z "$value" ]; then
            echo "   Setting $key"
            heroku config:set "$key=$value" --app $APP_NAME
        fi
    done < .env
fi

echo ""
echo "📦 Deploying to Heroku..."
git init 2>/dev/null || true
git add .
git commit -m "Deploy WhatsApp Agentforce Handler" 2>/dev/null || git commit --amend -m "Deploy WhatsApp Agentforce Handler" 2>/dev/null || true
git push heroku main 2>&1 || git push heroku HEAD:main --force 2>&1

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Getting app URL..."
APP_URL=$(heroku apps:info $APP_NAME --json 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin)['app']['web_url'])" 2>/dev/null || echo "https://$APP_NAME.herokuapp.com")
echo ""
echo "✅ App URL: $APP_URL"
echo ""
echo "📋 Next steps:"
echo "1. Configure Twilio webhook:"
echo "   - Go to: https://console.twilio.com/"
echo "   - Navigate to: Messaging → Settings → WhatsApp Sandbox"
echo "   - Set Webhook URL: $APP_URL"
echo "   - Set HTTP Method: POST"
echo "   - Save"
echo ""
echo "2. Test the webhook:"
echo "   curl -X POST $APP_URL \\"
echo "     -H 'Content-Type: application/x-www-form-urlencoded' \\"
echo "     -d 'From=whatsapp:+971586672299&Body=Hello&MessageSid=test123&NumMedia=0'"







