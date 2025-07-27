import pyaudio

class StreamingAudioPlayer:
    """
    Plays PCM audio data from a generator of audio chunks using PyAudio.
    Intended for use with streaming TTS outputs (e.g., ElevenLabs, Polly PCM).
    """

    def __init__(self, sample_rate=44100, channels=1, format=pyaudio.paInt16, chunk_size=4096):
        """
        :param sample_rate: Audio sample rate (Hz).
        :param channels: Number of audio channels.
        :param format: PyAudio format (e.g., pyaudio.paInt16 for 16-bit PCM).
        :param chunk_size: Number of bytes per write to the audio stream.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.format = format
        self.chunk_size = chunk_size
        self.p = pyaudio.PyAudio()
        self.stream = None

    def play(self, audio_chunks):
        """
        Plays audio chunks (bytes) as they arrive from the generator.
        :param audio_chunks: Generator or iterable yielding PCM audio bytes.
        """
        self.stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=self.chunk_size
        )
        try:
            for chunk in audio_chunks:
                if chunk:
                    self.stream.write(chunk)
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
