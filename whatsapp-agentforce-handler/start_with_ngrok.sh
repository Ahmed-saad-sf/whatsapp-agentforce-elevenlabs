#!/bin/bash
# Start the function locally and expose with ngrok

cd "$(dirname "$0")"

echo "🚀 Starting WhatsApp Agentforce Handler with ngrok"
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing Flask..."
    pip3 install --break-system-packages flask requests gunicorn 2>&1 | tail -3
fi

# Start Flask in background
echo "🌐 Starting Flask server on port 8080..."
export FLASK_APP=main.py
export FLASK_ENV=production
python3 -m flask run --host=0.0.0.0 --port=8080 > /tmp/flask.log 2>&1 &
FLASK_PID=$!
echo "   Flask PID: $FLASK_PID"

# Wait for Flask to start
sleep 3

# Check if Flask is running
if ! curl -s http://localhost:8080/ > /dev/null; then
    echo "❌ Flask server failed to start"
    kill $FLASK_PID 2>/dev/null
    exit 1
fi

echo "✅ Flask server started"
echo ""

# Start ngrok
echo "🌍 Starting ngrok tunnel..."
ngrok http 8080 > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
sleep 3

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; tunnels = json.load(sys.stdin).get('tunnels', []); print(tunnels[0]['public_url'] if tunnels else '')" 2>/dev/null)

if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL"
    kill $FLASK_PID $NGROK_PID 2>/dev/null
    exit 1
fi

echo "✅ ngrok tunnel active"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 WEBHOOK URL: $NGROK_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Configure Twilio Webhook:"
echo "   1. Go to: https://console.twilio.com/"
echo "   2. Navigate to: Messaging → Settings → WhatsApp Sandbox"
echo "   3. Set 'When a message comes in' URL: $NGROK_URL"
echo "   4. Set HTTP Method: POST"
echo "   5. Save"
echo ""
echo "🧪 Test by sending a WhatsApp message to: +1 415 523-8886"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $FLASK_PID $NGROK_PID 2>/dev/null
    echo "✅ Stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep running
while true; do
    sleep 1
done







