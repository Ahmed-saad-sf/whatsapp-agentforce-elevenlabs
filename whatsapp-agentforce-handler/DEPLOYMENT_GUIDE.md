# Deployment Guide: WhatsApp → Agentforce Integration

## Prerequisites

1. Google Cloud Project with billing enabled
2. Twilio account with WhatsApp enabled
3. Salesforce org with Agentforce configured
4. Google Cloud API key for Speech-to-Text and Text-to-Speech

## Step 1: Configure Environment Variables

Create a `.env` file in the `whatsapp-agentforce-handler` directory:

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Agentforce Configuration
AGENTFORCE_AGENT_ID=your_agentforce_agent_id
SALESFORCE_CONSUMER_KEY=your_salesforce_consumer_key
SALESFORCE_CONSUMER_SECRET=your_salesforce_consumer_secret
SALESFORCE_INSTANCE_URL=https://your-domain.my.salesforce.com
# Note: Using client_credentials OAuth flow (no username/password needed)

# ElevenLabs Configuration (for voice messages)
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_elevenlabs_voice_id
```

## Step 2: Deploy to Google Cloud Functions

### Option A: Using Deployment Script

```bash
cd whatsapp-agentforce-handler
./deploy.sh
```

### Option B: Manual Deployment

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
  --set-env-vars="TWILIO_ACCOUNT_SID=...,TWILIO_AUTH_TOKEN=...,AGENTFORCE_AGENT_ID=...,SALESFORCE_CONSUMER_KEY=...,SALESFORCE_CONSUMER_SECRET=...,SALESFORCE_INSTANCE_URL=...,SALESFORCE_USERNAME=...,SALESFORCE_PASSWORD=...,SALESFORCE_SECURITY_TOKEN=...,GOOGLE_CLOUD_API_KEY=..."
```

## Step 3: Get Function URL

```bash
gcloud functions describe whatsapp-agentforce-handler \
  --gen2 \
  --region=us-central1 \
  --format='value(serviceConfig.uri)'
```

Copy the URL - you'll need it for Twilio webhook configuration.

## Step 4: Configure Twilio Webhook

1. Go to: https://console.twilio.com/
2. Navigate to: **Messaging → Settings → WhatsApp Sandbox**
3. In the **"When a message comes in"** section:
   - **Webhook URL**: Paste your function URL
   - **HTTP Method**: POST
4. Click **Save**

## Step 5: Test the Integration

### Test Text Message

Send a WhatsApp message to your Twilio WhatsApp number:
```
Hello, how can you help me?
```

### Test Voice Message

Send a voice message to your Twilio WhatsApp number.

## Troubleshooting

### Check Function Logs

```bash
gcloud functions logs read whatsapp-agentforce-handler \
  --gen2 \
  --region=us-central1 \
  --limit=50
```

### Common Issues

1. **"Failed to get Salesforce token"**
   - Verify Consumer Key and Consumer Secret are correct
   - Check that Connected App has "Enable Client Credentials Flow" enabled
   - Verify SALESFORCE_INSTANCE_URL is correct (use your org's My Domain URL)
   - Example: `https://your-domain.my.salesforce.com` or `https://your-instance.salesforce.com`

3. **"No transcription found"**
   - Verify Google Cloud API key is valid
   - Check audio format is supported

4. **"Session not found"**
   - This is normal for first message - session will be created automatically

## Security Best Practices

1. **Use Secret Manager** for sensitive credentials:
   ```bash
   # Create secrets
   echo -n "your-password" | gcloud secrets create salesforce-password --data-file=-
   
   # Grant access
   gcloud secrets add-iam-policy-binding salesforce-password \
     --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
     --role="roles/secretmanager.secretAccessor"
   ```

2. **Enable VPC** for additional security (optional)

3. **Set up monitoring** and alerts

4. **Rotate credentials** regularly

## Monitoring

### View Metrics

```bash
gcloud functions describe whatsapp-agentforce-handler \
  --gen2 \
  --region=us-central1 \
  --format='value(serviceConfig.availableMemory)'
```

### Set Up Alerts

1. Go to Cloud Monitoring → Alerting
2. Create alert policy for function errors
3. Set notification channels

