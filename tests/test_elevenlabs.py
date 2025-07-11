import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from dotenv import load_dotenv
import os
from elevenlabs.client import ElevenLabs
from fastapi import HTTPException
from datetime import datetime
from config.elevenlabs_voice_config import ELEVENLABS_VOICE_IDs, TONE_SETTINGS
from textblob import TextBlob

load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

async def convert_text_to_speech(answer: str, prompt: str = None, voice_name: str = "Sarah") -> str:
    """
    Convert text to speech using ElevenLabs with basic tone adjustment based on sentiment.
    """

    try:
        if not ELEVENLABS_API_KEY:
            raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not found in .env file")

        tone = "neutral"
        if prompt:
            analysis = TextBlob(prompt)
            polarity = analysis.sentiment.polarity
            subjectivity = analysis.sentiment.subjectivity

            if polarity > 0.4:
                tone = "happy"
            elif polarity < -0.6:
                tone = "sad"
            elif polarity < -0.3:
                tone = "serious"
            elif subjectivity > 0.6:
                tone = "empathetic"

        voice_id = ELEVENLABS_VOICE_IDs.get(voice_name, ELEVENLABS_VOICE_IDs["Sarah"])

        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio = client.text_to_speech.convert(
            text=answer,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            voice_settings=TONE_SETTINGS[tone]
        )

        # Save output
        output_path = f"data/model_outputs/output_{datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.mp3"
        os.makedirs("data/model_outputs", exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        return output_path

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating speech: {str(e)}")


async def test_tts():
    english_test_text = "Test of the ElevenLabs text-to-speech conversion."
    arabic_test_text = "هذا اختبار للنص العربي, هذا اختبار للنص العربي"
    try:
        output_file = await convert_text_to_speech(english_test_text)
        print(f"Audio file generated successfully: {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_tts())