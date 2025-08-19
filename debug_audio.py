#!/usr/bin/env python3
"""
Audio debugging script for Entourage TTS playback issues.
This script tests different audio configurations to help diagnose choppy playback.
"""

import time
import sys
import os
import pyaudio
from dotenv import dotenv_values

# Add the current directory to Python path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tts.elevenlabs_client import ElevenLabsTTSClient
from tts.audio_player import StreamingAudioPlayer
from tts.buffered_audio_player import BufferedAudioPlayer, SimpleAudioPlayer
from tts.mp3_decoder import mp3_chunks_to_pcm, mp3_chunks_to_pcm_buffered

def test_system_info():
    """Test system audio capabilities."""
    print("=== SYSTEM AUDIO INFO ===")
    p = pyaudio.PyAudio()

    print(f"PyAudio version: {pyaudio.__version__}")
    try:
        print(f"PortAudio version: {p.get_portaudio_version()}")
    except AttributeError:
        print("PortAudio version: Not available in this PyAudio version")
    try:
        print(f"Default output device: {p.get_default_output_device_info()}")
    except Exception as e:
        print(f"Default output device: Error - {e}")

    # List available audio devices
    print(f"Available audio devices:")
    try:
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                print(f"  {i}: {info['name']} (channels: {info['maxOutputChannels']}, rate: {info['defaultSampleRate']})")
    except Exception as e:
        print(f"  Error listing devices: {e}")

    p.terminate()
    print()

def test_elevenlabs_connection():
    """Test ElevenLabs API connection."""
    print("=== ELEVENLABS CONNECTION TEST ===")

    try:
        env_vars = dotenv_values('.env')
        api_key = env_vars.get('ELEVENLABS_API_KEY')

        if not api_key:
            print("❌ No ELEVENLABS_API_KEY found in .env file")
            return None

        client = ElevenLabsTTSClient(api_key=api_key)
        print("✅ ElevenLabs client created successfully")

        # Test a very short synthesis
        test_text = "Test"
        voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel

        print(f"Testing synthesis with voice: {voice_id}")
        audio_chunks = list(client.stream(test_text, voice_id))
        total_bytes = sum(len(chunk) for chunk in audio_chunks)
        print(f"✅ Generated {len(audio_chunks)} chunks, {total_bytes} bytes total")

        return client

    except Exception as e:
        print(f"❌ ElevenLabs test failed: {e}")
        return None

def test_mp3_decoding_performance(client, test_text="Hello, this is a test of the audio system."):
    """Test MP3 decoding performance with different buffer sizes."""
    if not client:
        print("⚠️  Skipping MP3 decoding test - no ElevenLabs client")
        return

    print("=== MP3 DECODING PERFORMANCE TEST ===")
    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    for buffer_size in [4096, 8192, 16384, 32768]:
        print(f"\nTesting buffer size: {buffer_size}")
        try:
            start_time = time.time()
            audio_chunks = client.stream(test_text, voice_id)
            pcm_chunks = list(mp3_chunks_to_pcm(audio_chunks, min_buffer_size=buffer_size))
            decode_time = time.time() - start_time

            total_pcm_bytes = sum(len(chunk) for chunk in pcm_chunks)
            print(f"  ✅ Decoded {len(pcm_chunks)} PCM chunks, {total_pcm_bytes} bytes in {decode_time:.3f}s")

        except Exception as e:
            print(f"  ❌ Failed with buffer size {buffer_size}: {e}")

    # Test buffered decoder
    print(f"\nTesting buffered decoder:")
    try:
        start_time = time.time()
        audio_chunks = client.stream(test_text, voice_id)
        pcm_chunks = list(mp3_chunks_to_pcm_buffered(audio_chunks, buffer_duration_ms=500))
        decode_time = time.time() - start_time

        total_pcm_bytes = sum(len(chunk) for chunk in pcm_chunks)
        print(f"  ✅ Buffered decoder: {len(pcm_chunks)} PCM chunks, {total_pcm_bytes} bytes in {decode_time:.3f}s")

    except Exception as e:
        print(f"  ❌ Buffered decoder failed: {e}")

