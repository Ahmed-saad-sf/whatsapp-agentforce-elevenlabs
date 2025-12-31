# Voice Message Handling Fix

## Issues Fixed

1. **Better Encoding Detection**: WhatsApp voice messages come as OGG/Opus format, now properly detected
2. **Improved Error Logging**: Added detailed logging at each step to identify failures
3. **Better Error Handling**: More specific error messages for debugging
4. **AMR Support**: Added support for AMR format (sometimes used by WhatsApp)
5. **Timeout Handling**: Added timeouts to prevent hanging requests

## Changes Made

### `download_twilio_media()`
- Added detailed logging
- Better error messages
- Timeout handling

### `google_stt()`
- Improved encoding detection (defaults to OGG_OPUS for WhatsApp)
- Better error logging with response details
- Disabled `enableWordTimeOffsets` to avoid API errors
- Added support for AMR format
- More detailed exception messages

## Testing

After deployment, test by:
1. Sending a voice message via WhatsApp to +1 415 523-8886
2. Check Heroku logs: `heroku logs --tail --app whatsapp-agentforce-handler`
3. Look for detailed error messages if it fails

## Common Issues

1. **Encoding Mismatch**: If STT fails, check the content type in logs
2. **API Key Issues**: Verify GOOGLE_CLOUD_API_KEY is set correctly
3. **Media Download**: Check if Twilio media URL is accessible
4. **Timeout**: Voice processing may take longer, ensure timeout is sufficient

## Next Steps

If voice messages still fail:
1. Check Heroku logs for specific error
2. Verify Google Cloud API key has Speech-to-Text API enabled
3. Test STT API directly with a sample audio file
4. Check Twilio media URL format







