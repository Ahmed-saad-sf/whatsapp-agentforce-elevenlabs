# Connected App Setup for Production

## ⚠️ Important: My Domain Required

The **client_credentials** OAuth flow requires your Salesforce org's **My Domain URL**, not `login.salesforce.com`.

## Finding Your My Domain URL

### Option 1: From Salesforce Setup
1. Go to: **Setup → My Domain**
2. Your My Domain URL will be displayed (e.g., `https://your-domain.my.salesforce.com`)

### Option 2: From Browser
1. Log into your Salesforce org
2. Look at the URL in your browser
3. It should be something like: `https://your-domain.my.salesforce.com` or `https://your-domain.lightning.force.com`

### Option 3: From Salesforce CLI
```bash
sf org display --json | jq -r '.result.instanceUrl'
```

## Enable Client Credentials Flow

1. Go to: **Setup → App Manager**
2. Find your Connected App
3. Click **Edit**
4. Go to **OAuth Settings**
5. Check **"Enable Client Credentials Flow"**
6. **Save**

## Test Connected App

Run the test script with your My Domain URL:

```bash
# Set your My Domain URL
export SALESFORCE_INSTANCE_URL=https://your-domain.my.salesforce.com

# Run test
python3 test_connected_app.py
```

Or test directly:

```bash
python3 test_connected_app.py
# It will prompt you to provide the My Domain URL
```

## Expected Result

If configured correctly, you should see:
```
✅ SUCCESS!
   Token Type: Bearer
   Access Token: 00D...
   Instance URL: https://your-domain.my.salesforce.com
```

## Common Issues

### Error: "request not supported on this domain"
- **Cause**: Using `login.salesforce.com` instead of My Domain URL
- **Solution**: Use your org's My Domain URL (e.g., `https://your-domain.my.salesforce.com`)

### Error: "invalid_client_id"
- **Cause**: Consumer Key is incorrect
- **Solution**: Verify Consumer Key in Setup → App Manager → Connected App

### Error: "invalid_client"
- **Cause**: Consumer Secret is incorrect or doesn't match Consumer Key
- **Solution**: Verify Consumer Secret matches the Consumer Key

### Error: "invalid_grant"
- **Cause**: Client Credentials Flow not enabled
- **Solution**: Enable "Client Credentials Flow" in Connected App OAuth Settings

## Configuration for Google Cloud Function

Once you have your My Domain URL, set it in the environment:

```bash
SALESFORCE_INSTANCE_URL=https://your-domain.my.salesforce.com
SALESFORCE_CONSUMER_KEY=your_consumer_key_here
SALESFORCE_CONSUMER_SECRET=your_consumer_secret_here
```

## Production vs Sandbox

- **Production**: Use your production org's My Domain URL
- **Sandbox**: Use your sandbox org's My Domain URL (usually `https://your-domain--sandboxname.my.salesforce.com`)

Both use the same OAuth flow, just different My Domain URLs.







