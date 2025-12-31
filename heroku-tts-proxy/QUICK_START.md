# 🚀 Heroku Quick Start

## **Step 1: Login to Heroku**

Run this command in your terminal:

```bash
heroku login
```

This will:
1. Open your default browser
2. Show a Heroku login page
3. Complete the login there
4. Return to terminal when done

**Or if browser doesn't open:**
```bash
heroku login -i
```
Then enter your email and password.

---

## **Step 2: Deploy (Copy & Paste)**

After login, run these commands:

```bash
cd /Users/ahmed.saad/Documents/E-Finance_Tax_Advisor/heroku-tts-proxy

# Create app
APP_NAME="tts-proxy-$(date +%s)"
heroku create $APP_NAME

# Generate API key
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "🔑 Save this API Key: $API_KEY"

# Set environment variables
# IMPORTANT: Replace YOUR_GOOGLE_CLOUD_API_KEY with your actual key
heroku config:set \
  GOOGLE_CLOUD_API_KEY="YOUR_GOOGLE_CLOUD_API_KEY" \
  API_KEY="$API_KEY" \
  --app $APP_NAME

# Deploy
git init
git add .
git commit -m "Initial deployment"
git push heroku main

# Scale dyno
heroku ps:scale web=1 --app $APP_NAME

# Get app URL
echo "🌐 Your app URL: https://$APP_NAME.herokuapp.com"
```

---

## **Step 3: Test**

```bash
# Health check
curl https://$APP_NAME.herokuapp.com/health

# TTS test (replace $API_KEY with the key from Step 2)
curl -X POST https://$APP_NAME.herokuapp.com/synthesize \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"text":"مرحبا","return_type":"url"}'
```

---

## **Step 4: Configure Salesforce**

1. **Remote Site Settings:**
   - URL: `https://$APP_NAME.herokuapp.com`

2. **Component Properties:**
   - Cloud Run TTS Service Url: `https://$APP_NAME.herokuapp.com/synthesize`
   - Cloud Run TTS API Key: `$API_KEY`

---

**That's it! No IAM, no policies, just works!** 🎉















