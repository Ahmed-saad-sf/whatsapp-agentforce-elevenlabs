# Enhanced Error Logging for Agentforce API

## Changes Made

I've enhanced error logging in `main.py` to capture detailed error information when Agentforce API calls fail. This will help diagnose why users are receiving "Sorry, I encountered an error. Please try again."

## Improvements

### 1. Enhanced `send_to_agentforce()` Error Handling
- **Before**: Generic `response.raise_for_status()` that only logged HTTP status codes
- **After**: 
  - Logs full error response body (JSON or text)
  - Logs request details (session ID, sequence ID, message length)
  - Logs response details before parsing
  - Handles empty messages and missing message arrays with warnings

### 2. Enhanced `get_agentforce_session()` Error Handling
- **Before**: Generic error on session creation failure
- **After**:
  - Logs full error response from Agentforce
  - Logs agent ID and external session key
  - Provides detailed error messages

### 3. Enhanced `handle_text_message()` Error Handling
- **Before**: Generic error logging
- **After**:
  - Logs error type (Exception class name)
  - Logs message text (first 200 chars)
  - Logs phone number
  - Full stack trace with `exc_info=True`

## How to Check Logs

### Option 1: Heroku Dashboard (Recommended)
1. Go to: https://dashboard.heroku.com/apps/whatsapp-agentforce-elevenlabs
2. Click on "More" → "View logs"
3. Look for lines containing:
   - `❌ Agentforce API error`
   - `❌ Error handling text message`
   - `❌ Agentforce session creation error`

### Option 2: Heroku CLI
```bash
cd whatsapp-agentforce-handler
heroku logs --tail --app whatsapp-agentforce-elevenlabs --num 500 | grep -i "error\|exception\|agentforce"
```

### Option 3: Filter Recent Errors
```bash
heroku logs --app whatsapp-agentforce-elevenlabs --num 500 | grep -A 10 "❌"
```

## What to Look For

When investigating the error "ازاي اتجنب الازدواج الضريبي" → "Sorry, I encountered an error":

1. **Check for Agentforce API errors**:
   - Look for `❌ Agentforce API error: Status: XXX`
   - Common status codes:
     - `401`: Authentication/OAuth token issue
     - `400`: Bad request (invalid payload, sequence ID issue)
     - `404`: Session not found
     - `500`: Agentforce server error

2. **Check for session creation errors**:
   - Look for `❌ Agentforce session creation error`
   - May indicate OAuth token expiration or invalid agent ID

3. **Check for OAuth token errors**:
   - Look for `Salesforce OAuth failed`
   - May indicate expired or invalid credentials

4. **Check response structure**:
   - Look for `⚠️ No messages in Agentforce response`
   - May indicate Agentforce returned success but no message content

## Next Steps

1. **Deploy the changes**:
   ```bash
   git push heroku HEAD:main
   ```

2. **Test with the same message**:
   - Send: "ازاي اتجنب الازدواج الضريبي"
   - Check logs immediately after

3. **Review error details**:
   - The enhanced logging will show exactly what Agentforce returned
   - This will help identify if it's:
     - An authentication issue
     - A session issue
     - An API payload issue
     - An Agentforce service issue

## Expected Log Output

When an error occurs, you should now see logs like:

```
❌ Agentforce API error: Status: 400, Response: {"error": "Invalid sequenceId", "details": "..."}
❌ Error handling text message (HTTPError): Agentforce API returned 400: Status: 400, Response: {...}
   Message text: ازاي اتجنب الازدواج الضريبي
   From number: +971586672299
```

This will help pinpoint the exact issue.




