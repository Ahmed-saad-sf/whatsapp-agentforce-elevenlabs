"""
Heroku TTS Proxy Service
Proxies Google Cloud Text-to-Speech API calls to bypass CSP restrictions
No IAM issues - Heroku is public by default!
"""

import os
import json
import logging
from flask import Flask, request, jsonify, Response
import requests
import uuid
import base64
from datetime import datetime, timedelta

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Cloud TTS API Key (from environment variable)
GOOGLE_CLOUD_API_KEY = os.environ.get('GOOGLE_CLOUD_API_KEY', '')

# API Key for authentication (optional)
API_KEY = os.environ.get('API_KEY', None)

# In-memory cache for audio files
audio_cache = {}

def detect_language(text):
    """Detect if text is Arabic or English"""
    arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')
    text_chars = set(text)
    
    if arabic_chars.intersection(text_chars):
        return 'ar-XA', 'ar-XA-Standard-A'  # Arabic (various regions)
    return 'en-US', 'en-US-Standard-A'

def synthesize_speech_google(text, language_code, voice_name):
    """Synthesize speech using Google Cloud TTS API"""
    if not GOOGLE_CLOUD_API_KEY:
        raise ValueError("GOOGLE_CLOUD_API_KEY environment variable not set")
    
    # Google Cloud TTS API endpoint
    tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_CLOUD_API_KEY}"
    
    # Request payload
    payload = {
        'input': {'text': text},
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
    
    import requests
    response = requests.post(tts_url, json=payload)
    
    if response.status_code != 200:
        error_detail = response.text
        try:
            error_json = response.json()
            error_detail = json.dumps(error_json, indent=2)
        except:
            pass
        raise Exception(f"Google Cloud TTS API error ({response.status_code}): {error_detail}")
    
    result = response.json()
    if 'audioContent' not in result:
        raise Exception(f"Unexpected response format: {json.dumps(result)}")
    
    audio_content = base64.b64decode(result['audioContent'])
    
    return audio_content

def check_api_key():
    """Check if API key is valid"""
    if not API_KEY:
        return True  # No API key set, allow all
    
    # Check API key from header or query parameter
    provided_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    return provided_key == API_KEY

@app.route('/health', methods=['GET'])
@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'heroku-tts-proxy',
        'google_cloud_configured': bool(GOOGLE_CLOUD_API_KEY)
    }), 200

@app.route('/audio/<audio_id>', methods=['GET', 'OPTIONS'])
def get_audio(audio_id):
    """Get audio file by ID from cache"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response(
            '',
            status=204,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '3600'
            }
        )
    
    # Check if audio exists BEFORE cleanup
    if audio_id not in audio_cache:
        # Clean up old cache entries (older than 1 hour) before returning 404
        current_time = datetime.utcnow()
        keys_to_delete = [
            key for key, value in audio_cache.items()
            if (current_time - value['timestamp']).total_seconds() > 7200  # 2 hours instead of 1
        ]
        for key in keys_to_delete:
            del audio_cache[key]
        
        return Response(
            json.dumps({'error': 'Audio not found', 'audio_id': audio_id}),
            status=404,
            mimetype='application/json',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    
    audio_data = audio_cache[audio_id]
    audio_content = audio_data['content']
    
    # Clean up old cache entries (older than 2 hours) AFTER serving
    current_time = datetime.utcnow()
    keys_to_delete = [
        key for key, value in audio_cache.items()
        if key != audio_id and (current_time - value['timestamp']).total_seconds() > 7200  # 2 hours instead of 1
    ]
    for key in keys_to_delete:
        del audio_cache[key]
    
    # Return audio file with CORS headers
    return Response(
        audio_content,
        mimetype='audio/mpeg',
        headers={
            'Content-Type': 'audio/mpeg',
            'Content-Length': str(len(audio_content)),
            'Cache-Control': 'public, max-age=3600',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Expose-Headers': 'Content-Length, Content-Type'
        }
    )

@app.route('/synthesize', methods=['POST', 'OPTIONS'])
def synthesize():
    """Synthesize speech endpoint"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response(
            '',
            status=204,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
                'Access-Control-Max-Age': '3600'
            }
        )
    
    # Check authentication
    if not check_api_key():
        return jsonify({
            'error': 'Unauthorized: Invalid or missing API key',
            'hint': 'Provide X-API-Key header'
        }), 401
    
    try:
        # Parse request body
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing required field: text'}), 400
        
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'Text cannot be empty'}), 400
        
        # Detect language if not provided
        language_code = data.get('language_code')
        voice_name = data.get('voice_name')
        
        if not language_code or not voice_name:
            language_code, voice_name = detect_language(text)
        
        return_type = data.get('return_type', 'url')
        
        logger.info(f"Synthesizing speech: language={language_code}, text_length={len(text)}")
        
        # Synthesize speech using Google Cloud TTS
        audio_content = synthesize_speech_google(text, language_code, voice_name)
        
        # Handle return type
        if return_type == 'base64':
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
            return jsonify({
                'audio_base64': audio_base64,
                'language_detected': language_code,
                'format': 'mp3'
            }), 200
        
        # Default: return URL (store in cache and return Heroku URL)
        audio_id = str(uuid.uuid4())
        audio_cache[audio_id] = {
            'content': audio_content,
            'timestamp': datetime.utcnow(),
            'language': language_code
        }
        
        # Get the Heroku app URL from request
        base_url = request.host_url.rstrip('/')
        audio_url = f"{base_url}/audio/{audio_id}"
        
        # Also return base64 as fallback (for multi-dyno cache issues)
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        return jsonify({
            'audio_url': audio_url,
            'audio_base64': audio_base64,  # Fallback for cache misses
            'language_detected': language_code,
            'format': 'mp3',
            'size_bytes': len(audio_content)
        }), 200
        
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

