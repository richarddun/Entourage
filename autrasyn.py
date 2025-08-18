import wave
import openai
import boto3
from pydub import AudioSegment
from pydub.playback import play
import pyaudio
import time
import os
import json
try:
    from dotenv import dotenv_values
    env_vars = dotenv_values('.env')
except ImportError:
    print("Warning: python-dotenv is not installed, .env file will not be loaded")
    env_vars = {}

# create Class to handle integration with Amazon Polly
class PollyInterface():
    def __init__(self):
        # Create a Polly client with credentials from environment
        self.polly = boto3.client(
            'polly',
            region_name='eu-west-1',
            aws_access_key_id=env_vars.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=env_vars.get('AWS_SECRET_ACCESS_KEY')
        )
        # load configuration from json configuration file
        self.refresh_configuration()

        # Initialize PyAudio for playback
        self.audio: pyaudio.PyAudio
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = None
        except Exception as e:
            raise Exception(f"Error initializing PyAudio: {e}")

    def refresh_configuration(self):
        with open('configuration.json') as f:
            self.config = json.load(f)

    def play_audio_stream(self, audio_stream):
        """Play audio stream from Polly in chunks"""
        if self.stream is None:
            self.stream = self.audio.open(format=pyaudio.paInt16,
                                          channels=1,
                                          rate=16000,
                                          output=True)
        data = audio_stream.read(1024)
        while data:
            self.stream.write(data)
            data = audio_stream.read(1024)

    def synthesize_and_play(self, text_chunk):
        """Synthesize speech for a text chunk and play it immediately"""
        response = self.polly.synthesize_speech(
            Text=text_chunk,
            OutputFormat='pcm',
            VoiceId=self.config.get('voice_id', 'Joanna'),
            SampleRate='16000'
        )
        audio_stream = response['AudioStream']
        self.play_audio_stream(audio_stream)

    def say_streaming(self, text_generator):
        """Handle streaming text for voice output with incremental synthesis and playback"""
        self.refresh_configuration()
        buffer = ""
        for chunk in text_generator:
            buffer += chunk
            # Check for sentence end or buffer length threshold to synthesize
            if any(p in buffer for p in ['.', '!', '?']) or len(buffer) > 100:
                self.synthesize_and_play(buffer.strip())
                buffer = ""
        # Synthesize any remaining buffered text
        if buffer:
            self.synthesize_and_play(buffer.strip())

    def close(self):
        """Cleanup audio stream and PyAudio"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.audio:
            self.audio.terminate()

    def say(self, text):
        self.refresh_configuration()
        # Synthesize speech from the input text.
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
        # Initialize OpenAI client with API key from .env file
        self.client = openai.OpenAI(
            api_key=env_vars.get("OPENAI_API_KEY"),
            base_url="https://api.openai.com/v1"
        )

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
        self.transcript = self.client.audio.transcriptions.create(
            model="whisper-1",
            file=self.audio_file
        )
        # remove .wav and .mp3 files generated
        self.audio_file.close()
        os.remove(self.compressed_audio)
        os.remove(self.output_file_name)
        return self.transcript

    def quit(self):
        self.pa.terminate()
