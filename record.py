import sounddevice as sd
import numpy as np
import wavio
import os
from datetime import datetime

def record_audio(duration=5, sample_rate=44100):
    """
    Record audio from microphone and save it as a WAV file
    
    Args:
        duration (int): Recording duration in seconds
        sample_rate (int): Sample rate for recording
    """
    print(f"Recording for {duration} seconds...")
    
    # Record audio
    recording = sd.rec(int(duration * sample_rate), 
                      samplerate=sample_rate, 
                      channels=1)
    
    # Wait for recording to complete
    sd.wait()
    
    # Create audio_prompts directory if it doesn't exist
    os.makedirs('audio_prompts', exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'audio_prompts/a_recording_{timestamp}.wav'
    
    # Save the recording
    wavio.write(filename, recording, sample_rate, sampwidth=2)
    
    print(f"Recording saved as {filename}")
    return filename

if __name__ == "__main__":
    # Ask user for recording duration
    try:
        duration = int(input("Enter recording duration (in seconds): "))
        if duration <= 0:
            raise ValueError("Duration must be greater than 0")
    except ValueError as e:
        print(f"Invalid input: {str(e)}")
        duration = 5  # Default duration
        print(f"Using default duration of {duration} seconds")
    
    # Record and save audio
    record_audio(duration)
