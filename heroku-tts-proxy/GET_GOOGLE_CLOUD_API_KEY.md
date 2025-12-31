# 🔑 How to Get Google Cloud TTS API Key

## ⚠️ **Issue**

OAuth Client IDs (starting with `GOCSPX-`) are different from **Google Cloud API Keys**.

Google Cloud API keys:
- Start with `AIza` (for REST API keys)
- Are ~39 characters long
- Example format: `AIzaSy...EXAMPLE_KEY...1234567` (replace with your actual key)

---

## 🚀 **How to Get API Key**

### **Step 1: Go to Google Cloud Console**

1. Open: https://console.cloud.google.com/
2. Select your Google Cloud project

### **Step 2: Enable Text-to-Speech API**

1. Go to **APIs & Services** → **Library**
2. Search for: **"Cloud Text-to-Speech API"**
3. Click **Enable**

### **Step 3: Create API Key**

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **API Key**
3. Copy the API key (starts with `AIza...`)

### **Step 4: Restrict API Key (Recommended)**

1. Click on the API key you just created
2. Under **API restrictions**, select **Restrict key**
3. Choose **Cloud Text-to-Speech API**
4. Click **Save**

---

## 📝 **Set API Key in Heroku**

Once you have the correct API key (starts with `AIza`), run:

```bash
heroku config:set GOOGLE_CLOUD_API_KEY="YOUR_AIza_API_KEY" --app your-tts-proxy-app-name
```

---

## ✅ **Current Status**

- ✅ Heroku app deployed
- ✅ API key authentication working
- ⏳ **Need:** Valid Google Cloud API key (starts with `AIza`)

---

**Once you set the correct API key, everything will work!** 🚀















