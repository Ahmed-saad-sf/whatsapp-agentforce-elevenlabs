#!/bin/bash
# Auto-login to Heroku via browser (automatically presses key)

cd "$(dirname "$0")"

echo "🌐 Starting Heroku browser login..."
echo "This will automatically open your browser."
echo ""

# Use expect or just echo newline to heroku login
echo "" | heroku login 2>&1 | grep -v "Press any key" || true

# Wait a moment for browser to open
sleep 2

echo ""
echo "✅ Browser should be open. Please complete authentication."
echo ""
echo "Waiting for authentication..."
sleep 5

# Check authentication status
if heroku auth:whoami &>/dev/null; then
    echo "✅ Successfully authenticated as: $(heroku auth:whoami)"
else
    echo "⏳ Please complete the login in your browser."
    echo "Run 'heroku auth:whoami' to verify when done."
fi







