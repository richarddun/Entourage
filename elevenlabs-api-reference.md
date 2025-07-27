---
title: Introduction
subtitle: Welcome to the ElevenLabs API reference.
hide-feedback: true
---

## Installation

You can interact with the API through HTTP or Websocket requests from any language, via our official Python bindings or our official Node.js libraries.

To install the official Python bindings, run the following command:

```bash
pip install elevenlabs
```

To install the official Node.js library, run the following command in your Node.js project directory:

```bash
npm install @elevenlabs/elevenlabs-js
```

<div id="overview-wave">
  <ElevenLabsWaveform color="gray" className="h-[500px]" />
</div>

Text to Speech API Overview

The ElevenLabs Text to Speech API converts text into lifelike audio with nuanced intonation, pacing, and emotional awareness
. The API supports 32 languages and offers multiple voice styles for various applications

.
API Endpoint Types

There are three types of text-to-speech endpoints available

:

    Regular endpoint: Returns a complete audio file in a single response
    Streaming endpoint: Returns audio chunks progressively using Server-sent events
    WebSockets endpoint: Enables bidirectional streaming for real-time audio generation

Non-Streaming Usage

For non-streaming requests, you receive the complete audio file at once. Here's how to use it:

Python:

from elevenlabs.client import ElevenLabs

elevenlabs = ElevenLabs()

response = elevenlabs.text_to_speech.convert(

    voice_id="pNInz6obpgDQGcFmaJgB",

    output_format="mp3_22050_32",

    text="Hello World",

    model_id="eleven_turbo_v2_5"

)

Node.js:

const audio = await elevenlabs.textToSpeech.convert('JBFqnCBsd6RMkjVDRZzb', {

    text: 'Hello World',

    modelId: 'eleven_multilingual_v2',

    outputFormat: 'mp3_44100_128'

});

Streaming Usage

Streaming returns raw audio bytes directly over HTTP using chunked transfer encoding, allowing clients to process or play audio incrementally as it's generated

.

Python streaming:

from elevenlabs import stream

from elevenlabs.client import ElevenLabs

elevenlabs = ElevenLabs()

audio_stream = elevenlabs.text_to_speech.stream(

    text="This is a test",

    voice_id="JBFqnCBsd6RMkjVDRZzb",

    model_id="eleven_multilingual_v2"

)

# Option 1: Play streamed audio locally

stream(audio_stream)

# Option 2: Process audio bytes manually

for chunk in audio_stream:

    if isinstance(chunk, bytes):

        print(chunk)

Node.js streaming:

import { ElevenLabsClient, stream } from '@elevenlabs/elevenlabs-js';

const elevenlabs = new ElevenLabsClient();

const audioStream = await elevenlabs.textToSpeech.stream('JBFqnCBsd6RMkjVDRZzb', {

    text: 'This is a test',

    modelId: 'eleven_multilingual_v2'

});

// Option 1: Play streamed audio locally

await stream(Readable.from(audioStream));

// Option 2: Process audio manually

for await (const chunk of audioStream) {

    console.log(chunk);

}

WebSocket Streaming

The WebSocket endpoint is ideal for real-time applications where text is being generated incrementally (like LLM outputs)

. It supports bidirectional streaming and includes automatic buffering management:

    Setting auto_mode to true automatically handles generation triggers
    Without auto_mode, the model waits for enough text to match the chunk schedule before starting generation
    If you set a chunk schedule of 125 characters but only 50 arrive, the model stalls until additional characters come in

Buffering Considerations
Streaming Benefits

    Reduced time-to-first-byte: Audio starts playing as it's generated
    Lower perceived latency: Users hear audio immediately rather than waiting for complete generation
    Memory efficiency: Process audio chunks incrementally instead of loading entire files

WebSocket Buffering

    The WebSocket API involves some buffering since generations are partial

    This could potentially result in slightly higher latency compared to standard HTTP requests
    Use auto_mode=true to optimize buffering automatically

Latency Optimization

For minimal latency:

    Use Flash models (~75ms inference speed)

    Leverage streaming endpoints for progressive audio delivery
    Consider geographic proximity to reduce network latency
    Choose appropriate voices (default voices are fastest)

When to Use Each Approach

Use regular endpoints when:

    The entire text is available upfront
    You need the complete audio file before processing
    Simple use cases where streaming complexity isn't needed

Use streaming when:

    You want to reduce time-to-first-byte
    Processing long text that benefits from progressive delivery
    Building real-time applications

Use WebSockets when:

    Text is being generated in chunks (e.g., LLM outputs)
    You need bidirectional communication
    Building conversational or interactive applications
    Word-to-audio alignment information is required

---

ElevenLabs API Reference from github

📖 API & Docs

Check out the HTTP API documentation.
Install

pip install elevenlabs

Usage
Main Models

    Eleven Multilingual v2 (eleven_multilingual_v2)
        Excels in stability, language diversity, and accent accuracy
        Supports 29 languages
        Recommended for most use cases

    Eleven Flash v2.5 (eleven_flash_v2_5)
        Ultra-low latency
        Supports 32 languages
        Faster model, 50% lower price per character

    Eleven Turbo v2.5 (eleven_turbo_v2_5)
        Good balance of quality and latency
        Ideal for developer use cases where speed is crucial
        Supports 32 languages

For more detailed information about these models and others, visit the ElevenLabs Models documentation.

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play

load_dotenv()

client = ElevenLabs()

audio = client.text_to_speech.convert(
    text="The first move is what sets everything in motion.",
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)

play(audio)

Play

Voices

List all your available voices with voices().

from elevenlabs.client import ElevenLabs

client = ElevenLabs(
  api_key="YOUR_API_KEY",
)

response = client.voices.search()
print(response.voices)

For information about the structure of the voices output, please refer to the official ElevenLabs API documentation for Get Voices.

Build a voice object with custom settings to personalize the voice style, or call client.voices.get_settings("your-voice-id") to get the default settings for the voice.
Clone Voice

Clone your voice in an instant. Note that voice cloning requires an API key, see below.

from elevenlabs.client import ElevenLabs
from elevenlabs import play

client = ElevenLabs(
  api_key="YOUR_API_KEY",
)

voice = client.voices.ivc.create(
    name="Alex",
    description="An old American male voice with a slight hoarseness in his throat. Perfect for news", # Optional
    files=["./sample_0.mp3", "./sample_1.mp3", "./sample_2.mp3"],
)

Streaming

Stream audio in real-time, as it's being generated.

from elevenlabs import stream
from elevenlabs.client import ElevenLabs

client = ElevenLabs()

audio_stream = client.text_to_speech.stream(
    text="This is a test",
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2"
)

# option 1: play the streamed audio locally
stream(audio_stream)

# option 2: process the audio bytes manually
for chunk in audio_stream:
    if isinstance(chunk, bytes):
        print(chunk)
