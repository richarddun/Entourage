from elevenlabs.client import ElevenLabs
from .base import BaseTTSClient

class ElevenLabsTTSClient(BaseTTSClient):
    """
    ElevenLabs TTS client supporting streaming and voice listing.
    """

    def __init__(self, api_key=None, model_id="eleven_multilingual_v2"):
        self.client = ElevenLabs(api_key=api_key)
        self.model_id = model_id

    def stream(self, text, voice_id, **kwargs):
        """
        Streams audio chunks (as bytes) from ElevenLabs TTS.
        Yields PCM-encoded MP3 chunks.
        """
        # model_id and other keyword overrides
        model_id = kwargs.get("model_id", self.model_id)
        audio_stream = self.client.text_to_speech.stream(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
        )
        for chunk in audio_stream:
            if isinstance(chunk, bytes):
                yield chunk

    def list_voices(self):
        """
        Returns a list of available voices (as dicts).
        """
        response = self.client.voices.search()
        return response.voices
