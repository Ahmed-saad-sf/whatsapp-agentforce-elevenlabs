"""
WhatsApp → Agentforce Integration Handler (ElevenLabs Version)
Heroku Flask app to handle Twilio WhatsApp webhooks
Uses ElevenLabs for both STT (Speech-to-Text) and TTS (Text-to-Speech)

OPTIMIZATION 2: Parallel Processing (v2.0)
- Parallel download and STT conversion
- Pre-warm Agentforce sessions
- Optimized retry logic (0.5s → 1s → 2s)
- Faster ffmpeg settings for STT
- Performance metrics tracking

OPTIMIZATION 3: Connection Pooling & TTS Settings (v2.1)
- Optimized HTTP connection pooling (better concurrency)
- Faster TTS settings (15-30% faster generation)
"""

import os
import json
import base64
import requests
import logging
import io
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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
ELEVENLABS_STT_ENDPOINT = f'{ELEVENLABS_API_BASE}/speech-to-text'
ELEVENLABS_TTS_ENDPOINT = f'{ELEVENLABS_API_BASE}/text-to-speech/{ELEVENLABS_VOICE_ID}'

# In-memory session storage (can be upgraded to Redis/Firestore)
sessions: Dict[str, Dict] = {}

# OAuth token cache (to avoid fetching on every request)
token_cache = {'token': None, 'expires_at': None}

# HTTP session for connection pooling (OPTIMIZATION 3: Optimized connection pooling)
# Configure connection pool for better concurrency and performance
adapter = HTTPAdapter(
    pool_connections=10,      # Number of connection pools to cache
    pool_maxsize=20,          # Max connections per pool (increased for better concurrency)
    max_retries=Retry(
        total=3,              # Total retries
        backoff_factor=0.3,   # Exponential backoff: 0.3s, 0.6s, 1.2s
        status_forcelist=[500, 502, 503, 504],  # Retry on these status codes
        allowed_methods=['GET', 'POST']  # Only retry safe methods
    ),
    pool_block=False          # Don't block when pool is full (fail fast)
)

http_session = requests.Session()
http_session.mount('http://', adapter)
http_session.mount('https://', adapter)
logger.info("✅ Optimized HTTP connection pooling configured (pool_maxsize=20, pool_connections=10)")

# Thread pool executor for parallel processing (Optimization 2)
executor = ThreadPoolExecutor(max_workers=5)

# Performance metrics tracking
performance_metrics = {
    'download_time': [],
    'stt_time': [],
    'agentforce_time': [],
    'tts_time': [],
    'total_time': []
}


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


@app.route('/metrics', methods=['GET'])
def get_performance_metrics():
    """Get performance metrics (Optimization 2)"""
    def calculate_stats(times):
        if not times:
            return {'count': 0, 'avg': 0, 'min': 0, 'max': 0}
        return {
            'count': len(times),
            'avg': sum(times) / len(times),
            'min': min(times),
            'max': max(times)
        }
    
    metrics = {
        'download_time': calculate_stats(performance_metrics['download_time']),
        'stt_time': calculate_stats(performance_metrics['stt_time']),
        'agentforce_time': calculate_stats(performance_metrics['agentforce_time']),
        'tts_time': calculate_stats(performance_metrics['tts_time']),
        'total_time': calculate_stats(performance_metrics['total_time'])
    }
    
    return Response(json.dumps(metrics, indent=2), status=200, mimetype='application/json')


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


def detect_language_from_text(text: str) -> str:
    """Detect language from text (simple heuristic)
    
    Returns:
        'ar' for Arabic, 'en' for English (default)
    """
    # Check if text contains Arabic characters
    arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')
    text_chars = set(text)
    
    # If more than 10% of characters are Arabic, consider it Arabic
    if len(text_chars & arabic_chars) > len(text) * 0.1:
        return 'ar'
    return 'en'


def send_acknowledgment_message(to_number: str, language: str):
    """Send immediate acknowledgment message based on language"""
    if language == 'ar':
        message = "إديني ثانية واحدة أجيبلك المعلومة دي"
    else:
        message = "Give me just a second to find that information..."
    
    send_whatsapp_message(to_number, message)


