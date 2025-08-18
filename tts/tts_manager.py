from .audio_player import StreamingAudioPlayer
from .mp3_decoder import mp3_chunks_to_pcm
from .polly_client import PollyTTSClient
from .elevenlabs_client import ElevenLabsTTSClient

class TTSManager:
    """
    Manages TTS provider selection, streaming, and playback.
    Handles both streaming (ElevenLabs) and non-streaming (Polly) providers.
    """

    def __init__(self, tts_client, is_streaming=True):
        """
        :param tts_client: Instance of BaseTTSClient (Polly or ElevenLabs)
        :param is_streaming: True if provider supports streaming (ElevenLabs), False for full-file (Polly)
        """
        self.tts_client = tts_client
        self.is_streaming = is_streaming
        self.player = StreamingAudioPlayer()

    def speak(self, text, voice_id, **kwargs):
        """
        Synthesizes speech and plays it back.
        For streaming providers, audio is played as chunks arrive.
        For non-streaming providers, the full file is played after retrieval.
        :param text: Text to synthesize
        :param voice_id: Voice identifier
        :param kwargs: Additional provider-specific arguments
        """
        audio_chunks = self.tts_client.stream(text, voice_id, **kwargs)
        if self.is_streaming:
            # ElevenLabs streams MP3; decode to PCM and play
            pcm_chunks = mp3_chunks_to_pcm(audio_chunks)
            self.player.play(pcm_chunks)
        else:
            # Polly yields the full audio at once (PCM or MP3)
            audio_data = next(audio_chunks)
            self.player.play([audio_data])

    def list_voices(self):
        """
        Returns a list of available voices from the current provider.
        """
        return self.tts_client.list_voices()

    @staticmethod
    def from_config(provider, **kwargs):
        """
        Factory method to instantiate TTSManager with the correct client and streaming flag.
        :param provider: "polly" or "elevenlabs"
        :param kwargs: Additional arguments for the TTS client (e.g., API keys)
        :return: TTSManager instance
        """
        from dotenv import dotenv_values
        env_vars = dotenv_values('.env')
        if provider == "elevenlabs":
            api_key = kwargs.get("api_key") or env_vars.get("ELEVENLABS_API_KEY")
            client = ElevenLabsTTSClient(api_key=api_key, model_id=kwargs.get("model_id", "eleven_multilingual_v2"))
            return TTSManager(client, is_streaming=True)
        elif provider == "polly":
            client = PollyTTSClient(
                region_name=kwargs.get("region_name", "us-east-1"),
                aws_access_key_id=kwargs.get("aws_access_key_id"),
                aws_secret_access_key=kwargs.get("aws_secret_access_key"),
            )
            return TTSManager(client, is_streaming=False)
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")
