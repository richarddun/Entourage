import wave
import openai
import boto3
from pydub import AudioSegment
from pydub.playback import play
import pyaudio
import time 
import os
import json

# create Class to handle integration with Amazon Polly
class PollyInterface():
    def __init__(self):
        # Create a Polly client
        self.polly = boto3.client('polly',region_name='eu-west-1')
        # load configuration from json configuration file

    def refresh_configuration(self):
        with open('configuration.json') as f:
            self.config = json.load(f)


    def say(self, text):
        self.refresh_configuration()
        # Synthesize speech from the input text.
        # TODO - implement streaming
        response = self.polly.synthesize_speech(
            OutputFormat='mp3',
            Text=text,
            Engine='neural',
            VoiceId=self.config['voice_id']
        )

        # Save the audio stream to a .mp3 file
        with open('speech.mp3', 'wb') as f:
            f.write(response['AudioStream'].read())
        # play the audio stream immediately using pydub
        sound = AudioSegment.from_mp3("speech.mp3")
        play(sound)
        os.remove("speech.mp3")

class AudioInterface():
    def __init__(self):
        # Create a PyAudio object
        self.pa = pyaudio.PyAudio()
        self.recording = False
    
    def stop_record_audio(self):
        self.recording = False

    def start_record_audio(self):
        # Open a microphone stream

        self.stream = self.pa.open(format=pyaudio.paInt16, channels=2, rate=44100, input=True, frames_per_buffer=1024)#,
        #                            input_device_index=1)

        self.recording = True
        self.audio_data = []
        while self.recording:
            self.data = self.stream.read(1024)
            self.audio_data.append(self.data)
        # Stop recording
        self.stream.stop_stream()
        self.stream.close()
        #self.pa.terminate()

        # generate the output file name based on epoch now
        self.output_file_name = str(time.time()) + ".wav"

        # Write the audio data to a WAV file
        with wave.open(self.output_file_name, 'wb') as f:
            f.setnchannels(2)
            f.setsampwidth(self.pa.get_sample_size(pyaudio.paInt16))
            f.setframerate(44100)
            f.writeframes(b''.join(self.audio_data))

        # convert output_file_name to mp3
        sound = AudioSegment.from_wav(self.output_file_name)
        sound.export(self.output_file_name[:-4] + ".mp3", format="mp3")
        self.compressed_audio = self.output_file_name[:-4] + ".mp3"
        
    def transcribe_audio(self):
        self.audio_file = open(self.compressed_audio, "rb")
        self.transcript = openai.Audio.transcribe("whisper-1",self.audio_file)
        # remove .wav and .mp3 files generated 
        self.audio_file.close()
        os.remove(self.compressed_audio)
        os.remove(self.output_file_name)
        return self.transcript

    def quit(self):
        self.pa.terminate()
