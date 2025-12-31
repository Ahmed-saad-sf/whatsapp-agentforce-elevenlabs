# 🚀 Deploy Now - Simple 2-Step Process

## **Step 1: Login to Heroku**

Open your terminal and run:

```bash
heroku login
```

**This will:**
1. Open your browser automatically
2. Show Heroku login page
3. Complete login there
4. Return to terminal

**Verify login:**
```bash
heroku auth:whoami
```
Should show your email address.

---

## **Step 2: Run Deployment Script**

After login, run:

```bash
cd /Users/ahmed.saad/Documents/E-Finance_Tax_Advisor/heroku-tts-proxy
./deploy-after-login.sh
```

**The script will:**
1. ✅ Check you're logged in
2. ✅ Create Heroku app
3. ✅ Generate API key
4. ✅ Ask for your Google Cloud TTS API key
5. ✅ Deploy the app
6. ✅ Show you the app URL and API key

**That's it!** Takes about 2 minutes total.

---

## **After Deployment**

You'll get:
- **App URL:** `https://tts-proxy-XXXXX.herokuapp.com`
- **API Key:** Generated automatically

Then configure Salesforce:
1. Remote Site: `https://tts-proxy-XXXXX.herokuapp.com`
2. Component Properties:
   - Service URL: `https://tts-proxy-XXXXX.herokuapp.com/synthesize`
   - API Key: (from script output)

---

**No IAM, no policies, just works!** 🎉















