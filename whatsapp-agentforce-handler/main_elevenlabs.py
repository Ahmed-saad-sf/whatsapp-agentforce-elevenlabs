"""
WhatsApp → Agentforce Integration Handler
Google Cloud Function to handle Twilio WhatsApp webhooks
"""

import os
import json
import base64
import requests
import logging
import io
import subprocess
import tempfile
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from flask import Flask, request as flask_request, Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Configuration from environment variables
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

AGENTFORCE_AGENT_ID = os.environ.get('AGENTFORCE_AGENT_ID', '0XxKB000000La8H0AS')
SALESFORCE_CONSUMER_KEY = os.environ.get('SALESFORCE_CONSUMER_KEY')
SALESFORCE_CONSUMER_SECRET = os.environ.get('SALESFORCE_CONSUMER_SECRET')
SALESFORCE_INSTANCE_URL = os.environ.get('SALESFORCE_INSTANCE_URL')

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID')

# API Endpoints
AGENTFORCE_API_BASE = 'https://api.salesforce.com/einstein/ai-agent/v1'
ELEVENLABS_API_BASE = 'https://api.elevenlabs.io/v1'
# Note: ElevenLabs doesn't have STT API, so we'll keep Google STT for speech-to-text
ELEVENLABS_TTS_ENDPOINT = f'{ELEVENLABS_API_BASE}/text-to-speech/{ELEVENLABS_VOICE_ID}'

# In-memory session storage (can be upgraded to Redis/Firestore)
sessions: Dict[str, Dict] = {}


@app.route('/audio/<audio_id>', methods=['GET'])
def serve_audio(audio_id):
    """Serve audio file for WhatsApp media"""
    if audio_id not in audio_cache:
        return Response('Audio not found', status=404)
    
    audio_data = audio_cache[audio_id]
    
    return Response(
        audio_data['data'],
        mimetype=audio_data['content_type'],
        headers={
            'Content-Type': audio_data['content_type'],
            'Content-Disposition': 'inline; filename="voice.mp3"',
            'Cache-Control': 'no-cache'
        }
    )


@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    """
    Main entry point for Cloud Run / Cloud Functions
    Handles Twilio WhatsApp webhooks
    """
    try:
        # Parse request
        if flask_request.method == 'GET':
            # Webhook verification
            return handle_verification()
        
        # Get webhook data
        # Twilio sends form-encoded data (application/x-www-form-urlencoded)
        if flask_request.content_type and 'application/json' in flask_request.content_type:
            data = flask_request.get_json(silent=True) or {}
        else:
            # Twilio sends form-encoded data
            data = flask_request.form.to_dict()
        
        logger.info(f"Received webhook: {json.dumps(data, indent=2)}")
        
        # Extract message details
        from_number = data.get('From', '').replace('whatsapp:', '').strip()
        # Ensure number starts with +
        if from_number and not from_number.startswith('+'):
            from_number = '+' + from_number.lstrip('+')
        message_sid = data.get('MessageSid', '')
        num_media = int(data.get('NumMedia', '0'))
        
        if num_media > 0:
            # Voice message
            media_url = data.get('MediaUrl0', '')
            media_content_type = data.get('MediaContentType0', '')
            logger.info(f"Voice message detected: {media_url}")
            return handle_voice_message(from_number, message_sid, media_url, media_content_type)
        else:
            # Text message
            message_text = data.get('Body', '')
            logger.info(f"Text message: {message_text}")
            return handle_text_message(from_number, message_sid, message_text)
    
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        return Response(json.dumps({'error': 'Internal server error'}), status=500, mimetype='application/json')


def handle_verification():
    """Handle webhook verification (GET request)"""
    return Response('OK', status=200)


def handle_text_message(from_number: str, message_sid: str, message_text: str):
    """Handle text message from WhatsApp"""
    try:
        # Get Agentforce response
        response_text = send_to_agentforce(from_number, message_text)
        
        # Send WhatsApp reply
        send_whatsapp_message(from_number, response_text)
        
        return Response('OK', status=200)
    
    except Exception as e:
        logger.error(f"Error handling text message: {str(e)}", exc_info=True)
        send_whatsapp_message(from_number, "Sorry, I encountered an error. Please try again.")
        return Response(json.dumps({'error': str(e)}), status=500, mimetype='application/json')