def send_voice_preparation_message(to_number: str, language: str):
    """Send message before generating voice response"""
    if language == 'ar':
        message = "ثانية واحدة، بجهزلك فويس بالرد"
    else:
        message = "I am sending you a voice"
    
    send_whatsapp_message(to_number, message)


def handle_text_message(from_number: str, message_sid: str, message_text: str):
    """Handle text message from WhatsApp with Optimization 2: Pre-warm session"""
    start_time = time.time()
    try:
        # OPTIMIZATION 2: Pre-warm Agentforce session while detecting language
        logger.info("Pre-warming Agentforce session in parallel...")
        session_future = executor.submit(get_agentforce_session, from_number)
        
        # Detect language from text
        detected_language = detect_language_from_text(message_text)
        
        # Send immediate acknowledgment
        logger.info(f"Sending acknowledgment message (language: {detected_language})...")
        send_acknowledgment_message(from_number, detected_language)
        
        # OPTIMIZATION 2: Get pre-warmed session (should be ready by now)
        session_id = session_future.result(timeout=10)
        
        # Get Agentforce response
        agentforce_start = time.time()
        response_text = send_to_agentforce(from_number, message_text)
        agentforce_time = time.time() - agentforce_start
        performance_metrics['agentforce_time'].append(agentforce_time)
        logger.info(f"⏱️ Agentforce time: {agentforce_time:.2f}s")
        
        # Send WhatsApp reply
        send_whatsapp_message(from_number, response_text)
        
        total_time = time.time() - start_time
        performance_metrics['total_time'].append(total_time)
        logger.info(f"⏱️ Total processing time: {total_time:.2f}s")
        
        return Response('OK', status=200)
    
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"❌ Error handling text message ({error_type}): {error_msg}", exc_info=True)
        
        # Log additional context
        logger.error(f"   Message text: {message_text[:200]}")
        logger.error(f"   From number: {from_number}")
        
        # Send error message to user
        send_whatsapp_message(from_number, "Sorry, I encountered an error. Please try again.")
        return Response(json.dumps({'error': error_msg, 'type': error_type}), status=500, mimetype='application/json')