def test_audio_players(client, test_text="This is a longer test to check audio player performance."):
    """Test different audio player implementations."""
    if not client:
        print("⚠️  Skipping audio player test - no ElevenLabs client")
        return

    print("=== AUDIO PLAYER PERFORMANCE TEST ===")
    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    players = [
        ("StreamingAudioPlayer (Original)", StreamingAudioPlayer),
        ("StreamingAudioPlayer (8K buffer)", lambda: StreamingAudioPlayer(chunk_size=8192)),
        ("StreamingAudioPlayer (16K buffer)", lambda: StreamingAudioPlayer(chunk_size=16384)),
        ("BufferedAudioPlayer", BufferedAudioPlayer),
        ("SimpleAudioPlayer (22kHz)", SimpleAudioPlayer)
    ]

    for name, player_factory in players:
        print(f"\nTesting {name}:")
        try:
            # Generate audio
            audio_chunks = client.stream(test_text, voice_id)
            pcm_chunks = mp3_chunks_to_pcm(audio_chunks, min_buffer_size=16384)

            # Test playback
            player = player_factory()
            start_time = time.time()
            player.play(pcm_chunks)
            playback_time = time.time() - start_time

            print(f"  ✅ Playback completed in {playback_time:.3f}s")

        except Exception as e:
            print(f"  ❌ {name} failed: {e}")

def test_simple_tone():
    """Generate and play a simple sine wave to test basic audio functionality."""
    print("=== SIMPLE TONE TEST ===")

    import numpy as np

    try:
        # Generate a 1-second 440Hz sine wave
        sample_rate = 44100
        duration = 1.0
        frequency = 440.0

        t = np.linspace(0, duration, int(sample_rate * duration))
        wave = (32767 * np.sin(2 * np.pi * frequency * t)).astype(np.int16)

        # Convert to bytes
        audio_bytes = wave.tobytes()

        # Test with different players
        players = [
            ("StreamingAudioPlayer", StreamingAudioPlayer()),
            ("SimpleAudioPlayer", SimpleAudioPlayer())
        ]

        for name, player in players:
            print(f"Testing {name} with sine wave...")
            try:
                start_time = time.time()
                player.play([audio_bytes])
                playback_time = time.time() - start_time
                print(f"  ✅ {name}: Sine wave played in {playback_time:.3f}s")
            except Exception as e:
                print(f"  ❌ {name}: Failed to play sine wave: {e}")

    except ImportError:
        print("⚠️  NumPy not available - skipping sine wave test")
    except Exception as e:
        print(f"❌ Sine wave test failed: {e}")

def main():
    """Run all audio debugging tests."""
    print("🔊 Entourage Audio Debugging Tool")
    print("=" * 50)

    # System info
    test_system_info()

    # ElevenLabs connection
    client = test_elevenlabs_connection()

    # MP3 decoding performance
    test_mp3_decoding_performance(client)

    # Simple tone test (doesn't require ElevenLabs)
    test_simple_tone()

    # Audio player tests (requires ElevenLabs)
    if client:
        print("\nDo you want to test audio playback? This will play audio through your speakers.")
        response = input("Type 'yes' to continue: ").lower()
        if response == 'yes':
            test_audio_players(client)
        else:
            print("⚠️  Skipping audio playback tests")

    print("\n🏁 Audio debugging complete!")
    print("\nIf you're experiencing choppy audio, try:")
    print("1. Use BufferedAudioPlayer instead of StreamingAudioPlayer")
    print("2. Increase buffer sizes (16384 or higher)")
    print("3. Use the buffered MP3 decoder")
    print("4. Check if other audio applications are running")
    print("5. Try the SimpleAudioPlayer with lower sample rate")

if __name__ == "__main__":
    main()
