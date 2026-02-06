"""
Speech Service - Handles text-to-speech
"""
import base64
from pathlib import Path
from typing import Optional
from gtts import gTTS
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class TextToSpeechService:
    """Service for converting text to speech using gTTS (Google Text-to-Speech)"""

    def __init__(self):
        """Initialize text-to-speech service"""
        logger.info("TextToSpeechService initialized with gTTS")

    def text_to_speech(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: str = "autumn",  # Kept for compatibility, mapped internally if needed or ignored
        response_format: str = "wav"
    ) -> bytes:
        """
        Convert text to speech

        Args:
            text: Text to convert to speech
            output_path: Optional path to save audio file
            voice: Voice style (ignored for gTTS standard, uses default)
            response_format: Audio format (mp3 recommended for gTTS)

        Returns:
            bytes: Audio data
        """
        try:
            # gTTS generates mp3 by default. We can convert if needed, but for web playback mp3 is fine.
            # We'll stick to mp3 as the native gTTS format.
            tts = gTTS(text=text, lang='en')
            
            import tempfile
            import os
            
            # Create a logical temporary file path
            if output_path:
                save_path = output_path
            else:
                # Use mp3 as default for gTTS
                fd, save_path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)

            tts.save(save_path)
            
            # Read back the data
            with open(save_path, "rb") as f:
                audio_data = f.read()

            # Clean up if we created a temp file
            if not output_path:
                os.remove(save_path)
            else:
                 logger.info(f"Speech audio saved to {output_path}")

            logger.info(f"Text converted to speech successfully")
            return audio_data

        except Exception as e:
            logger.error(f"Error converting text to speech: {str(e)}")
            raise

    def text_to_speech_base64(
        self,
        text: str,
        voice: str = "autumn",
        response_format: str = "wav"
    ) -> str:
        """
        Convert text to speech and return as base64 string

        Args:
            text: Text to convert to speech
            voice: Voice style
            response_format: Audio format

        Returns:
            str: Base64 encoded audio data
        """
        audio_data = self.text_to_speech(text, voice=voice, response_format=response_format)
        return base64.b64encode(audio_data).decode('utf-8')