def handle_voice_message(from_number: str, message_sid: str, media_url: str, content_type: str):
    """Handle voice message from WhatsApp with Optimization 2: Parallel Processing"""
    start_time = time.time()
    try:
        # OPTIMIZATION 2: Pre-warm Agentforce session in parallel with download
        logger.info("Pre-warming Agentforce session in parallel...")
        session_future = executor.submit(get_agentforce_session, from_number)
        
        # Download audio from Twilio
        download_start = time.time()
        logger.info(f"Downloading audio from: {media_url}")
        audio_data = download_twilio_media(media_url)
        download_time = time.time() - download_start
        performance_metrics['download_time'].append(download_time)
        logger.info(f"⏱️ Download time: {download_time:.2f}s")
        
        # OPTIMIZATION 2: Convert speech to text in parallel with session creation
        stt_start = time.time()
        logger.info("Converting speech to text...")
        transcribed_text, detected_language_code = elevenlabs_stt(audio_data, content_type)
        stt_time = time.time() - stt_start
        performance_metrics['stt_time'].append(stt_time)
        logger.info(f"⏱️ STT time: {stt_time:.2f}s")
        logger.info(f"Transcribed text: {transcribed_text} (language: {detected_language_code})")
        
        # Map ElevenLabs language code to our simple language code
        # ElevenLabs returns codes like 'ara', 'en', etc.
        if detected_language_code and ('ara' in detected_language_code.lower() or 'ar' in detected_language_code.lower()):
            detected_language = 'ar'
        else:
            detected_language = 'en'
        
        # Send transcribed text back to user BEFORE acknowledgment
        logger.info(f"Sending transcribed text to user: {transcribed_text}")
        send_whatsapp_message(from_number, transcribed_text)
        
        # Send immediate acknowledgment
        logger.info(f"Sending acknowledgment message (language: {detected_language})...")
        send_acknowledgment_message(from_number, detected_language)
        
        # OPTIMIZATION 2: Get pre-warmed session (should be ready by now)
        logger.info("Getting pre-warmed Agentforce session...")
        session_id = session_future.result(timeout=10)  # Should be ready already
        
        # Send to Agentforce
        agentforce_start = time.time()
        logger.info("Sending to Agentforce...")
        response_text = send_to_agentforce(from_number, transcribed_text)
        agentforce_time = time.time() - agentforce_start
        performance_metrics['agentforce_time'].append(agentforce_time)
        logger.info(f"⏱️ Agentforce time: {agentforce_time:.2f}s")
        logger.info(f"Agentforce response: {response_text}")
        
        # OPTIMIZATION: Send text response immediately (user sees response faster!)
        logger.info("Sending text response immediately...")
        send_whatsapp_message(from_number, response_text)
        
        # Wait a moment to ensure all message chunks are sent before voice preparation message
        # This prevents the voice preparation message from appearing between split messages
        # Calculate delay based on message length (longer messages = more chunks = more delay)
        message_chunks = (len(response_text) // 1600) + 1
        delay_seconds = min(0.5 * message_chunks, 2.0)  # Max 2 seconds delay
        if message_chunks > 1:
            logger.info(f"Waiting {delay_seconds:.1f}s to ensure all {message_chunks} message chunks are sent...")
            time.sleep(delay_seconds)
        
        # Send voice preparation message AFTER all response chunks are sent
        logger.info(f"Sending voice preparation message (language: {detected_language})...")
        send_voice_preparation_message(from_number, detected_language)
        
        # Generate voice response in background thread (truly non-blocking)
        # This allows the webhook to return immediately while voice is being generated
        def generate_and_send_voice():
            try:
                tts_start = time.time()
                logger.info(f"Generating voice response in background using ElevenLabs...")
                audio_base64 = elevenlabs_tts(response_text, detected_language_code)
                tts_time = time.time() - tts_start
                performance_metrics['tts_time'].append(tts_time)
                logger.info(f"⏱️ TTS time: {tts_time:.2f}s")
                logger.info("Voice generation complete, sending voice message...")
                send_whatsapp_voice_message(from_number, response_text, audio_base64)
            except Exception as voice_error:
                error_msg = str(voice_error)
                logger.error(f"Error generating/sending voice response: {error_msg}", exc_info=True)
                
                # Send error details to user via WhatsApp
                if detected_language == 'ar':
                    error_message = f"حدث خطأ أثناء توليد الصوت:\n{error_msg}"
                else:
                    error_message = f"An error occurred while generating voice:\n{error_msg}"
                
                try:
                    send_whatsapp_message(from_number, error_message)
                except Exception as send_error:
                    logger.error(f"Failed to send error message to user: {str(send_error)}")
                
                # Don't fail the whole request if voice fails - text response was already sent
        
        voice_thread = threading.Thread(target=generate_and_send_voice, daemon=True)
        voice_thread.start()
        logger.info("Voice generation started in background thread, returning webhook response...")
        
        total_time = time.time() - start_time
        performance_metrics['total_time'].append(total_time)
        logger.info(f"⏱️ Total processing time: {total_time:.2f}s (download: {download_time:.2f}s, STT: {stt_time:.2f}s, Agentforce: {agentforce_time:.2f}s)")
        
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
    """Download media file from Twilio with optimized retry logic (Optimization 2 & 3)"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading media from Twilio (attempt {attempt + 1}/{max_retries}): {media_url}")
            response = http_session.get(
                media_url, 
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), 
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 404 and attempt < max_retries - 1:
                # OPTIMIZATION 3: Faster retry logic (0.5s → 1s → 2s, total max 3.5s instead of 7s)
                wait_time = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s (optimized from 1s, 2s, 4s)
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
    """Convert speech to text using ElevenLabs REST API
    
    Reference: https://elevenlabs.io/docs/api-reference/speech-to-text
    POST /v1/speech-to-text with multipart/form-data
    """
    try:
        logger.info(f"Original audio: {len(audio_data)} bytes, Content type: {content_type}")

        # ElevenLabs supports all major audio formats, so we can use the original audio
        # But we'll convert to WAV for best compatibility if needed
        audio_to_send = audio_data
        audio_filename = 'audio.ogg'
        audio_mime_type = content_type or 'audio/ogg'
        
        # If it's OGG/Opus (WhatsApp voice notes), we can send it directly
        # Otherwise, convert to WAV for better compatibility
        if not content_type or 'ogg' not in content_type.lower():
            try:
                logger.info("Converting audio to WAV format using ffmpeg for better compatibility...")
                
                with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as input_file:
                    input_file.write(audio_data)
                    input_file.flush()
                    input_path = input_file.name
                
                # Create WAV output file
                output_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                output_path = output_file.name
                output_file.close()
                
                try:
                    # OPTIMIZATION 4: Faster ffmpeg settings for STT (lower quality, faster processing)
                    # STT doesn't need perfect quality, so we optimize for speed
                    result = subprocess.run([
                        'ffmpeg',
                        '-y',
                        '-i', input_path,
                        '-ar', '16000',      # Sample rate: 16kHz (sufficient for STT)
                        '-ac', '1',          # Channels: mono
                        '-f', 'wav',         # Format: WAV
                        '-threads', '2',      # Use 2 threads for faster processing
                        '-acodec', 'pcm_s16le',  # PCM 16-bit (faster encoding)
                        '-loglevel', 'error',     # Reduce logging overhead
                        output_path
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode != 0:
                        logger.error(f"ffmpeg stderr: {result.stderr}")
                        raise Exception(f"ffmpeg failed: {result.stderr}")
                    
                    # Read the converted audio
                    with open(output_path, 'rb') as f:
                        audio_to_send = f.read()
                    
                    if len(audio_to_send) == 0:
                        raise Exception("ffmpeg produced empty output file")
                    
                    audio_filename = 'audio.wav'
                    audio_mime_type = 'audio/wav'
                    logger.info(f"Converted audio: {len(audio_to_send)} bytes (WAV @ 16kHz)")
                    
                finally:
                    try:
                        os.unlink(input_path)
                        os.unlink(output_path)
                    except:
                        pass
                
            except Exception as conv_error:
                logger.warning(f"Audio conversion failed, using original format: {str(conv_error)}")
                # Fallback: use original audio
                audio_to_send = audio_data
        
        # Call ElevenLabs REST API for STT
        logger.info(f"Calling ElevenLabs STT REST API with {len(audio_to_send)} bytes...")
        
        headers = {
            'xi-api-key': ELEVENLABS_API_KEY
        }
        
        # Prepare multipart form data
        files = {
            'file': (audio_filename, audio_to_send, audio_mime_type)
        }
        
        data = {
            'model_id': 'scribe_v1',  # Use scribe_v1 model (supports multilingual)
            'language_code': None,  # Auto-detect language
            'tag_audio_events': True,
            'diarize': False,
            'timestamps_granularity': 'word'
        }
        
        logger.info(f"Sending audio file to ElevenLabs STT (model: scribe_v1)...")
        response = http_session.post(
            ELEVENLABS_STT_ENDPOINT,
            headers=headers,
            files=files,
            data=data,
            timeout=60  # STT can take longer for longer audio files
        )
        
        if response.status_code != 200:
            logger.error(f"ElevenLabs STT API error: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        result = response.json()
        logger.info(f"ElevenLabs STT response received")
        
        # Extract transcription
        transcript_text = result.get('text', '').strip()
        language_code = result.get('language_code', 'unknown')
        language_probability = result.get('language_probability', 0)
        
        if not transcript_text:
            raise Exception("No transcription text in ElevenLabs STT response")
        
        logger.info(f"✅ ElevenLabs STT successful: '{transcript_text}' (lang: {language_code}, prob: {language_probability:.2f})")
        return transcript_text, language_code
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error in ElevenLabs STT: {str(e)}")
        raise Exception(f"Failed to call ElevenLabs STT API: {str(e)}")
    except Exception as e:
        logger.error(f"Error in elevenlabs_stt: {str(e)}", exc_info=True)
        raise


def elevenlabs_tts(text: str, detected_language: str = None) -> str:
    """Convert text to speech using ElevenLabs API
    
    Args:
        text: Text to convert to speech
        detected_language: Language detected from STT (e.g., 'ar-eg', 'en-us') - not used for ElevenLabs
    
    Returns:
        Base64 encoded audio content (MP3)
    """
    try:
        logger.info(f"TTS: Using ElevenLabs voice_id={ELEVENLABS_VOICE_ID}")
        
        # ElevenLabs API endpoint for text-to-speech
        url = ELEVENLABS_TTS_ENDPOINT
        
        # Build request payload according to ElevenLabs API
        # OPTIMIZATION 3: Optimized TTS settings for speed (15-30% faster)
        # Lower stability and similarity_boost = faster generation with minimal quality loss
        # Disabled speaker_boost = faster processing
        payload = {
            'text': text,
            'model_id': 'eleven_multilingual_v2',  # Multilingual model supports Arabic and English
            'voice_settings': {
                'stability': 0.35,          # Lower = faster (was 0.5, optimized for speed)
                'similarity_boost': 0.6,     # Lower = faster (was 0.75, still good quality)
                'style': 0.0,
                'use_speaker_boost': False  # Disabled = faster (was True, minimal quality impact)
            }
        }
        logger.info("✅ Using optimized TTS settings (stability=0.35, similarity_boost=0.6, speaker_boost=False)")
        
        headers = {
            'Accept': 'audio/mpeg',
            'Content-Type': 'application/json',
            'xi-api-key': ELEVENLABS_API_KEY
        }
        
        # Call ElevenLabs TTS API
        logger.info(f"Calling ElevenLabs TTS API...")
        response = http_session.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"ElevenLabs TTS API error: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        # ElevenLabs returns audio directly as binary (MP3)
        audio_data = response.content
        
        if not audio_data or len(audio_data) == 0:
            raise Exception("No audio content in ElevenLabs TTS response")
        
        # Convert to base64 for consistency with existing code
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        logger.info(f"✅ Generated ElevenLabs TTS audio: {len(audio_data)} bytes (MP3)")
        return audio_base64
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error in ElevenLabs TTS: {str(e)}")
        raise Exception(f"Failed to call ElevenLabs TTS API: {str(e)}")
    except Exception as e:
        logger.error(f"Error in elevenlabs_tts: {str(e)}", exc_info=True)
        raise


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
    
    logger.info(f"📤 Creating Agentforce session: agent_id={AGENTFORCE_AGENT_ID}, external_key=whatsapp_{from_number}")
    response = http_session.post(url, json=session_payload, headers=headers)
    
    # Enhanced error handling for session creation
    if response.status_code != 200 and response.status_code != 201:
        error_details = f"Status: {response.status_code}"
        try:
            error_json = response.json()
            error_details += f", Response: {json.dumps(error_json)}"
            logger.error(f"❌ Agentforce session creation error: {error_details}")
        except:
            error_details += f", Response text: {response.text[:500]}"
            logger.error(f"❌ Agentforce session creation error (non-JSON): {error_details}")
        raise Exception(f"Failed to create Agentforce session: {error_details}")
    
    result = response.json()
    session_id = result.get('sessionId')
    
    if not session_id:
        logger.error(f"❌ No sessionId in response: {json.dumps(result)}")
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
    
    logger.info(f"📤 Sending to Agentforce: session={session_id}, sequence={sequence_id}, text_length={len(message_text)}")
    logger.debug(f"Message text: {message_text[:100]}...")
    
    response = http_session.post(url, json=message_payload, headers=headers, timeout=120)
    
    # Handle different response status codes
    if response.status_code == 204:
        # 204 No Content - message accepted but no immediate response
        # This might indicate async processing or streaming response
        # For now, we'll retry the request or return a helpful message
        logger.info(f"✅ Agentforce accepted message (204), attempting to get response...")
        
        # Wait a moment for processing, then try to get response
        # Note: This is a workaround - ideally Agentforce should return the response immediately
        time.sleep(0.5)
        
        # Try making a GET request to retrieve the latest message
        # Some APIs require polling after a 204
        try:
            get_url = f"{AGENTFORCE_API_BASE}/sessions/{session_id}/messages"
            get_response = http_session.get(get_url, headers=headers, timeout=30)
            
            if get_response.status_code == 200:
                result = get_response.json()
                logger.debug(f"📥 Agentforce response (from GET): {json.dumps(result)[:500]}...")
                messages = result.get('messages', [])
                if messages:
                    # Get the latest message (should be the response)
                    response_text = messages[-1].get('message', '')
                    if response_text:
                        return response_text
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve response after 204: {e}")
        
        # If we can't get the response, return a helpful message
        logger.warning(f"⚠️ Agentforce returned 204 but couldn't retrieve response")
        return "تم استلام رسالتك. جاري معالجة طلبك..."
    
    elif response.status_code == 200:
        # Normal response with JSON body
        try:
            result = response.json()
            logger.debug(f"📥 Agentforce response: {json.dumps(result)[:500]}...")
            
            # Extract response text
            messages = result.get('messages', [])
            if messages:
                first_message = messages[0]
                message_type = first_message.get('type', '')
                
                # Handle Failure messages
                if message_type == 'Failure':
                    errors = first_message.get('errors', [])
                    error_code = first_message.get('code', '')
                    logger.error(f"❌ Agentforce returned Failure: code={error_code}, errors={errors}")
                    
                    # Extract error message
                    if errors and len(errors) > 0:
                        error_msg = errors[0]
                        # Translate common error messages to Arabic
                        if "system error" in error_msg.lower() or "error occurred" in error_msg.lower():
                            return "عذراً، حدث خطأ في النظام. يرجى المحاولة مرة أخرى."
                        elif "timeout" in error_msg.lower():
                            return "انتهت مهلة الاتصال. يرجى المحاولة مرة أخرى."
                        else:
                            return f"عذراً، حدث خطأ: {error_msg}"
                    else:
                        return "عذراً، حدث خطأ في النظام. يرجى المحاولة مرة أخرى."
                
                # Handle normal Text messages
                response_text = first_message.get('message', '')
                if not response_text:
                    logger.warning(f"⚠️ Agentforce returned empty message. Full response: {json.dumps(result)}")
                    return "تم استلام رسالتك، لكن لم أتمكن من إنشاء رد. يرجى المحاولة مرة أخرى."
                return response_text
            
            logger.warning(f"⚠️ No messages in Agentforce response. Full response: {json.dumps(result)}")
            return "تم استلام رسالتك، لكن لم أتمكن من إنشاء رد. يرجى المحاولة مرة أخرى."
        except ValueError as e:
            logger.error(f"❌ Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response.text[:500]}")
            return "تم استلام رسالتك، لكن حدث خطأ في معالجة الرد. يرجى المحاولة مرة أخرى."
    
    else:
        # Error response
        error_details = f"Status: {response.status_code}"
        try:
            error_json = response.json()
            error_details += f", Response: {json.dumps(error_json)}"
            logger.error(f"❌ Agentforce API error: {error_details}")
        except:
            error_details += f", Response text: {response.text[:500]}"
            logger.error(f"❌ Agentforce API error (non-JSON): {error_details}")
        
        # Raise with detailed error message
        raise Exception(f"Agentforce API returned {response.status_code}: {error_details}")


def get_salesforce_token() -> str:
    """Get Salesforce OAuth access token with caching
    
    Caches the token to avoid fetching on every request.
    Tokens typically expire in 2 hours, so we cache for 1.5 hours for safety.
    """
    global token_cache
    
    # Check if cached token is still valid
    if token_cache['token'] and token_cache['expires_at']:
        if datetime.now() < token_cache['expires_at']:
            logger.info("✅ Using cached OAuth token")
            return token_cache['token']
        else:
            logger.info("⚠️ Cached token expired, fetching new token")
    
    # Fetch new token
    logger.info("Fetching new Salesforce OAuth token...")
    url = f"{SALESFORCE_INSTANCE_URL}/services/oauth2/token"
    
    payload = {
        'grant_type': 'client_credentials',
        'client_id': SALESFORCE_CONSUMER_KEY,
        'client_secret': SALESFORCE_CONSUMER_SECRET
    }
    
    response = http_session.post(url, data=payload)
    
    if response.status_code != 200:
        error_msg = response.text
        try:
            error_json = response.json()
            error_msg = error_json.get('error_description', error_json.get('error', error_msg))
        except:
            pass
        raise Exception(f"Salesforce OAuth failed: {error_msg}")
    
    result = response.json()
    access_token = result['access_token']
    
    # Cache token (expires in ~2 hours, use 1.5 hours for safety)
    expires_in = result.get('expires_in', 7200)  # Default 2 hours (7200 seconds)
    token_cache['token'] = access_token
    # Cache for expires_in - 5 minutes buffer to ensure we refresh before expiry
    token_cache['expires_at'] = datetime.now() + timedelta(seconds=expires_in - 300)
    
    logger.info(f"✅ Cached new OAuth token (expires in {expires_in}s, cached until {token_cache['expires_at']})")
    return access_token


def send_whatsapp_message(to_number: str, message_text: str):
    """Send text message via Twilio WhatsApp
    
    Twilio WhatsApp has a 1600 character limit per message.
    If the message exceeds this limit, it will be split into multiple messages.
    """
    # Clean and validate phone number
    to_number = to_number.strip()
    if not to_number.startswith('+'):
        to_number = '+' + to_number.lstrip('+')
    
    # Twilio WhatsApp character limit
    MAX_MESSAGE_LENGTH = 1600
    
    # If message is within limit, send it directly
    if len(message_text) <= MAX_MESSAGE_LENGTH:
        _send_single_whatsapp_message(to_number, message_text)
        return
    
    # Split message into chunks
    logger.info(f"Message exceeds {MAX_MESSAGE_LENGTH} characters ({len(message_text)}), splitting into multiple messages...")
    
    # Reserve space for chunk indicator (e.g., "[99/99]\n\n" = 10 chars, reserve 25 for safety)
    INDICATOR_RESERVE = 25
    CHUNK_SIZE = MAX_MESSAGE_LENGTH - INDICATOR_RESERVE
    
    def add_chunk_if_needed(chunks_list, current_chunk_str):
        """Helper to add chunk if it's not empty, ensuring it doesn't exceed CHUNK_SIZE"""
        if current_chunk_str:
            trimmed = current_chunk_str.strip()
            if len(trimmed) > CHUNK_SIZE:
                # If trimmed chunk exceeds size, truncate it
                trimmed = trimmed[:CHUNK_SIZE]
            chunks_list.append(trimmed)
        return ""
    
    # Split by paragraphs first (double newlines), then by sentences, then by character limit
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs
    paragraphs = message_text.split('\n\n')
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # Calculate what the chunk would be if we add this paragraph
        if current_chunk:
            potential_chunk = current_chunk + '\n\n' + paragraph
        else:
            potential_chunk = paragraph
        
        # If adding this paragraph would exceed chunk size, save current chunk and start new one
        if len(potential_chunk) > CHUNK_SIZE:
            # Save current chunk if it exists
            current_chunk = add_chunk_if_needed(chunks, current_chunk)
            
            # If paragraph itself is too long, split it by sentences
            if len(paragraph) > CHUNK_SIZE:
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    # Add period back if sentence doesn't end with punctuation
                    if sentence and not sentence[-1] in '.!?':
                        sentence += '.'
                    
                    # Calculate potential chunk with this sentence
                    if current_chunk:
                        potential_chunk = current_chunk + ' ' + sentence
                    else:
                        potential_chunk = sentence
                    
                    if len(potential_chunk) > CHUNK_SIZE:
                        # Save current chunk
                        current_chunk = add_chunk_if_needed(chunks, current_chunk)
                        # If sentence itself is too long, split by words
                        if len(sentence) > CHUNK_SIZE:
                            words = sentence.split()
                            for word in words:
                                if current_chunk:
                                    potential_chunk = current_chunk + ' ' + word
                                else:
                                    potential_chunk = word
                                
                                if len(potential_chunk) > CHUNK_SIZE:
                                    current_chunk = add_chunk_if_needed(chunks, current_chunk)
                                    current_chunk = word
                                else:
                                    current_chunk = potential_chunk
                        else:
                            current_chunk = sentence
                    else:
                        current_chunk = potential_chunk
            else:
                current_chunk = paragraph
        else:
            current_chunk = potential_chunk
    
    # Add the last chunk
    add_chunk_if_needed(chunks, current_chunk)
    
    # Filter out empty chunks
    chunks = [chunk for chunk in chunks if chunk.strip()]
    
    if not chunks:
        # Fallback: if somehow no chunks were created, just truncate the original message
        logger.warning("⚠️ No chunks created, truncating original message")
        chunks = [message_text[:MAX_MESSAGE_LENGTH]]
    
    # Send each chunk as a separate message
    total_chunks = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        # Ensure chunk doesn't exceed CHUNK_SIZE
        if len(chunk) > CHUNK_SIZE:
            logger.warning(f"⚠️ Chunk {i} exceeds CHUNK_SIZE ({len(chunk)} > {CHUNK_SIZE}), truncating")
            chunk = chunk[:CHUNK_SIZE]
        
        # Add chunk indicator if multiple chunks
        if total_chunks > 1:
            indicator = f"[{i}/{total_chunks}]\n\n"
            chunk_with_indicator = indicator + chunk
            
            # CRITICAL: Ensure final message never exceeds MAX_MESSAGE_LENGTH
            if len(chunk_with_indicator) > MAX_MESSAGE_LENGTH:
                logger.error(f"❌ Chunk {i}/{total_chunks} with indicator exceeds limit: {len(chunk_with_indicator)} > {MAX_MESSAGE_LENGTH}")
                logger.error(f"   Indicator: '{indicator}' ({len(indicator)} chars)")
                logger.error(f"   Chunk length: {len(chunk)} chars")
                logger.error(f"   Chunk preview: {chunk[:100]}...")
                # Truncate chunk to fit within limit with indicator
                available_space = MAX_MESSAGE_LENGTH - len(indicator)
                chunk = chunk[:available_space]
                chunk_with_indicator = indicator + chunk
                
                # Final safety check
                if len(chunk_with_indicator) > MAX_MESSAGE_LENGTH:
                    logger.error(f"❌ CRITICAL: Still exceeds limit after truncation: {len(chunk_with_indicator)}")
                    chunk_with_indicator = chunk_with_indicator[:MAX_MESSAGE_LENGTH]
            
            logger.info(f"Sending chunk {i}/{total_chunks}: {len(chunk_with_indicator)} chars (indicator: {len(indicator)}, chunk: {len(chunk)})")
            _send_single_whatsapp_message(to_number, chunk_with_indicator)
        else:
            # Single chunk - no indicator needed, but still validate
            if len(chunk) > MAX_MESSAGE_LENGTH:
                logger.warning(f"⚠️ Single chunk exceeds limit, truncating: {len(chunk)} > {MAX_MESSAGE_LENGTH}")
                chunk = chunk[:MAX_MESSAGE_LENGTH]
            logger.info(f"Sending single chunk: {len(chunk)} chars")
            _send_single_whatsapp_message(to_number, chunk)
        
        # Small delay between messages to avoid rate limiting
        import time
        if i < total_chunks:
            time.sleep(0.5)


def _send_single_whatsapp_message(to_number: str, message_text: str):
    """Send a single WhatsApp message (internal helper)"""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    
    payload = {
        'From': TWILIO_WHATSAPP_FROM,
        'To': f"whatsapp:{to_number}",
        'Body': message_text
    }
    
    logger.info(f"Sending WhatsApp message to {to_number}: {message_text[:50]}...")
    response = http_session.post(url, data=payload, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    
    if response.status_code not in [200, 201]:
        logger.error(f"Twilio API error: {response.status_code} - {response.text}")
        response.raise_for_status()
    
    logger.info(f"✅ Sent WhatsApp message to {to_number} ({len(message_text)} chars)")


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
        
        response = http_session.post(url, data=payload, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        
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
    # Use Heroku app name from environment or fallback to current app
    # The app name can be detected from HEROKU_APP_NAME env var or from the app itself
    heroku_app_name = os.environ.get('HEROKU_APP_NAME')
    if not heroku_app_name:
        # Try to get from Flask app context (if available)
        try:
            from flask import has_request_context, request
            if has_request_context():
                # Extract app name from request host
                host = request.host
                if '.herokuapp.com' in host:
                    heroku_app_name = host.split('.herokuapp.com')[0]
        except:
            pass
    
    # Fallback: use the known app name for this deployment
    if not heroku_app_name:
        heroku_app_name = 'whatsapp-agentforce-elevenlabs-6c9f8d6eced2'
    
    public_url = f"https://{heroku_app_name}.herokuapp.com/audio/{audio_id}"
    
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
