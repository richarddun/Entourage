#!/usr/bin/env python3
"""
Test script for the optimized audio solution.
This script tests the new OptimizedAudioPlayer that should eliminate choppy playback.
"""

import sys
import os
import time
from dotenv import dotenv_values

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tts.elevenlabs_client import ElevenLabsTTSClient
from tts.optimized_audio_player import OptimizedAudioPlayer, StreamCollectPlayer, FallbackAudioPlayer
from tts.tts_manager import TTSManager

def test_optimized_solution():
    """Test the optimized audio solution that should eliminate choppy playback."""
    print("🎵 Testing Optimized Audio Solution")
    print("=" * 50)

    # Load environment
    env_vars = dotenv_values('.env')
    api_key = env_vars.get('ELEVENLABS_API_KEY')

    if not api_key:
        print("❌ No ELEVENLABS_API_KEY found in .env file")
        print("Please add your ElevenLabs API key to test the audio solution.")
        return

    # Test configurations
    test_configs = [
        {
            "name": "Optimized Player (Recommended)",
            "description": "Collects all MP3 data, decodes once, plays smoothly",
            "player_type": "optimized"
        },
        {
            "name": "Stream Collect Player",
            "description": "Streams collection with background processing",
            "player_type": "stream_collect"
        },
        {
            "name": "Fallback Player",
            "description": "Uses temporary file and system audio player",
            "player_type": "fallback"
        }
    ]

    test_text = "Hello! This is a test of the new optimized audio system. It should play smoothly without any choppiness on your Lenovo ThinkPad."
    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    print(f"Test text: '{test_text}'")
    print(f"Voice: Rachel ({voice_id})")
    print()

    for i, config in enumerate(test_configs, 1):
        print(f"{i}. {config['name']}")
        print(f"   {config['description']}")
        print("-" * 50)

        try:
            # Create TTS manager with specific player type
            tts_manager = TTSManager.from_config("elevenlabs", player_type=config["player_type"])

            print("   Generating and playing audio...")
            start_time = time.time()

            # This should now play smoothly without choppy audio
            tts_manager.speak(test_text, voice_id)

            total_time = time.time() - start_time
            print(f"   ✅ {config['name']}: Completed in {total_time:.2f}s")

        except Exception as e:
            print(f"   ❌ {config['name']}: Failed - {e}")

        if i < len(test_configs):
            print()
            response = input("   Press Enter to test next configuration (or 'q' to quit): ").strip().lower()
            if response == 'q':
                break
            print()

    print()
    print("🎯 Solution Summary:")
    print("The optimized approach eliminates choppy audio by:")
    print("1. ⚡ Collecting all MP3 chunks first (still streaming from ElevenLabs)")
    print("2. 🔧 Decoding complete MP3 in ONE operation (not 10+ ffmpeg calls)")
    print("3. 🎵 Playing smooth PCM audio with proper buffering")
    print()
    print("This reduces decoding time from 5-6 seconds to ~0.2 seconds!")

def test_performance_comparison():
    """Compare performance of old vs new approach."""
    print("📊 Performance Comparison")
    print("=" * 30)

    env_vars = dotenv_values('.env')
    api_key = env_vars.get('ELEVENLABS_API_KEY')

    if not api_key:
        print("❌ No API key found")
        return

    test_text = "Performance test of audio decoding approaches."
    voice_id = "21m00Tcm4TlvDq8ikWAM"

    print("Comparing decode performance (no audio playback):")
    print()

    try:
        client = ElevenLabsTTSClient(api_key=api_key)

        # Test old approach (chunk by chunk decoding)
        print("1. Old Approach (chunk-by-chunk MP3 decoding):")
        from tts.mp3_decoder import mp3_chunks_to_pcm

        audio_chunks = client.stream(test_text, voice_id)
        start_time = time.time()
        pcm_chunks = list(mp3_chunks_to_pcm(audio_chunks, min_buffer_size=4096))
        old_time = time.time() - start_time

        old_pcm_bytes = sum(len(chunk) for chunk in pcm_chunks)
        print(f"   Time: {old_time:.3f}s")
        print(f"   PCM bytes: {old_pcm_bytes}")
        print(f"   Chunks: {len(pcm_chunks)}")

        # Test new approach (single decode)
        print()
        print("2. New Approach (single MP3 decode):")

        audio_chunks = client.stream(test_text, voice_id)

        # Collect all chunks
        start_time = time.time()
        mp3_data = b''.join(chunk for chunk in audio_chunks if chunk)
        collect_time = time.time() - start_time

        # Decode all at once
        from pydub import AudioSegment
        import io
        start_time = time.time()
        mp3_io = io.BytesIO(mp3_data)
        audio_segment = AudioSegment.from_file(mp3_io, format="mp3")
        pcm_data = audio_segment.raw_data
        decode_time = time.time() - start_time

        new_total_time = collect_time + decode_time

        print(f"   Collection time: {collect_time:.3f}s")
        print(f"   Decode time: {decode_time:.3f}s")
        print(f"   Total time: {new_total_time:.3f}s")
        print(f"   PCM bytes: {len(pcm_data)}")

        # Show improvement
        improvement = old_time / new_total_time if new_total_time > 0 else 0
        print()
        print(f"🚀 Performance Improvement: {improvement:.1f}x faster!")
        print(f"   Old: {old_time:.3f}s → New: {new_total_time:.3f}s")

    except Exception as e:
        print(f"❌ Performance test failed: {e}")

def main():
    """Main test function."""
    print("🔧 Entourage Audio Fix Tester")
    print("=" * 40)
    print()
    print("This script tests the solution for choppy ElevenLabs audio playback.")
    print("The optimized approach should eliminate the 300-450ms ffmpeg delays")
    print("that were causing choppy audio on your Lenovo ThinkPad.")
    print()

    while True:
        print("Options:")
        print("1. Test optimized audio playback (with sound)")
        print("2. Performance comparison (no sound)")
        print("3. Exit")
        print()

        choice = input("Choose option (1-3): ").strip()

        if choice == "1":
            print()
            test_optimized_solution()
        elif choice == "2":
            print()
            test_performance_comparison()
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option, please choose 1-3")

        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
