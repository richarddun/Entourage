from pydub import AudioSegment
import io

def mp3_chunks_to_pcm(chunks, min_buffer_size=4096):
    """
    Generator that takes an iterable of MP3 audio chunks (bytes) and yields PCM raw audio data.
    Designed for streaming audio playback with PyAudio.

    Args:
        chunks: Iterable yielding MP3 bytes (e.g., from ElevenLabs streaming API).
        min_buffer_size: Minimum number of bytes to buffer before attempting to decode.

    Yields:
        PCM raw audio bytes suitable for PyAudio playback.
    """
    buffer = io.BytesIO()
    for chunk in chunks:
        if not chunk:
            continue
        buffer.write(chunk)
        # Only attempt to decode if we have enough data
        if buffer.tell() < min_buffer_size:
            continue
        buffer.seek(0)
        try:
            audio = AudioSegment.from_file(buffer, format="mp3")
            yield audio.raw_data
            # Reset buffer for next chunk
            buffer = io.BytesIO()
        except Exception:
            # Not enough data yet, continue buffering
            buffer.seek(0, io.SEEK_END)
    # Try to flush remaining buffer at the end
    buffer.seek(0)
    try:
        if buffer.getbuffer().nbytes > 0:
            audio = AudioSegment.from_file(buffer, format="mp3")
            yield audio.raw_data
    except Exception:
        pass
