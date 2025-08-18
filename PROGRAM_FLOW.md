# Entourage Program Flow Documentation

## Overview
Entourage is a cross-platform, voice-enabled chat client for OpenAI's GPT4.1-mini model. It provides a GUI interface built with Kivy that allows users to interact with an AI assistant through text input or voice commands. The application supports session management, persistent conversation memory, and voice input/output using OpenAI Whisper with intelligent TTS selection (ElevenLabs primary, Amazon Polly fallback). Voice output is only activated when using speech recognition to maintain a clean user experience.

## Main Components

### 1. UI Layer (Kivy)
- **File**: `Entourage.kv`
- **Description**: Defines the GUI layout using Kivy's kv language
- **Key Elements**:
  - Output text area (`outputwidget`) for displaying AI responses
  - Input text area (`inputwidget`) for user text input
  - Submit button to send text prompts
  - Push to Talk button for voice input
  - Settings button to open configuration popup
  - Configuration popup with session management and voice selection

### 2. Application Logic (main_app.py)
- **Main Class**: `EntourageApp`
- **Description**: The main Kivy application class that handles user interactions and coordinates between components

#### Key Methods:
- `build()`: Initializes the application components including intelligent TTS system
- `submit()`: Handles text input submission with streaming support
- `voicemode_toggle()`: Toggles voice input mode and sets voice tracking flag
- `gather_vocal_audio_for_transcription()`: Records and transcribes voice input
- `evaluate_thread()`: Processes user prompts with the AI using streaming
- `process_streaming_response()`: Handles streaming response chunks from OpenAI
- `on_streaming_complete()`: Handles completion of streaming response with conditional TTS
- `_initialize_tts_manager()`: Initializes TTS with ElevenLabs first, Polly fallback
- `_speak_with_fallback()`: Intelligent TTS with automatic provider fallback

### 3. AI Communication (oaiops.py)
- **Main Class**: `AICommunicator`
- **Description**: Handles communication with OpenAI's API for chat completions and voice transcription

#### Key Methods:
- `evaluate()`: Sends user prompts to OpenAI and returns streaming responses
- `voice_summarize()`: Summarizes long responses for better voice output
- `reset_prompt_history()`: Resets or loads conversation history
- `save_context()` and `export_chat_log()`: Persist conversation data
- `confirm_active_session()`: Manages session switching
- `load_json_configuration()`: Loads system prompt configuration

### 4. Audio Processing (autrasyn.py & tts/)
- **Classes**: `PollyInterface`, `AudioInterface`, and `TTSManager`
- **Description**: Handles voice input recording, transcription, and intelligent voice output synthesis

#### Key Methods:
- `PollyInterface.say()`: Legacy Polly TTS (used as final fallback)
- `PollyInterface.say_streaming()`: Handles streaming text for voice output
- `AudioInterface.start_record_audio()`: Records audio from microphone
- `AudioInterface.transcribe_audio()`: Transcribes recorded audio using OpenAI Whisper
- `TTSManager.speak()`: Primary TTS interface with provider abstraction
- `TTSManager.from_config()`: Factory method for TTS provider initialization

### 5. Environment Configuration
- **Files**: `.env`, `configuration.json`, `session_tracker.json`
- **Description**: All API credentials now exclusively sourced from `.env` file, ignoring system environment variables

#### Key Variables (.env):
- `OPENAI_API_KEY`: OpenAI API access for GPT and Whisper
- `ELEVENLABS_API_KEY`: ElevenLabs TTS API access (primary TTS)
- `AWS_ACCESS_KEY_ID`: AWS credentials for Polly fallback
- `AWS_SECRET_ACCESS_KEY`: AWS credentials for Polly fallback

## Program Flow

### 1. Application Startup
1. `EntourageApp.build()` initializes:
   - AICommunicator with memory persistence (loads from `.env` only)
   - Popup for processing indicator
   - Intelligent TTS system (ElevenLabs → Polly → PollyInterface fallback chain)
   - AudioInterface for voice input
   - Voice input tracking flag (`voice_input_used = False`)
2. Environment variables loaded exclusively from `.env` file
3. Configuration is loaded from `configuration.json`
4. Session data is loaded from `session_tracker.json`
5. GUI is displayed with initial "waiting for input..." message

### 2. Text Input Flow (with Streaming)
1. User types prompt in `inputwidget`
2. User clicks "Submit" button or presses Enter
3. `submit()` method:
   - Stops any existing worker thread
   - Clears output widget
   - Gets text from input widget
   - Starts StreamingWorkerThread with `evaluate_thread()` target
   - Opens processing popup