def handle_voice_message(from_number: str, message_sid: str, media_url: str, content_type: str):
    """Handle voice message from WhatsApp"""
    try:
        # Download audio from Twilio
        logger.info(f"Downloading audio from: {media_url}")
        audio_data = download_twilio_media(media_url)
        
        # Convert speech to text
        logger.info("Converting speech to text...")
        transcribed_text, detected_language = elevenlabs_stt(audio_data, content_type)
        logger.info(f"Transcribed text: {transcribed_text} (language: {detected_language})")
        
        # Send to Agentforce
        logger.info("Sending to Agentforce...")
        response_text = send_to_agentforce(from_number, transcribed_text)
        logger.info(f"Agentforce response: {response_text}")
        
        # OPTIMIZATION: Send text response immediately (user sees response faster!)
        logger.info("Sending text response immediately...")
        send_whatsapp_message(from_number, response_text)
        
        # Generate voice response in background (non-blocking)
        # This allows the webhook to return quickly while voice is being generated
        logger.info(f"Generating voice response in background using ElevenLabs...")
        try:
            audio_base64 = elevenlabs_tts(response_text, detected_language)
            logger.info("Voice generation complete, sending voice message...")
            send_whatsapp_voice_message(from_number, response_text, audio_base64)
        except Exception as voice_error:
            logger.error(f"Error generating/sending voice response: {str(voice_error)}")
            # Don't fail the whole request if voice fails - text was already sent
        
        return Response('OK', status=200)
    
    except Exception as e:
        logger.error(f"Error handling voice message: {str(e)}", exc_info=True)
        error_msg = str(e)
        
        # Provide more helpful error messages
        if "no speech detected" in error_msg.lower() or "totalBilledTime" in error_msg:
            user_message = "I couldn't detect any speech in your voice message. Please try:\n• Speaking louder\n• Recording a longer message\n• Sending a text message instead"
        else:
            user_message = "Sorry, I couldn't process your voice message. Please try typing your message."
        
        send_whatsapp_message(from_number, user_message)
        return Response(json.dumps({'error': str(e)}), status=500, mimetype='application/json')


