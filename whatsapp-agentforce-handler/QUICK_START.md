# Quick Start - WhatsApp Agentforce Handler

## ✅ Function Status: READY AND TESTED

The function has been tested and works correctly:
- ✅ Salesforce OAuth authentication
- ✅ Agentforce session creation
- ✅ Agentforce message handling
- ✅ Twilio webhook simulation

## 🚀 Start the Function Locally

### Option 1: Using the startup script

```bash
cd whatsapp-agentforce-handler
./start_with_ngrok.sh
```

This will:
1. Start Flask server on port 8080
2. Start ngrok tunnel
3. Display the webhook URL

### Option 2: Manual start

**Terminal 1 - Start Flask:**
```bash
cd whatsapp-agentforce-handler
export $(cat .env | grep -v '^#' | xargs)
export FLASK_APP=main.py
python3 -m flask run --host=0.0.0.0 --port=8080
```

**Terminal 2 - Start ngrok:**
```bash
ngrok http 8080
```

Copy the `https://` URL from ngrok (e.g., `https://abc123.ngrok.io`)

## 📝 Configure Twilio Webhook

1. **Go to Twilio Console:**
   - https://console.twilio.com/us1/develop/sms/setup/whatsapp/learn
   - Or: https://console.twilio.com/ → Messaging → Settings → WhatsApp Sandbox

2. **Set Webhook URL:**
   - Find "When a message comes in"
   - Enter your ngrok URL (e.g., `https://abc123.ngrok.io`)
   - Set HTTP Method: **POST**
   - Click **Save**

3. **Test:**
   - Send a WhatsApp message to: **+1 415 523-8886**
   - Send: "egyptian tax details"
   - You should get a response from Agentforce!

## 🧪 Test Locally First

Before configuring Twilio, test the function:

```bash
cd whatsapp-agentforce-handler
python3 test_twilio_webhook.py
```

## 📋 Current Status

- ✅ Function code: Ready
- ✅ Tests: All passing
- ✅ Local testing: Working
- ⏳ Deployment: Use ngrok for now, or deploy to Cloud Run

## 🔧 Troubleshooting

**If ngrok doesn't start:**
```bash
# Check if port 8080 is free
lsof -i :8080

# Kill any existing Flask/ngrok processes
pkill -f flask
pkill -f ngrok

# Start fresh
./start_with_ngrok.sh
```

**If Twilio webhook doesn't work:**
1. Verify ngrok URL is accessible: `curl https://your-ngrok-url.ngrok.io/`
2. Check Flask logs: `tail -f /tmp/flask_server.log`
3. Check ngrok logs: Visit http://localhost:4040

**To stop services:**
```bash
pkill -f flask
pkill -f ngrok
```







