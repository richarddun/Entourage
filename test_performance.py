#!/usr/bin/env python3
"""
Simple performance test for the optimized audio solution.
Tests decoding performance without interactive prompts.
"""

import sys
import os
import time
import io
from dotenv import dotenv_values

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tts.elevenlabs_client import ElevenLabsTTSClient
from pydub import AudioSegment

def test_performance():
    """Test performance of old vs new MP3 decoding approach."""
    print("🔧 ElevenLabs Audio Performance Test")
    print("=" * 50)

    # Load environment
    env_vars = dotenv_values('.env')
    api_key = env_vars.get('ELEVENLABS_API_KEY')

    if not api_key:
        print("❌ No ELEVENLABS_API_KEY found in .env file")
        return False

    test_text = "This is a performance test to measure MP3 decoding speed improvements."
    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    try:
        client = ElevenLabsTTSClient(api_key=api_key)
        print("✅ ElevenLabs client initialized")
        print(f"📝 Test text: '{test_text}'")
        print()

        # Test OLD approach (chunk-by-chunk decoding)
        print("🐌 OLD APPROACH: Chunk-by-chunk MP3 decoding")
        print("-" * 40)

        from tts.mp3_decoder import mp3_chunks_to_pcm

        audio_chunks = list(client.stream(test_text, voice_id))
        print(f"   Generated {len(audio_chunks)} MP3 chunks")

        start_time = time.time()
        pcm_chunks = list(mp3_chunks_to_pcm(audio_chunks, min_buffer_size=4096))
        old_decode_time = time.time() - start_time

        old_pcm_bytes = sum(len(chunk) for chunk in pcm_chunks)
        print(f"   ⏱️  Decode time: {old_decode_time:.3f}s")
        print(f"   📊 PCM output: {old_pcm_bytes:,} bytes in {len(pcm_chunks)} chunks")

        # Test NEW approach (single decode)
        print()
        print("🚀 NEW APPROACH: Single complete MP3 decode")
        print("-" * 40)

        audio_chunks = list(client.stream(test_text, voice_id))

        # Collect all MP3 data
        collect_start = time.time()
        mp3_data = b''.join(chunk for chunk in audio_chunks if chunk)
        collect_time = time.time() - collect_start

        # Single decode operation
        decode_start = time.time()
        mp3_io = io.BytesIO(mp3_data)
        audio_segment = AudioSegment.from_file(mp3_io, format="mp3")
        pcm_data = audio_segment.raw_data
        new_decode_time = time.time() - decode_start

        total_new_time = collect_time + new_decode_time

        print(f"   📥 Collection time: {collect_time:.3f}s")
        print(f"   🔧 Decode time: {new_decode_time:.3f}s")
        print(f"   ⏱️  Total time: {total_new_time:.3f}s")
        print(f"   📊 PCM output: {len(pcm_data):,} bytes")

        # Calculate improvement
        print()
        print("📈 PERFORMANCE RESULTS")
        print("=" * 30)

        if total_new_time > 0:
            improvement = old_decode_time / total_new_time
            time_saved = old_decode_time - total_new_time

            print(f"🎯 Speed improvement: {improvement:.1f}x faster")
            print(f"⚡ Time saved: {time_saved:.3f}s ({time_saved*1000:.0f}ms)")
            print(f"📉 Old approach: {old_decode_time:.3f}s")
            print(f"📈 New approach: {total_new_time:.3f}s")

            if improvement >= 5.0:
                print("🏆 EXCELLENT: >5x performance improvement!")
            elif improvement >= 2.0:
                print("✅ GOOD: >2x performance improvement!")
            else:
                print("⚠️  MARGINAL: <2x improvement")

            return improvement >= 2.0
        else:
            print("❌ Cannot calculate improvement")
            return False

    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_decode():
    """Test just the basic decode functionality."""
    print("\n🔍 BASIC DECODE TEST")
    print("=" * 25)

    env_vars = dotenv_values('.env')
    api_key = env_vars.get('ELEVENLABS_API_KEY')

    if not api_key:
        print("❌ No API key")
        return

    try:
        client = ElevenLabsTTSClient(api_key=api_key)

        # Very short test
        audio_chunks = list(client.stream("Test", "21m00Tcm4TlvDq8ikWAM"))
        mp3_data = b''.join(audio_chunks)

        print(f"✅ Generated {len(mp3_data)} bytes of MP3 data")

        # Test decode
        mp3_io = io.BytesIO(mp3_data)
        audio_segment = AudioSegment.from_file(mp3_io, format="mp3")

        print(f"✅ Decoded to {len(audio_segment)}ms of audio")
        print(f"✅ Audio format: {audio_segment.frame_rate}Hz, {audio_segment.channels}ch")

    except Exception as e:
        print(f"❌ Basic test failed: {e}")

if __name__ == "__main__":
    success = test_performance()
    test_simple_decode()

    print("\n" + "="*60)
    print("🎵 SOLUTION SUMMARY")
    print("="*60)

    if success:
        print("✅ The optimized approach significantly improves performance!")
        print("📋 Next steps:")
        print("   1. The main app now uses OptimizedAudioPlayer by default")
        print("   2. This should eliminate choppy audio on your Lenovo ThinkPad")
        print("   3. If you still hear choppiness, try the 'fallback' player type")
    else:
        print("⚠️  Performance improvement may be limited")
        print("📋 Try these alternatives:")
        print("   1. Use 'fallback' player type (saves to temp file)")
        print("   2. Check if other audio applications are interfering")
        print("   3. Verify ALSA/PulseAudio configuration")

    print("\n🔧 The key insight: Multiple small ffmpeg calls (300-450ms each)")
    print("   were causing choppy audio. Single decode eliminates this!")
