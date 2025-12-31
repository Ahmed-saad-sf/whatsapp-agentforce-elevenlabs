# WhatsApp Agentforce Handler - Deployment Status

## ✅ Function Status: READY FOR DEPLOYMENT

All tests passed successfully:
- ✅ Flask app imports correctly
- ✅ Salesforce OAuth authentication works
- ✅ Agentforce session creation works
- ✅ Agentforce message sending works
- ✅ Twilio webhook simulation works
- ✅ End-to-end integration test passes

## 📋 Deployment Options

### Option 1: Google Cloud Run (Recommended)
The function is ready to deploy to Cloud Run. If you encounter build issues, try:

```bash
cd whatsapp-agentforce-handler
gcloud run deploy whatsapp-agentforce-handler \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --timeout 540 \
  --memory 512Mi \
  --max-instances 10 \
  --set-env-vars "TWILIO_ACCOUNT_SID=your_twilio_account_sid,TWILIO_AUTH_TOKEN=your_twilio_auth_token,TWILIO_WHATSAPP_FROM=whatsapp:+14155238886,AGENTFORCE_AGENT_ID=your_agentforce_agent_id,SALESFORCE_CONSUMER_KEY=your_consumer_key,SALESFORCE_CONSUMER_SECRET=your_consumer_secret,SALESFORCE_INSTANCE_URL=https://your-domain.my.salesforce.com,ELEVENLABS_API_KEY=your_elevenlabs_api_key,ELEVENLABS_VOICE_ID=your_elevenlabs_voice_id" \
  --project your-google-cloud-project-id
```

### Option 2: Heroku
Use the `deploy_heroku.sh` script (requires Heroku CLI login).

### Option 3: AWS Lambda
Convert to AWS Lambda format (see `azure_function.py` as reference).

### Option 4: Manual Testing
Run locally and use ngrok to expose it:

```bash
# Terminal 1: Run the function
cd whatsapp-agentforce-handler
python3 test_local.sh

# Terminal 2: Expose with ngrok
ngrok http 8080
```

Then use the ngrok URL as your Twilio webhook.

## 🧪 Testing

### Local Testing
```bash
cd whatsapp-agentforce-handler
python3 test_twilio_webhook.py
python3 test_end_to_end.py
```

### Test with Real Twilio Webhook
Once deployed, configure Twilio:
1. Go to: https://console.twilio.com/
2. Navigate to: Messaging → Settings → WhatsApp Sandbox
3. Set Webhook URL: `https://your-deployed-url/`
4. Set HTTP Method: POST
5. Save

Then send a WhatsApp message to your Twilio sandbox number.

## 📝 Next Steps

1. Deploy the function using one of the options above
2. Get the deployment URL
3. Configure Twilio webhook with the URL
4. Test by sending a WhatsApp message
5. Monitor logs for any issues

## 🔧 Troubleshooting

If Cloud Run deployment fails:
- Check build logs: `gcloud builds list --limit=1`
- Ensure all APIs are enabled
- Check IAM permissions
- Try deploying from Cloud Console UI

If function doesn't respond:
- Check environment variables are set correctly
- Verify Salesforce credentials
- Check Agentforce agent ID is correct
- Review Cloud Run logs







