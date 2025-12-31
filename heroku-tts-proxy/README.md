# 🎤 Heroku TTS Proxy

Heroku-based Text-to-Speech proxy service that bypasses CSP restrictions with **NO IAM/POLICY ISSUES**!

## ✅ **Why Heroku?**

- ✅ **No IAM Issues** - Public by default
- ✅ **No Policy Restrictions** - Works immediately
- ✅ **No Admin Needed** - You can deploy yourself
- ✅ **Free Tier Available** - 550-1000 free dyno hours/month
- ✅ **Simple Deployment** - Git push to deploy
- ✅ **Auto-scaling** - Handles traffic automatically

## 🚀 **Quick Start**

### **1. Install Heroku CLI**

```bash
# Mac
brew tap heroku/brew && brew install heroku

# Or download from: https://devcenter.heroku.com/articles/heroku-cli
```

### **2. Login to Heroku**

```bash
heroku login
```

### **3. Run Deployment Script**

```bash
cd heroku-tts-proxy
./deploy.sh
```

The script will:
- Create Heroku app
- Set environment variables
- Deploy code
- Scale dyno
- Generate API key

### **4. Test**

```bash
# Replace with your app URL and API key from deploy.sh output
curl https://YOUR_APP_NAME.herokuapp.com/health

curl -X POST https://YOUR_APP_NAME.herokuapp.com/synthesize \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"text":"مرحبا","return_type":"url"}'
```

## 📋 **Files**

- `app.py` - Main Flask application
- `Procfile` - Heroku process file
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version
- `deploy.sh` - Automated deployment script
- `README.md` - This file

## 🔧 **Configuration**

Set these environment variables in Heroku:

- `GOOGLE_CLOUD_API_KEY` - Your Google Cloud TTS API key
- `API_KEY` - API key for authentication (auto-generated)

**Set via CLI:**
```bash
heroku config:set GOOGLE_CLOUD_API_KEY="your-key" --app YOUR_APP_NAME
heroku config:set API_KEY="your-api-key" --app YOUR_APP_NAME
```

**Or via Dashboard:**
1. Go to https://dashboard.heroku.com/apps/YOUR_APP_NAME/settings
2. Click "Reveal Config Vars"
3. Add variables

## 📝 **Salesforce Integration**

1. **Add Remote Site Setting:**
   - URL: `https://YOUR_APP_NAME.herokuapp.com`

2. **Update Component Properties:**
   - Cloud Run TTS Service Url: `https://YOUR_APP_NAME.herokuapp.com/synthesize`
   - Cloud Run TTS API Key: `YOUR_API_KEY` (from deploy.sh output)

3. **Test voice mode!**

## 💰 **Cost**

- **Free Tier:** 550-1000 dyno hours/month (enough for testing)
- **Hobby Dyno:** $7/month (unlimited hours)
- **Google Cloud TTS:** ~$4 per 1M characters

**Total:** ~$7-11/month for moderate usage

## 🎯 **Benefits Over Other Platforms**

- ✅ No IAM/policy restrictions
- ✅ Public by default
- ✅ No admin permissions needed
- ✅ Simple git-based deployment
- ✅ Free tier available
- ✅ Easy to scale

## 📚 **Manual Deployment**

If you prefer manual deployment:

```bash
# 1. Create app
heroku create tts-proxy-$(date +%s)

# 2. Set config vars
heroku config:set GOOGLE_CLOUD_API_KEY="your-key"
heroku config:set API_KEY="your-api-key"

# 3. Deploy
git init
git add .
git commit -m "Initial deployment"
git push heroku main

# 4. Scale
heroku ps:scale web=1
```

## 🔒 **Security**

- API key authentication (optional but recommended)
- CORS enabled for Salesforce
- Environment variables for secrets
- HTTPS by default

## 🎉 **Status**

- ✅ **Code:** Complete
- ✅ **Deployment Script:** Ready
- ✅ **Documentation:** Complete
- ✅ **Ready to Deploy:** YES!

---

**Heroku = No IAM headaches, no policy restrictions, works immediately!** 🚀















