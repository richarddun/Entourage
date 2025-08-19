#!/usr/bin/env python3
"""
Quick audio test script for debugging choppy ElevenLabs playback.
This script provides a fast way to test different audio configurations.
"""

import sys
import os
import time
from dotenv import dotenv_values

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tts.elevenlabs_client import ElevenLabsTTSClient
from tts.audio_player import StreamingAudioPlayer
from tts.buffered_audio_player import BufferedAudioPlayer, SimpleAudioPlayer
from tts.mp3_decoder import mp3_chunks_to_pcm, mp3_chunks_to_pcm_buffered

def quick_test():
    """Quick test of different audio configurations."""
    print("🔊 Quick Audio Test for Choppy Playback Issues")
    print("=" * 50)

    # Load environment
    env_vars = dotenv_values('.env')
    api_key = env_vars.get('ELEVENLABS_API_KEY')

    if not api_key:
        print("❌ No ELEVENLABS_API_KEY found in .env file")
        return

    # Test text
    test_text = "Hello, this is a test of the audio system to check for choppy playback."
    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    # Initialize client
    try:
        client = ElevenLabsTTSClient(api_key=api_key)
        print("✅ ElevenLabs client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return

    # Test configurations
    configs = [
        {
            "name": "Original (likely choppy)",
            "player": StreamingAudioPlayer(chunk_size=4096),
            "decoder": lambda chunks: mp3_chunks_to_pcm(chunks, min_buffer_size=4096)
        },
        {
            "name": "Improved Original",
            "player": StreamingAudioPlayer(chunk_size=8192),
            "decoder": lambda chunks: mp3_chunks_to_pcm(chunks, min_buffer_size=16384)
        },
        {
            "name": "Buffered Player (recommended)",
            "player": BufferedAudioPlayer(chunk_size=16384),
            "decoder": lambda chunks: mp3_chunks_to_pcm_buffered(chunks, buffer_duration_ms=500)
        },
        {
            "name": "Simple Player (conservative)",
            "player": SimpleAudioPlayer(),
            "decoder": lambda chunks: mp3_chunks_to_pcm(chunks, min_buffer_size=16384)
        }
    ]

    for i, config in enumerate(configs, 1):
        print(f"\n{i}. Testing {config['name']}")
        print("-" * 40)

        try:
            # Generate audio
            print("Generating audio...")
            audio_chunks = client.stream(test_text, voice_id)

            # Decode to PCM
            print("Decoding MP3 to PCM...")
            start_time = time.time()
            pcm_chunks = list(config["decoder"](audio_chunks))
            decode_time = time.time() - start_time

            total_pcm = sum(len(chunk) for chunk in pcm_chunks)
            print(f"Decoded {len(pcm_chunks)} chunks ({total_pcm} bytes) in {decode_time:.3f}s")

            # Play audio
            print("Playing audio...")
            start_time = time.time()
            config["player"].play(pcm_chunks)
            play_time = time.time() - start_time

            print(f"✅ {config['name']}: Completed in {play_time:.3f}s")

        except Exception as e:
            print(f"❌ {config['name']}: Failed - {e}")

        if i < len(configs):
            input("\nPress Enter to test next configuration (or Ctrl+C to exit)...")

    print("\n🏁 Quick test complete!")
    print("\nIf you found a configuration that works well:")
    print("1. Edit Entourage/main_app.py")
    print("2. In _initialize_tts_manager(), change player_type to:")
    print("   - 'buffered' for BufferedAudioPlayer")
    print("   - 'simple' for SimpleAudioPlayer")
    print("   - 'original' for StreamingAudioPlayer")

def benchmark_test():
    """Run performance benchmark without playing audio."""
    print("🏃 Audio Performance Benchmark")
    print("=" * 40)

    env_vars = dotenv_values('.env')
    api_key = env_vars.get('ELEVENLABS_API_KEY')

    if not api_key:
        print("❌ No ELEVENLABS_API_KEY found")
        return

    try:
        client = ElevenLabsTTSClient(api_key=api_key)
        test_text = "This is a performance test of the audio decoding system."
        voice_id = "21m00Tcm4TlvDq8ikWAM"

        # Test different buffer sizes
        buffer_sizes = [4096, 8192, 16384, 32768]

        print("Testing MP3 decoding performance:")
        for buffer_size in buffer_sizes:
            audio_chunks = client.stream(test_text, voice_id)

            start_time = time.time()
            pcm_chunks = list(mp3_chunks_to_pcm(audio_chunks, min_buffer_size=buffer_size))
            decode_time = time.time() - start_time

            total_bytes = sum(len(chunk) for chunk in pcm_chunks)
            print(f"  Buffer {buffer_size:5d}: {len(pcm_chunks):2d} chunks, {decode_time:.3f}s")

        # Test buffered decoder
        audio_chunks = client.stream(test_text, voice_id)
        start_time = time.time()
        pcm_chunks = list(mp3_chunks_to_pcm_buffered(audio_chunks))
        decode_time = time.time() - start_time
        print(f"  Buffered   : {len(pcm_chunks):2d} chunks, {decode_time:.3f}s")

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        benchmark_test()
    else:
        quick_test()
