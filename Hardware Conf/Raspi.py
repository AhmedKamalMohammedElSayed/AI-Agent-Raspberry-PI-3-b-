import RPi.GPIO as GPIO
import time
import pyaudio
import wave
import numpy as np
import requests
from elevenlabs.client import ElevenLabs
from textblob import TextBlob
from datetime import datetime
import asyncio
import subprocess
import pygame

# === Constants ===
API_ENDPOINT = "http://192.168.1.4:8000/process_audio"

ELEVENLABS_VOICE_IDs = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Domi": "AZnzlk1XvdvUeBnXmlld",
    "Bella": "EXAVITQu4vr4xnSDxMaL",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX",
    "Arnold": "VR6AewLTigWG4xSOukaG",
    "Clyde": "2EiwWnXFnvU5JabPnv8n",
    "Charlotte": "XB0fDUnXU5powFXDhCwa",
    "Sarah": "EXAVITQu4vr4xnSDxMaL",
    "Laura": "FGY2WhTYpPnrIDTdsKH5",
    "Brian": "nPczCjzI2devNBz1zQrb",
    "Bill": "pqHfZKP75CvOlQylNhV4",
}

TONE_SETTINGS = {
    "neutral": {"stability": 0.5, "similarity_boost": 0.75},
    "happy": {"stability": 0.3, "similarity_boost": 0.85},
    "serious": {"stability": 0.7, "similarity_boost": 0.65},
    "empathetic": {"stability": 0.4, "similarity_boost": 0.85},
    "sad": {"stability": 0.6, "similarity_boost": 0.8},
}

# === Keypad Setup ===
KEYPAD = [["1", "2"], ["3", "4"]]
ROW_PINS = [17, 27]
COL_PINS = [23, 16]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for row in ROW_PINS:
    GPIO.setup(row, GPIO.IN, pull_up_down=GPIO.PUD_UP)
for col in COL_PINS:
    GPIO.setup(col, GPIO.OUT)
    GPIO.output(col, GPIO.HIGH)

def scan_keypad():
    for col_index, col_pin in enumerate(COL_PINS):
        GPIO.output(col_pin, GPIO.LOW)
        for row_index, row_pin in enumerate(ROW_PINS):
            if GPIO.input(row_pin) == GPIO.LOW:
                time.sleep(0.05)
                if GPIO.input(row_pin) == GPIO.LOW:
                    GPIO.output(col_pin, GPIO.HIGH)
                    return KEYPAD[row_index][col_index]
        GPIO.output(col_pin, GPIO.HIGH)
    return None

# === Audio Parameters ===
CHANNELS = 2
RATE = 48000
CHUNK = 1024
FORMAT = pyaudio.paInt32
DEVICE_INDEX = 1
WAVE_OUTPUT_FILENAME = "voicehat_output_amplified.wav"
GAIN = 5.0

audio = pyaudio.PyAudio()
frames = []
stream = None
recording = False

print("Press '1' to start recording and '3' to stop and save:")

async def convert_text_to_speech(answer: str, prompt: str = None, voice_name: str = "Sarah") -> str:
    try:
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

        voice_id = ELEVENLABS_VOICE_IDs[voice_name]
        client = ElevenLabs(api_key="sk_67f2bcdec3acc18a6509389180c751b0078f4a0494dff747")

        audio_stream = client.text_to_speech.convert(
            text=answer,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            voice_settings=TONE_SETTINGS[tone],
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"tts_output_{timestamp}.wav"

        with open(output_path, "wb") as audio_file:
            for chunk in audio_stream:
                audio_file.write(chunk)

        print(f"Saved text-to-speech audio: {output_path}")
        return output_path

    except Exception as e:
        print(f"Error generating speech: {str(e)}")
        return None

def convert_to_pcm(input_path, output_path):
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-ar", "44100", "-ac", "2", "-sample_fmt", "s16",
            output_path
        ], check=True)
        print("File converted successfully to PCM format.")
        return True
    except subprocess.CalledProcessError:
        print("FFmpeg failed to convert the file.")
        return False

try:
    while True:
        key = scan_keypad()
        if key:
            print(f"You pressed: {key}")

            if key == "1" and not recording:
                try:
                    stream = audio.open(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=DEVICE_INDEX,
                        frames_per_buffer=CHUNK,
                    )
                    frames = []
                    recording = True
                    print("Recording started...")
                except Exception as e:
                    print(f"Error opening stream: {e}")
                    recording = False

            elif key == "3" and recording:
                recording = False
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception as e:
                    print(f"Error stopping stream: {e}")

                print("Recording stopped. Saving...")

                raw_audio = b"".join(frames)
                audio_np = np.frombuffer(raw_audio, dtype=np.int32)
                amplified = np.clip(
                    audio_np * GAIN, np.iinfo(np.int32).min, np.iinfo(np.int32).max
                ).astype(np.int32)

                with wave.open(WAVE_OUTPUT_FILENAME, "wb") as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(amplified.tobytes())

                print(f"Saved amplified file: {WAVE_OUTPUT_FILENAME}")

                with open(WAVE_OUTPUT_FILENAME, "rb") as audio_file:
                    files = {"file": audio_file}
                    response = requests.post(API_ENDPOINT, files=files)
                    if response.status_code == 200:
                        response_data = response.json()
                        response_text = response_data.get("response", "")
                        response_voice = response_data.get("voice", "Sarah")
                        print(f"API Response: {response_text}")
                        print(f"Voice: {response_voice}")

                        audio_path = asyncio.run(
                            convert_text_to_speech(
                                answer=response_text,
                                voice_name=response_voice
                            )
                        )

                        if audio_path:
                            pcm_output = "converted_output.wav"
                            if convert_to_pcm(audio_path, pcm_output):
                                pygame.mixer.init()
                                pygame.mixer.music.load(pcm_output)
                                pygame.mixer.music.play()
                                while pygame.mixer.music.get_busy():
                                    pygame.time.Clock().tick(10)
                    else:
                        print(f"API request failed with status code: {response.status_code}")

        if recording and stream is not None:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            except IOError as e:
                print(f"Recording error: {e}")
                time.sleep(0.1)

except KeyboardInterrupt:
    print("Interrupted by user.")

finally:
    if stream is not None:
        stream.stop_stream()
        stream.close()
    audio.terminate()
    GPIO.cleanup()
    print("GPIO cleaned up.")
