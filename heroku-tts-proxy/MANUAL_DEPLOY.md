# 🚀 Heroku Manual Deployment Guide

## ✅ **Quick Deployment (3 Steps)**

### **Step 1: Login to Heroku**

```bash
heroku login
```

This will open a browser - complete the login there.

---

### **Step 2: Create App and Deploy**

```bash
cd heroku-tts-proxy

# Create Heroku app
APP_NAME="tts-proxy-$(date +%s)"
heroku create $APP_NAME

# Generate API key
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "API Key: $API_KEY"

# Set environment variables (replace YOUR_GOOGLE_CLOUD_API_KEY)
heroku config:set \
  GOOGLE_CLOUD_API_KEY="YOUR_GOOGLE_CLOUD_API_KEY" \
  API_KEY="$API_KEY" \
  --app $APP_NAME

# Initialize git and deploy
git init
git add .
git commit -m "Initial deployment"
git push heroku main

# Scale dyno
heroku ps:scale web=1 --app $APP_NAME
```

---

### **Step 3: Get Your App URL**

```bash
heroku info --app $APP_NAME
```

Or check: `https://dashboard.heroku.com/apps/$APP_NAME`

---

## 🧪 **Test**

```bash
# Health check
curl https://$APP_NAME.herokuapp.com/health

# TTS test
curl -X POST https://$APP_NAME.herokuapp.com/synthesize \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"text":"مرحبا","return_type":"url"}'
```

---

## 📝 **Salesforce Configuration**

1. **Remote Site Settings:**
   - URL: `https://$APP_NAME.herokuapp.com`

2. **Component Properties:**
   - Cloud Run TTS Service Url: `https://$APP_NAME.herokuapp.com/synthesize`
   - Cloud Run TTS API Key: `$API_KEY`

---

**That's it! No IAM, no policies, just works!** 🎉















