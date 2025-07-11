import sounddevice as sd
import numpy as np
import wavio
import os
from datetime import datetime

def record_audio(duration=5, sample_rate=44100):
    """
    Record audio from microphone and save it as a WAV file
    """
    print(f"Recording for {duration} seconds...")
    
    recording = sd.rec(int(duration * sample_rate), 
                      samplerate=sample_rate, 
                      channels=1)
    
    sd.wait()
    os.makedirs('data/audio_prompts', exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'data/audio_prompts/a_recording_{timestamp}.wav'
    wavio.write(filename, recording, sample_rate, sampwidth=2)
    
    print(f"Recording saved as {filename}")
    return filename

if __name__ == "__main__":
    try:
        duration = int(input("Enter recording duration (in seconds): "))
        if duration <= 0:
            raise ValueError("Duration must be greater than 0")
    except ValueError as e:
        print(f"Invalid input: {str(e)}")
        duration = 5
        print(f"Using default duration of {duration} seconds")
    
    record_audio(duration)
