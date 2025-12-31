# WhatsApp-Agentforce Integration with ElevenLabs

This repository contains the integration code for connecting WhatsApp messages to Salesforce Agentforce with voice support using ElevenLabs for Speech-to-Text (STT) and Text-to-Speech (TTS).

## 🏗️ Architecture

```
WhatsApp (Twilio) → Heroku Flask App → Salesforce Agentforce API → ElevenLabs (STT/TTS)
```

## 📦 Components

### 1. WhatsApp-Agentforce Handler (`whatsapp-agentforce-handler/`)
- Flask application running on Heroku
- Handles incoming WhatsApp webhooks from Twilio
- Processes text and voice messages
- Integrates with Salesforce Agentforce API
- Uses ElevenLabs for voice transcription and synthesis

### 2. Heroku TTS Proxy (`heroku-tts-proxy/`)
- Proxy service for Google Cloud Text-to-Speech API
- Bypasses CSP restrictions
- Provides audio caching

## 🚀 Quick Start

### Prerequisites

1. **Twilio Account** with WhatsApp enabled
2. **Salesforce Org** with Agentforce configured
3. **ElevenLabs Account** with API key
4. **Heroku Account** (for deployment)

### Setup Instructions

#### 1. Configure WhatsApp-Agentforce Handler

1. Navigate to `whatsapp-agentforce-handler/`
2. Set the following environment variables in Heroku:

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

# ElevenLabs Configuration
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_elevenlabs_voice_id
```

3. Deploy to Heroku:
```bash
cd whatsapp-agentforce-handler
heroku create your-app-name
git push heroku main
```

#### 2. Configure Heroku TTS Proxy (Optional)

If you need Google Cloud TTS as a fallback:

1. Navigate to `heroku-tts-proxy/`
2. Set environment variable:
```bash
GOOGLE_CLOUD_API_KEY=your_google_cloud_api_key
```
3. Deploy to Heroku:
```bash
cd heroku-tts-proxy
heroku create your-tts-proxy-name
git push heroku main
```

#### 3. Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to **Messaging → Settings → WhatsApp Sandbox**
3. Set **Webhook URL** to your Heroku app URL: `https://your-app-name.herokuapp.com/`
4. Set **HTTP Method** to `POST`
5. Click **Save**

## 📚 Documentation

- **WhatsApp Handler**: See `whatsapp-agentforce-handler/README.md` and `DEPLOYMENT_GUIDE.md`
- **TTS Proxy**: See `heroku-tts-proxy/README.md`
- **Connected App Setup**: See `whatsapp-agentforce-handler/CONNECTED_APP_SETUP.md`

## 🔧 Configuration

### Salesforce Connected App Setup

1. Create a Connected App in Salesforce
2. Enable **Client Credentials Flow**
3. Get Consumer Key and Consumer Secret
4. Use your org's My Domain URL (not `login.salesforce.com`)

See `whatsapp-agentforce-handler/CONNECTED_APP_SETUP.md` for detailed instructions.

### Agentforce Agent ID

1. Go to Salesforce Setup → Agentforce
2. Find your agent
3. Copy the Agent ID (starts with `0XxKB...`)

### ElevenLabs Setup

1. Sign up at [ElevenLabs](https://elevenlabs.io/)
2. Get your API key from the dashboard
3. Choose a voice ID or create a custom voice
4. Set `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` environment variables

## 🧪 Testing

### Test Text Message
Send a WhatsApp message to your Twilio WhatsApp number:
```
Hello, how can you help me?
```

### Test Voice Message
Send a voice message to your Twilio WhatsApp number. The app will:
1. Transcribe the audio using ElevenLabs STT
2. Send the text to Agentforce
3. Generate a voice response using ElevenLabs TTS
4. Send the audio back via WhatsApp

## 📝 Environment Variables Reference

### WhatsApp-Agentforce Handler

| Variable | Description | Required |
|----------|-------------|----------|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | Yes |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | Yes |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp number | Yes |
| `AGENTFORCE_AGENT_ID` | Salesforce Agentforce Agent ID | Yes |
| `SALESFORCE_CONSUMER_KEY` | Salesforce Connected App Consumer Key | Yes |
| `SALESFORCE_CONSUMER_SECRET` | Salesforce Connected App Consumer Secret | Yes |
| `SALESFORCE_INSTANCE_URL` | Salesforce My Domain URL | Yes |
| `ELEVENLABS_API_KEY` | ElevenLabs API Key | Yes |
| `ELEVENLABS_VOICE_ID` | ElevenLabs Voice ID | Yes |

### Heroku TTS Proxy

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLOUD_API_KEY` | Google Cloud TTS API Key | Yes |
| `API_KEY` | Optional API key for authentication | No |

## 🔒 Security Best Practices

1. **Never commit credentials** - Use environment variables
2. **Use Heroku Config Vars** - Store secrets securely
3. **Rotate credentials regularly** - Update API keys periodically
4. **Restrict API keys** - Limit scope and IP addresses where possible
5. **Enable logging** - Monitor for suspicious activity

## 🐛 Troubleshooting

### Common Issues

1. **"Failed to get Salesforce token"**
   - Verify Consumer Key and Secret are correct
   - Check Connected App has Client Credentials Flow enabled
   - Ensure SALESFORCE_INSTANCE_URL uses My Domain URL

2. **"No transcription found"**
   - Verify ElevenLabs API key is valid
   - Check audio format is supported

3. **"Session not found"**
   - This is normal for first message - session will be created automatically

### View Logs

```bash
# WhatsApp Handler logs
heroku logs --tail --app your-app-name

# TTS Proxy logs
heroku logs --tail --app your-tts-proxy-name
```

## 📄 License

This code is provided as-is for customer use.

## 🤝 Support

For issues or questions, please contact your implementation team.

