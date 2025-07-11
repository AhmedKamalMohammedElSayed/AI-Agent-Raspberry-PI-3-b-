import requests
import os

audio_file_path = "data/audio_prompts/audio.wav"
if not os.path.exists(audio_file_path):
    print(f"Error: File not found at {audio_file_path}")
    exit(1)

with open(audio_file_path, 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/process_audio', files=files)
    # response = requests.post('http://localhost:8000/process_audio', files=files, params={'new_conv': True})
    
    if response.status_code == 200:
        print("Success!")
        print("Response:", response.content)
    else:
        print("Error:", response.status_code)
        print("Response:", response.text)
