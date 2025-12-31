# 🔐 Heroku Login Instructions

## **Option 1: Browser Login (Recommended)**

In your terminal, run:
```bash
heroku login
```

Then:
1. **Press Enter** (or any key) when prompted
2. Browser will open automatically
3. Complete login in browser
4. Return to terminal

**Verify:**
```bash
heroku auth:whoami
```
Should show your email.

---

## **Option 2: Interactive Login (Email/Password)**

In your terminal, run:
```bash
heroku login -i
```

Then enter:
1. Your Heroku email
2. Your Heroku password

**Verify:**
```bash
heroku auth:whoami
```

---

## **After Login**

Once logged in, run:

```bash
cd /Users/ahmed.saad/Documents/E-Finance_Tax_Advisor/heroku-tts-proxy
./deploy-after-login.sh
```

This will deploy everything automatically!

---

**Need a Heroku account?** Sign up at: https://signup.heroku.com















