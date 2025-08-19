import pyaudio
import threading
import queue
import time
from collections import deque

class BufferedAudioPlayer:
    """
    A buffered audio player that should provide smoother playback on lower-end hardware.
    Uses a separate thread for audio output and maintains a buffer to prevent dropouts.
    """

    def __init__(self, sample_rate=44100, channels=1, format=pyaudio.paInt16,
                 chunk_size=8192, buffer_size=5):
        """
        :param sample_rate: Audio sample rate (Hz).
        :param channels: Number of audio channels.
        :param format: PyAudio format.
        :param chunk_size: Size of audio chunks for PyAudio.
        :param buffer_size: Number of chunks to buffer ahead.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.format = format
        self.chunk_size = chunk_size
        self.buffer_size = buffer_size

        self.p = pyaudio.PyAudio()
        self.stream = None
        self.audio_queue = queue.Queue(maxsize=buffer_size * 2)
        self.playback_thread = None
        self.stop_event = threading.Event()
        self.debug = True

    def _playback_worker(self):
        """Worker thread that handles audio playback."""
        try:
            self.stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size
            )

            if self.debug:
                print(f"[BufferedPlayer] Playback thread started")

            chunk_count = 0
            while not self.stop_event.is_set():
                try:
                    # Get audio chunk with timeout
                    chunk = self.audio_queue.get(timeout=0.1)
                    if chunk is None:  # Sentinel value to stop
                        break

                    self.stream.write(chunk)
                    chunk_count += 1

                    if self.debug and chunk_count % 10 == 0:
                        queue_size = self.audio_queue.qsize()
                        print(f"[BufferedPlayer] Played {chunk_count} chunks, queue: {queue_size}")

                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[BufferedPlayer] Playback error: {e}")
                    break

            if self.debug:
                print(f"[BufferedPlayer] Playback thread finished after {chunk_count} chunks")

        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()

    def play(self, audio_chunks):
        """
        Plays audio chunks using buffered playback.
        :param audio_chunks: Generator or iterable yielding PCM audio bytes.
        """
        try:
            # Start playback thread
            self.stop_event.clear()
            self.playback_thread = threading.Thread(target=self._playback_worker)
            self.playback_thread.start()

            if self.debug:
                print(f"[BufferedPlayer] Starting to queue audio chunks")

            chunk_count = 0
            for chunk in audio_chunks:
                if not chunk:
                    continue

                # Split large chunks into smaller ones for better buffering
                for i in range(0, len(chunk), self.chunk_size):
                    sub_chunk = chunk[i:i + self.chunk_size]

                    # Queue the chunk (this will block if buffer is full, providing backpressure)
                    self.audio_queue.put(sub_chunk)
                    chunk_count += 1

                    if self.debug and chunk_count % 20 == 0:
                        queue_size = self.audio_queue.qsize()
                        print(f"[BufferedPlayer] Queued {chunk_count} sub-chunks, buffer: {queue_size}/{self.buffer_size * 2}")

            # Signal end of audio
            self.audio_queue.put(None)

            if self.debug:
                print(f"[BufferedPlayer] Finished queueing {chunk_count} chunks")

        except Exception as e:
            print(f"[BufferedPlayer] Error during playback setup: {e}")
            self.stop_event.set()
            raise
        finally:
            # Wait for playback to complete
            if self.playback_thread:
                self.playback_thread.join(timeout=10)
            self.p.terminate()


class SimpleAudioPlayer:
    """
    Simplified audio player that avoids MP3 decoding issues by using larger buffers
    and more conservative playback settings.
    """

    def __init__(self, sample_rate=22050, channels=1, format=pyaudio.paInt16, chunk_size=16384):
        """
        Uses lower sample rate and larger chunks for more reliable playback on slower hardware.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.format = format
        self.chunk_size = chunk_size
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.debug = True

    def play(self, audio_chunks):
        """
        Simple blocking playback with larger buffers.
        """
        if self.debug:
            print(f"[SimplePlayer] Starting playback (rate={self.sample_rate}, chunk={self.chunk_size})")

        self.stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=self.chunk_size
        )

        try:
            chunk_count = 0
            for chunk in audio_chunks:
                if chunk:
                    # Pad chunks to avoid underruns
                    if len(chunk) < self.chunk_size:
                        padding = b'\x00' * (self.chunk_size - len(chunk))
                        chunk = chunk + padding

                    self.stream.write(chunk)
                    chunk_count += 1

                    # Add small delay to prevent overwhelming the audio subsystem
                    if chunk_count % 5 == 0:
                        time.sleep(0.001)

            if self.debug:
                print(f"[SimplePlayer] Completed playback of {chunk_count} chunks")

        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
