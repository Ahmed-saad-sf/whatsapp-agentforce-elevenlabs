# WhatsApp → Agentforce Integration Handler

Google Cloud Function to handle Twilio WhatsApp webhooks and integrate with Agentforce.

## Features

- ✅ Text message handling
- ✅ Voice message handling (STT → Agentforce → TTS)
- ✅ Session management
- ✅ Multi-language support (Arabic/English)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

### 3. Deploy to Google Cloud Functions

```bash
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
  --set-env-vars="TWILIO_ACCOUNT_SID=...,TWILIO_AUTH_TOKEN=...,AGENTFORCE_AGENT_ID=...,SALESFORCE_CONSUMER_KEY=...,SALESFORCE_CONSUMER_SECRET=...,SALESFORCE_INSTANCE_URL=...,GOOGLE_CLOUD_API_KEY=..."
```

### 4. Configure Twilio Webhook

1. Go to Twilio Console → Messaging → Settings → WhatsApp Sandbox
2. Set Webhook URL to your function URL
3. Set HTTP Method to POST
4. Save

## Local Testing

### Using Functions Framework

```bash
functions-framework --target=handle_webhook --port=8080
```

### Test Text Message

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+971586672299",
    "Body": "Hello, how can you help me?",
    "MessageSid": "test123",
    "NumMedia": "0"
  }'
```

### Test Voice Message

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+971586672299",
    "MessageSid": "test456",
    "NumMedia": "1",
    "MediaUrl0": "https://api.twilio.com/2010-04-01/Accounts/.../Media/...",
    "MediaContentType0": "audio/ogg; codecs=opus"
  }'
```

## Architecture

See `../WHATSAPP_AGENTFORCE_ARCHITECTURE.md` for detailed architecture documentation.

## Notes

- Voice messages currently send text-only responses (voice sending requires additional Twilio Media API setup)
- Sessions are stored in-memory (consider Redis/Firestore for production)
- Error handling includes fallback to text messages







