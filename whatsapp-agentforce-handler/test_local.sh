#!/bin/bash
# Test the function locally

cd "$(dirname "$0")"

echo "🧪 Testing WhatsApp Agentforce Handler Locally"
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Install dependencies if needed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install --user flask requests gunicorn 2>&1 | tail -5
fi

echo "🚀 Starting local server on http://localhost:8080"
echo ""
echo "Test with:"
echo "  curl -X POST http://localhost:8080/ \\"
echo "    -H 'Content-Type: application/x-www-form-urlencoded' \\"
echo "    -d 'From=whatsapp:+971586672299&Body=Hello&MessageSid=test123&NumMedia=0'"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run Flask app
export FLASK_APP=main.py
export FLASK_ENV=development
python3 -m flask run --host=0.0.0.0 --port=8080