def download_twilio_media(media_url: str) -> bytes:
    """Download media file from Twilio with retry logic"""
    import time
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading media from Twilio (attempt {attempt + 1}/{max_retries}): {media_url}")
            response = requests.get(
                media_url, 
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), 
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 404 and attempt < max_retries - 1:
                # Media not ready yet, wait and retry
                wait_time = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s (faster retries)
                logger.warning(f"Media not ready (404), waiting {wait_time}s before retry")
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                logger.error(f"Twilio media download error: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            logger.info(f"✅ Downloaded {len(response.content)} bytes from Twilio")
            return response.content
            
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to download media after {max_retries} attempts: {str(e)}")
                raise Exception(f"Failed to download media from Twilio: {str(e)}")
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")


def elevenlabs_stt(audio_data: bytes, content_type: str) -> Tuple[str, str]:
    """Convert speech to text using ElevenLabs API
    
    Note: ElevenLabs may require specific audio formats. Converting to WAV for compatibility.
    """
    try:
        logger.info(f"Original audio: {len(audio_data)} bytes, Content type: {content_type}")

        # Convert audio to LINEAR16 (WAV) format for best Google STT compatibility
        # This matches the LWC component's approach and solves the OGG_OPUS transcription issue
        try:
            logger.info("Converting audio to LINEAR16/WAV format using ffmpeg...")
            
            # Use ffmpeg directly (available via buildpack) instead of pydub
            # This avoids Python 3.13+ audioop compatibility issues
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as input_file:
                input_file.write(audio_data)
                input_file.flush()  # CRITICAL: Ensure data is written to disk
                input_path = input_file.name
            
            # Create output file path (don't open it yet, let ffmpeg create it)
            output_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            output_path = output_file.name
            output_file.close()  # Close it so ffmpeg can write to it
            
            try:
                # Convert to mono, 16kHz, 16-bit PCM WAV using ffmpeg
                # Optimized for speed: lower quality is fine for STT
                result = subprocess.run([
                    'ffmpeg',
                    '-y',            # Overwrite output file
                    '-i', input_path,
                    '-ar', '16000',  # Sample rate: 16kHz
                    '-ac', '1',      # Channels: mono
                    '-f', 'wav',     # Format: WAV
                    '-threads', '2', # Use 2 threads for faster conversion
                    output_path
                ], capture_output=True, text=True, timeout=10)
                
                logger.info(f"ffmpeg returncode: {result.returncode}")
                if result.returncode != 0:
                    logger.error(f"ffmpeg stderr: {result.stderr}")
                    raise Exception(f"ffmpeg failed with code {result.returncode}: {result.stderr}")
                
                # Read the converted audio
                with open(output_path, 'rb') as f:
                    wav_data = f.read()
                
                if len(wav_data) == 0:
                    raise Exception("ffmpeg produced empty output file")
                
                logger.info(f"Converted audio: {len(wav_data)} bytes (LINEAR16/WAV @ 16kHz)")
                
                # Use the converted audio
                audio_base64 = base64.b64encode(wav_data).decode('utf-8')
                encoding = 'LINEAR16'
                sample_rate = 16000
                
            finally:
                # Clean up temp files
                try:
                    os.unlink(input_path)
                except:
                    pass
                try:
                    os.unlink(output_path)
                except:
                    pass
            
        except Exception as conv_error:
            logger.error(f"Audio conversion failed: {str(conv_error)}")
            logger.warning("Falling back to original audio format")
            # Fallback to original audio if conversion fails
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            encoding = 'OGG_OPUS'
            sample_rate = 48000
        
        # NOTE: ElevenLabs doesn't have STT API yet, so we'll use Google STT for now
        # If you want to use a different STT provider, replace this section
        
        # Build STT request - matching Agentforce LWC component configuration
        # LWC uses LINEAR16 @ 16kHz, which we now match
        config = {
            'encoding': encoding,
            'sampleRateHertz': sample_rate,
            'languageCode': 'en-US',  # Primary language
            'alternativeLanguageCodes': ['ar-EG', 'ar-SA', 'en-GB'],  # Arabic auto-detected
            'enableAutomaticPunctuation': True,
            'enableWordTimeOffsets': False,
            'enableWordConfidence': True,
            'maxAlternatives': 3
        }
        
        logger.info(f"STT config: encoding={encoding}, sample_rate={sample_rate}")
        
        payload = {
            'config': config,
            'audio': {'content': audio_base64}
        }
        
        # Call Google Cloud STT API (keeping Google STT since ElevenLabs doesn't have STT)
        GOOGLE_CLOUD_API_KEY = os.environ.get('GOOGLE_CLOUD_API_KEY')
        GOOGLE_STT_ENDPOINT = 'https://speech.googleapis.com/v1/speech:recognize'
        url = f"{GOOGLE_STT_ENDPOINT}?key={GOOGLE_CLOUD_API_KEY}"
        logger.info(f"Calling Google STT API (ElevenLabs doesn't have STT yet)...")
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Google STT API error: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        result = response.json()
        logger.info(f"STT API response: {json.dumps(result, indent=2)[:1000]}")
        
        # Extract transcription
        if 'results' in result and len(result['results']) > 0:
            alternatives = result['results'][0].get('alternatives', [])
            if alternatives and len(alternatives) > 0:
                transcript = alternatives[0].get('transcript', '')
                if transcript and transcript.strip():
                    confidence = alternatives[0].get('confidence', 0)
                    detected_lang = result['results'][0].get('languageCode', 'unknown')
                    logger.info(f"✅ Transcription successful: '{transcript}' (confidence: {confidence:.2f}, lang: {detected_lang})")
                    return transcript.strip(), detected_lang
                else:
                    # Empty transcript - audio was processed but no speech detected
                    billed_time = result.get('totalBilledTime', '0s')
                    detected_lang = result['results'][0].get('languageCode', 'unknown')
                    logger.warning(f"Audio processed ({billed_time}, lang: {detected_lang}) but transcript is empty")
                    raise Exception(f"Audio processed but no clear speech detected. Please speak louder and more clearly.")
        
        # If no results at all, audio wasn't processed
        if 'results' not in result or len(result.get('results', [])) == 0:
            logger.warning(f"No transcription results")
            logger.warning(f"Full STT response: {json.dumps(result)}")
            raise Exception(f"No speech detected in audio. Please try again with a clearer message.")
        
        # Fallback error
        raise Exception(f"No valid transcript found")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error in STT: {str(e)}")
        raise Exception(f"Failed to call STT API: {str(e)}")
    except Exception as e:
        logger.error(f"Error in elevenlabs_stt: {str(e)}", exc_info=True)
        raise


def google_tts(text: str, detected_language: str = None) -> str:
    """Convert text to speech using Google Cloud TTS
    
    Args:
        text: Text to convert to speech
        detected_language: Language detected from STT (e.g., 'ar-eg', 'en-us')
    
    Returns:
        Base64 encoded audio content (MP3)
    """
    # Use detected language from STT if available, otherwise detect from text
    if detected_language:
        # Normalize language code
        detected_language = detected_language.lower()
        if detected_language.startswith('ar'):
            language_code = 'ar-EG'
            voice_name = 'ar-XA-Standard-A'  # Chirp 3 HD Arabic voice
        else:
            language_code = 'en-US'
            voice_name = 'en-US-Standard-A'
    else:
        # Fallback: detect from text (simple heuristic)
        language_code = 'ar-EG'
        voice_name = 'ar-XA-Standard-A'
        
        # Check if text is primarily English
        if sum(1 for c in text if ord(c) < 128) > len(text) * 0.7:
            language_code = 'en-US'
            voice_name = 'en-US-Standard-A'
    
    logger.info(f"TTS: Using language={language_code}, voice={voice_name}")
    
    # Build TTS request
    payload = {
        'input': {
            'text': text
        },
        'voice': {
            'languageCode': language_code,
            'name': voice_name,
            'ssmlGender': 'FEMALE'
        },
        'audioConfig': {
            'audioEncoding': 'MP3',
            'speakingRate': 1.0,
            'pitch': 0.0,
            'volumeGainDb': 0.0
        }
    }
    
    # Call Google Cloud TTS API
    url = f"{GOOGLE_TTS_ENDPOINT}?key={GOOGLE_CLOUD_API_KEY}"
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    result = response.json()
    
    # Extract audio content
    audio_content = result.get('audioContent', '')
    if not audio_content:
        raise Exception("No audio content found in TTS response")
    
    return audio_content


def get_agentforce_session(from_number: str) -> str:
    """Get or create Agentforce session for WhatsApp number"""
    # Check if session exists and is still valid
    if from_number in sessions:
        session_data = sessions[from_number]
        # Check if session is still valid (30 minutes timeout)
        if datetime.now() - session_data['created_at'] < timedelta(minutes=30):
            return session_data['session_id']
    
    # Create new session
    logger.info(f"Creating new Agentforce session for {from_number}")
    
    # Get Salesforce OAuth token
    access_token = get_salesforce_token()
    
    # Create session
    session_payload = {
        'externalSessionKey': f"whatsapp_{from_number}",
        'instanceConfig': {
            'endpoint': SALESFORCE_INSTANCE_URL
        },
        'streamingCapabilities': {
            'chunkTypes': ['Text']
        },
        'bypassUser': True
    }
    
    url = f"{AGENTFORCE_API_BASE}/agents/{AGENTFORCE_AGENT_ID}/sessions"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, json=session_payload, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    session_id = result.get('sessionId')
    
    if not session_id:
        raise Exception("No sessionId returned from Agentforce")
    
    # Store session
    sessions[from_number] = {
        'session_id': session_id,
        'created_at': datetime.now(),
        'sequence_id': 0
    }
    
    logger.info(f"Created session: {session_id}")
    return session_id


def send_to_agentforce(from_number: str, message_text: str) -> str:
    """Send message to Agentforce and get response"""
    # Get or create session
    session_id = get_agentforce_session(from_number)
    
    # Get sequence ID
    session_data = sessions[from_number]
    sequence_id = session_data['sequence_id'] + 1
    session_data['sequence_id'] = sequence_id
    
    # Get Salesforce OAuth token
    access_token = get_salesforce_token()
    
    # Send message
    message_payload = {
        'message': {
            'sequenceId': sequence_id,
            'type': 'Text',
            'text': message_text
        },
        'variables': []
    }
    
    url = f"{AGENTFORCE_API_BASE}/sessions/{session_id}/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, json=message_payload, headers=headers, timeout=120)
    response.raise_for_status()
    
    result = response.json()
    
    # Extract response text
    messages = result.get('messages', [])
    if messages:
        response_text = messages[0].get('message', '')
        return response_text
    
    return "I received your message, but couldn't generate a response. Please try again."


def get_salesforce_token() -> str:
    """Get Salesforce OAuth access token using client_credentials flow (same as MessengerChatController)"""
    # Use client_credentials flow - same as the existing MessengerChatController implementation
    # This uses the Connected App Consumer Key and Secret directly
    url = f"{SALESFORCE_INSTANCE_URL}/services/oauth2/token"
    
    payload = {
        'grant_type': 'client_credentials',
        'client_id': SALESFORCE_CONSUMER_KEY,
        'client_secret': SALESFORCE_CONSUMER_SECRET
    }
    
    response = requests.post(url, data=payload)
    
    if response.status_code != 200:
        error_msg = response.text
        try:
            error_json = response.json()
            error_msg = error_json.get('error_description', error_json.get('error', error_msg))
        except:
            pass
        raise Exception(f"Salesforce OAuth failed: {error_msg}")
    
    result = response.json()
    return result['access_token']


def send_whatsapp_message(to_number: str, message_text: str):
    """Send text message via Twilio WhatsApp"""
    # Clean and validate phone number
    to_number = to_number.strip()
    if not to_number.startswith('+'):
        to_number = '+' + to_number.lstrip('+')
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    
    payload = {
        'From': TWILIO_WHATSAPP_FROM,
        'To': f"whatsapp:{to_number}",
        'Body': message_text
    }
    
    logger.info(f"Sending WhatsApp message to {to_number}: {message_text[:50]}...")
    response = requests.post(url, data=payload, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    
    if response.status_code not in [200, 201]:
        logger.error(f"Twilio API error: {response.status_code} - {response.text}")
        response.raise_for_status()
    
    logger.info(f"✅ Sent WhatsApp message to {to_number}")


def send_whatsapp_voice_message(to_number: str, text_message: str, audio_base64: str):
    """Send WhatsApp message with both text and voice note
    
    Args:
        to_number: Recipient phone number
        text_message: Text message to send
        audio_base64: Base64 encoded audio (MP3) from Google TTS
    """
    # Clean phone number early so it's always available
    clean_number = to_number.strip() if to_number else ''
    if clean_number and not clean_number.startswith('+'):
        clean_number = '+' + clean_number.lstrip('+')
    
    try:
        # Step 1: Convert base64 audio to binary
        audio_data = base64.b64decode(audio_base64)
        logger.info(f"Audio data size: {len(audio_data)} bytes")
        
        # Step 2: Store audio and get public URL
        logger.info("Storing audio and generating public URL...")
        media_url = upload_audio_to_twilio(audio_data)
        logger.info(f"Audio URL: {media_url}")
        
        # Step 3: Send WhatsApp message with voice attachment
        # IMPORTANT: For voice messages, use ONLY MediaUrl (no Body parameter)
        # This is different from text messages which use Body parameter
        # Note: Text message is already sent in handle_voice_message before calling this function
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
        
        payload = {
            'From': TWILIO_WHATSAPP_FROM,
            'To': f"whatsapp:{clean_number}",
            'MediaUrl': media_url   # Voice note attachment (MP3 URL must be publicly accessible)
        }
        
        logger.info(f"Sending WhatsApp voice message to {clean_number}")
        logger.info(f"Payload: From={payload['From']}, To={payload['To']}, MediaUrl={payload['MediaUrl']}")
        
        response = requests.post(url, data=payload, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        
        result = response.json() if response.status_code in [200, 201] else {}
        num_media = result.get('num_media', '0')
        
        if response.status_code != 201:
            logger.error(f"Twilio API error: {response.status_code} - {response.text}")
            response.raise_for_status()
        elif num_media == '0':
            logger.warning(f"⚠️  Message sent but NO MEDIA attached. Check if Twilio can access: {payload['MediaUrl']}")
        else:
            logger.info(f"✅ Sent WhatsApp message with voice to {clean_number} (num_media={num_media})")
        
    except Exception as e:
        logger.error(f"Error sending voice message: {str(e)}", exc_info=True)
        # Fallback: send text only
        logger.warning("Falling back to text-only message")
        send_whatsapp_message(clean_number, text_message)


def upload_audio_to_twilio(audio_data: bytes) -> str:
    """Store audio temporarily and return public URL
    
    Args:
        audio_data: Binary audio data (MP3)
    
    Returns:
        Public URL to access the audio
    """
    # Generate unique ID for this audio file
    audio_id = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + os.urandom(4).hex()
    
    # Store audio in memory cache (simple approach for now)
    # In production, you might want to use Redis or cloud storage
    audio_cache[audio_id] = {
        'data': audio_data,
        'timestamp': datetime.now(),
        'content_type': 'audio/mpeg'
    }
    
    # Clean up old audio files (older than 5 minutes)
    cleanup_old_audio()
    
    # Return public URL to access this audio
    # Heroku will provide the public URL via the app URL
    public_url = f"https://whatsapp-agentforce-handler-ca94b9efde9c.herokuapp.com/audio/{audio_id}"
    
    logger.info(f"Audio stored with ID: {audio_id}, URL: {public_url}")
    return public_url


# In-memory audio cache
audio_cache = {}

def cleanup_old_audio():
    """Remove audio files older than 5 minutes"""
    cutoff_time = datetime.now() - timedelta(minutes=5)
    to_delete = [aid for aid, data in audio_cache.items() if data['timestamp'] < cutoff_time]
    for aid in to_delete:
        del audio_cache[aid]
    if to_delete:
        logger.info(f"Cleaned up {len(to_delete)} old audio files")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
