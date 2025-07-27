# Entourage Program Flow Documentation

## Overview
Entourage is a cross-platform, voice-enabled chat client for OpenAI's GPT4.1-mini model. It provides a GUI interface built with Kivy that allows users to interact with an AI assistant through text input or voice commands. The application supports session management, persistent conversation memory, and voice input/output using OpenAI Whisper and Amazon Polly.

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

### 2. Application Logic (base.py)
- **Main Class**: `EntourageApp`
- **Description**: The main Kivy application class that handles user interactions and coordinates between components

#### Key Methods:
- `build()`: Initializes the application components
- `submit()`: Handles text input submission with streaming support
- `voicemode_toggle()`: Toggles voice input mode
- `gather_vocal_audio_for_transcription()`: Records and transcribes voice input
- `evaluate_thread()`: Processes user prompts with the AI using streaming
- `process_streaming_response()`: Handles streaming response chunks from OpenAI
- `on_streaming_complete()`: Handles completion of streaming response
- `say_summary()`: Summarizes long responses for voice output

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

### 4. Audio Processing (autrasyn.py)
- **Classes**: `PollyInterface` and `AudioInterface`
- **Description**: Handles voice input recording, transcription, and voice output synthesis

#### Key Methods:
- `PollyInterface.say()`: Converts text to speech using Amazon Polly
- `PollyInterface.say_streaming()`: Handles streaming text for voice output
- `AudioInterface.start_record_audio()`: Records audio from microphone
- `AudioInterface.transcribe_audio()`: Transcribes recorded audio using OpenAI Whisper

## Program Flow

### 1. Application Startup
1. `EntourageApp.build()` initializes:
   - AICommunicator with memory persistence
   - Popup for processing indicator
   - PollyInterface for text-to-speech
   - AudioInterface for voice input
2. Configuration is loaded from `configuration.json`
3. Session data is loaded from `session_tracker.json`
4. GUI is displayed with initial "waiting for input..." message

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
   - If response is long (>200 words), calls `say_summary()`
   - Otherwise, calls `PollyInterface.say()` to speak response

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
   - Automatically calls `submit()` to process transcribed prompt

### 4. Voice Output
1. After receiving AI response, `on_streaming_complete()` determines output method:
   - For responses >200 words: calls `say_summary()` to summarize before speaking
   - For shorter responses: calls `PollyInterface.say()` directly
2. `PollyInterface.say()`:
   - Refreshes configuration
   - Calls Amazon Polly API to synthesize speech
   - Saves audio stream to temporary MP3 file
   - Plays audio using pydub
   - Deletes temporary file

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

### configuration.json
- Contains system prompt for AI behavior
- Specifies default voice persona for Amazon Polly

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
- OpenAI: GPT-3.5-turbo for chat completions and Whisper for voice transcription
- Boto3: Amazon Polly integration for text-to-speech
- PyAudio: Audio recording
- Pydub: Audio processing and playback
