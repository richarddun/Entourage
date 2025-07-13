# Entourage

A cross-platform, voice-enabled chat client for OpenAI's GPT-3.5-turbo.

<p align="center">
  <img src="gpt-client.png" alt="Entourage Screenshot" width="600"/>
</p>

## Table of Contents

- [About](#about)
- [Features](#features)
- [Demo](#demo)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Acknowledgements](#acknowledgements)

## About

**Entourage** is a cross-platform, voice-enabled desktop (and mobile-ready) chat client for OpenAI's GPT-3.5-turbo.
With integrated voice input (via OpenAI Whisper) and voice output (via Amazon Polly), session management, automatic summarization, and persistent conversation memory, Entourage brings a conversational AI assistant experience to your desktop or mobile device.

> **⚠️ Note:** This application uses the OpenAI and AWS APIs, which may incur usage charges under your accounts.

## Features

- **Chat with GPT-3.5-turbo**: Natural language conversation powered by OpenAI.
- **Voice Input**: Speak your prompts using OpenAI Whisper for transcription.
- **Voice Output**: Listen to AI responses via Amazon Polly (neural voices).
- **Session Management**: Create and switch between multiple chat sessions.
- **Conversation Memory**: Optional context memory to continue conversations across sessions.
- **Summarization**: Automatically summarize long responses for natural speech.
- **Configuration**: Customize the assistant's system prompt and voice persona.
- **Cross-Platform**: Built with [Kivy](https://kivy.org), targeting Linux, macOS, Windows, iOS, and Android.
- **Persistent Logs**: Export chat logs and session context for later review.

## Demo

![Entourage Chat Demo](gpt-client.png)

## Prerequisites

- **Python**: Version 3.7 or higher.
- **OpenAI API key**: Set the `OPENAI_API_KEY` environment variable.
- **AWS credentials**: Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (with Amazon Polly access).
- **PortAudio** development libraries (for PyAudio).
- **FFmpeg** (for audio conversion with pydub).

### System Dependencies

**Ubuntu / Debian**:

```bash
sudo apt update
sudo apt install ffmpeg libportaudio2 libportaudiocpp0 portaudio19-dev
```

**macOS (Homebrew)**:

```bash
brew install ffmpeg portaudio
```

**Windows**:

> - Install FFmpeg from https://ffmpeg.org/
> - Install PortAudio development files (e.g., via vcpkg or manual download).

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/richarddun/gpt-client.git
   cd gpt-client
   ```

2. (Optional) Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install Python dependencies:

   ```bash
   pip install openai boto3 kivy pydub pyaudio
   ```

## Configuration

Configure `configuration.json` to tune the assistant:

```json
{
  "system_prompt": "You are a witty and keen conversationalist.   You try to keep your responses as short as possible but always try to be friendly and humorous. You regularly ask questions and make sure to respond with a clear and concise answer. You are a good listener and a good communicator.",
  "voice_id": "Emma"
}
```

Set environment variables:

```bash
export OPENAI_API_KEY=your_openai_api_key
export AWS_ACCESS_KEY_ID=your_aws_access_key
export AWS_SECRET_ACCESS_KEY=your_aws_secret_key
```

## Usage

Launch Entourage:

```bash
python base.py
```

Or via the Kivy launcher:

```bash
kivy base.py
```

- **Submit**: Type your prompt in the input box and click **Submit**.
- **Push to Talk**: Click and hold **Push to Talk**, speak your prompt, and release.
- **Settings**: Open **Settings** to switch sessions or select a voice persona.

Conversation data is saved to:

- `session_tracker.json` (active sessions)
- `all_chat_context.json` (persistent chat memory)
- `chat_log.txt` (exported logs)

## Contributing

Contributions, issues, and feature requests are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a pull request.

## Troubleshooting

- **PyAudio installation errors**: Ensure PortAudio headers and libraries are installed.
- **FFmpeg errors**: Verify FFmpeg is installed and accessible in your `PATH`.
- **AWS / Polly errors**: Confirm AWS credentials and permissions.
- **OpenAI API errors**: Check that `OPENAI_API_KEY` is set correctly.

## Roadmap

- Support streaming responses from OpenAI.
- Improve voice transcription accuracy and multi-language support.
- Mobile packaging for Android and iOS.
- Plugin architecture for extended capabilities.

## Acknowledgements

- [OpenAI](https://openai.com/) for GPT and Whisper APIs.
- [Amazon Polly](https://aws.amazon.com/polly/) for neural text-to-speech.
- [Kivy](https://kivy.org/) for the cross-platform UI framework.
