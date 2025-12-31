#!/bin/bash

# Quick script to check Heroku login status

echo "Checking Heroku login status..."
echo ""

if heroku auth:whoami &> /dev/null; then
    echo "✅ Logged in as: $(heroku auth:whoami)"
    echo ""
    echo "🚀 Ready to deploy! Run:"
    echo "   cd /Users/ahmed.saad/Documents/E-Finance_Tax_Advisor/heroku-tts-proxy"
    echo "   ./deploy-after-login.sh"
else
    echo "❌ Not logged in yet."
    echo ""
    echo "Please complete the browser login, then run this script again."
fi















