"""
Azure Function for WhatsApp → Agentforce Integration
"""

import azure.functions as func
import os
import json
import base64
import requests
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

AGENTFORCE_AGENT_ID = os.environ.get('AGENTFORCE_AGENT_ID', '0XxKB000000La8H0AS')
SALESFORCE_CONSUMER_KEY = os.environ.get('SALESFORCE_CONSUMER_KEY')
SALESFORCE_CONSUMER_SECRET = os.environ.get('SALESFORCE_CONSUMER_SECRET')
SALESFORCE_INSTANCE_URL = os.environ.get('SALESFORCE_INSTANCE_URL')

GOOGLE_CLOUD_API_KEY = os.environ.get('GOOGLE_CLOUD_API_KEY')

# API Endpoints
AGENTFORCE_API_BASE = 'https://api.salesforce.com/einstein/ai-agent/v1'
GOOGLE_STT_ENDPOINT = 'https://speech.googleapis.com/v1/speech:recognize'
GOOGLE_TTS_ENDPOINT = 'https://texttospeech.googleapis.com/v1/text:synthesize'

# In-memory session storage
sessions: Dict[str, Dict] = {}


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function entry point"""
    try:
        if req.method == 'GET':
            return func.HttpResponse('OK', status_code=200)
        
        # Get webhook data
        try:
            data = req.get_json()
        except:
            data = dict(req.form)
        
        logger.info(f"Received webhook: {json.dumps(data, indent=2)}")
        
        # Extract message details
        from_number = data.get('From', '').replace('whatsapp:', '')
        message_sid = data.get('MessageSid', '')
        num_media = int(data.get('NumMedia', '0'))
        
        if num_media > 0:
            # Voice message
            media_url = data.get('MediaUrl0', '')
            media_content_type = data.get('MediaContentType0', '')
            logger.info(f"Voice message detected: {media_url}")
            result = handle_voice_message(from_number, message_sid, media_url, media_content_type)
        else:
            # Text message
            message_text = data.get('Body', '')
            logger.info(f"Text message: {message_text}")
            result = handle_text_message(from_number, message_sid, message_text)
        
        return func.HttpResponse('OK', status_code=200)
    
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        return func.HttpResponse(json.dumps({'error': 'Internal server error'}), status_code=500, mimetype='application/json')


def handle_text_message(from_number: str, message_sid: str, message_text: str):
    """Handle text message from WhatsApp"""
    try:
        response_text = send_to_agentforce(from_number, message_text)
        send_whatsapp_message(from_number, response_text)
        return True
    except Exception as e:
        logger.error(f"Error handling text message: {str(e)}", exc_info=True)
        send_whatsapp_message(from_number, "Sorry, I encountered an error. Please try again.")
        return False


def handle_voice_message(from_number: str, message_sid: str, media_url: str, content_type: str):
    """Handle voice message from WhatsApp"""
    try:
        audio_data = download_twilio_media(media_url)
        transcribed_text = google_stt(audio_data, content_type)
        response_text = send_to_agentforce(from_number, transcribed_text)
        audio_base64 = google_tts(response_text)
        send_whatsapp_voice_message(from_number, response_text, audio_base64)
        return True
    except Exception as e:
        logger.error(f"Error handling voice message: {str(e)}", exc_info=True)
        send_whatsapp_message(from_number, "Sorry, I couldn't process your voice message. Please try typing your message.")
        return False


def download_twilio_media(media_url: str) -> bytes:
    """Download media file from Twilio"""
    response = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    response.raise_for_status()
    return response.content


def google_stt(audio_data: bytes, content_type: str) -> str:
    """Convert speech to text using Google Cloud STT"""
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    encoding = 'LINEAR16'
    sample_rate = 16000
    
    if 'ogg' in content_type.lower() or 'opus' in content_type.lower():
        encoding = 'OGG_OPUS'
        sample_rate = 48000
    elif 'mp3' in content_type.lower():
        encoding = 'MP3'
        sample_rate = 44100
    
    payload = {
        'config': {
            'encoding': encoding,
            'sampleRateHertz': sample_rate,
            'languageCode': 'ar-EG',
            'alternativeLanguageCodes': ['en-US'],
            'enableAutomaticPunctuation': True,
            'model': 'chirp'
        },
        'audio': {
            'content': audio_base64
        }
    }
    
    url = f"{GOOGLE_STT_ENDPOINT}?key={GOOGLE_CLOUD_API_KEY}"
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    result = response.json()
    if 'results' in result and len(result['results']) > 0:
        transcript = result['results'][0].get('alternatives', [{}])[0].get('transcript', '')
        if transcript:
            return transcript
    
    raise Exception("No transcription found")


def google_tts(text: str) -> str:
    """Convert text to speech using Google Cloud TTS"""
    language_code = 'ar-EG'
    voice_name = 'ar-XA-Standard-A'
    
    if sum(1 for c in text if ord(c) < 128) > len(text) * 0.7:
        language_code = 'en-US'
        voice_name = 'en-US-Standard-A'
    
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
    
    url = f"{GOOGLE_TTS_ENDPOINT}?key={GOOGLE_CLOUD_API_KEY}"
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    result = response.json()
    audio_content = result.get('audioContent', '')
    if not audio_content:
        raise Exception("No audio content found")
    
    return audio_content


def get_agentforce_session(from_number: str) -> str:
    """Get or create Agentforce session"""
    if from_number in sessions:
        session_data = sessions[from_number]
        if datetime.now() - session_data['created_at'] < timedelta(minutes=30):
            return session_data['session_id']
    
    logger.info(f"Creating new Agentforce session for {from_number}")
    access_token = get_salesforce_token()
    
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
    
    sessions[from_number] = {
        'session_id': session_id,
        'created_at': datetime.now(),
        'sequence_id': 0
    }
    
    return session_id


def send_to_agentforce(from_number: str, message_text: str) -> str:
    """Send message to Agentforce and get response"""
    session_id = get_agentforce_session(from_number)
    session_data = sessions[from_number]
    sequence_id = session_data['sequence_id'] + 1
    session_data['sequence_id'] = sequence_id
    
    access_token = get_salesforce_token()
    
    message_payload = {
        'message': {
            'sequenceId': sequence_id,
            'type': 'Text',
            'text': message_text
        },
        'variables': []
    }
    
    url = f"{AGENTFORCE_API_BASE}/agents/{AGENTFORCE_AGENT_ID}/sessions/{session_id}/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, json=message_payload, headers=headers, timeout=120)
    response.raise_for_status()
    
    result = response.json()
    messages = result.get('messages', [])
    if messages:
        return messages[0].get('message', '')
    
    return "I received your message, but couldn't generate a response. Please try again."


def get_salesforce_token() -> str:
    """Get Salesforce OAuth access token"""
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
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    
    payload = {
        'From': TWILIO_WHATSAPP_FROM,
        'To': f"whatsapp:{to_number}",
        'Body': message_text
    }
    
    response = requests.post(url, data=payload, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    response.raise_for_status()


def send_whatsapp_voice_message(to_number: str, text_message: str, audio_base64: str):
    """Send voice message via Twilio WhatsApp"""
    send_whatsapp_message(to_number, text_message)