4. `evaluate_thread()`:
   - Confirms active session
   - Calls `AICommunicator.evaluate()` with prompt
   - Passes streaming response to `process_streaming_response()`
5. `AICommunicator.evaluate()`:
   - Adds user prompt to conversation history
   - Sends request to OpenAI GPT-3.5-turbo with streaming enabled
   - Returns streaming response iterator
6. `process_streaming_response()`:
   - Iterates through streaming response chunks
   - Updates output widget in real-time with each chunk
   - Accumulates full response for history
   - Calls `on_streaming_complete()` when finished
7. `on_streaming_complete()`:
   - Adds complete response to conversation history
   - Closes processing popup
   - **NEW**: Only triggers TTS if `voice_input_used = True`
   - **Text input remains silent** (no TTS output)
   - **Voice input gets TTS**: Uses intelligent fallback system
   - Resets `voice_input_used` flag for next interaction

### 3. Voice Input Flow
1. User clicks and holds "Push to Talk" button
2. `voicemode_toggle()`:
   - Toggles listening state
   - Updates button appearance
   - Starts WorkerThread with `gather_vocal_audio_for_transcription()` target
3. `gather_vocal_audio_for_transcription()`:
   - If listening, calls `AudioInterface.start_record_audio()`
   - Records audio until button is released
   - Calls `AudioInterface.transcribe_audio()` to transcribe recording
   - Updates input widget with transcribed text
   - **Sets `voice_input_used = True`** to enable TTS output
   - Automatically calls `submit()` to process transcribed prompt

### 4. Voice Output (Intelligent TTS System)
1. **Voice Input Only**: TTS only activates when `voice_input_used = True`
2. **Text Input**: Completely silent (no TTS output)
3. **TTS Provider Chain**: ElevenLabs → Polly TTS Manager → PollyInterface → Graceful failure
4. `_speak_with_fallback()` process:
   - Auto-summarizes responses >200 words using `voice_summarize()`
   - Attempts ElevenLabs TTS first (streaming, high quality)
   - Falls back to Polly TTS Manager on ElevenLabs failure
   - Final fallback to original PollyInterface
   - Graceful degradation with error logging
5. **Authentication Handling**:
   - Tests providers on initialization with minimal API calls
   - Automatic fallback on credential/API errors
   - User experience remains uninterrupted during provider failures

### 5. Session Management
1. Configuration popup allows creating/deleting sessions
2. `ConfigurationPopup`:
   - Loads sessions from `session_tracker.json`
   - Displays toggle buttons for each session
   - Allows selecting active session
   - Saves session changes to file
3. `AICommunicator.confirm_active_session()`:
   - Reads active session from `session_tracker.json`
   - Loads appropriate conversation history for active session

### 6. Data Persistence
1. Conversation context saved to `all_chat_context.json`:
   - Performed by `AICommunicator.save_context()`
   - Called when application stops or sessions change
2. Chat logs exported to `chat_log.txt`:
   - Performed by `AICommunicator.export_chat_log()`
   - Called when application stops
3. Session tracking in `session_tracker.json`:
   - Managed by `ConfigurationPopup` class
   - Tracks active sessions and metadata

## Configuration Files

### .env
- **NEW**: Primary configuration for API credentials
- All environment variables loaded exclusively from this file
- Contains: `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- System environment variables are completely ignored

### configuration.json
- Contains system prompt for AI behavior
- Specifies voice ID preference for TTS systems
- Voice mapping handled automatically between providers

### session_tracker.json
- Tracks active chat sessions
- Maintains session metadata (currently active flag)

### all_chat_context.json
- Stores conversation history for all sessions
- Enables persistent memory across application restarts

### chat_log.txt
- Exported conversation logs
- Includes timestamps and session identifiers

## Dependencies
- Kivy: GUI framework
- OpenAI: GPT-4.1-mini for chat completions and Whisper for voice transcription
- ElevenLabs: Primary high-quality TTS provider (streaming)
- Boto3: Amazon Polly integration for TTS fallback
- python-dotenv: `.env` file loading (replaces system environment variables)
- PyAudio: Audio recording
- Pydub: Audio processing and playback

## Key Improvements
### Environment Security
- **Isolated Configuration**: `.env` file completely replaces system environment variables
- **No Environment Pollution**: `dotenv_values()` instead of `load_dotenv()`
- **Reduced Conflicts**: System-wide environment variables no longer interfere

### Intelligent TTS System
- **Context-Aware**: TTS only for voice interactions, silent text mode
- **High-Quality Primary**: ElevenLabs streaming TTS for best user experience
- **Robust Fallbacks**: Automatic provider switching on failures
- **Graceful Degradation**: System continues functioning even with API issues
- **Efficient**: Minimal API testing, smart error handling
