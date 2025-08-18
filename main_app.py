
#os.environ["KIVY_NO_ARGS"] = "1"
#os.environ["KIVY_NO_CONSOLELOG"] = "1"
from kivy.app import App
from kivy.factory import Factory
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.dropdown import DropDown
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.animation import Animation
from autrasyn import PollyInterface, AudioInterface
from oaiops import AICommunicator
import threading
import json
import queue

from tts.tts_manager import TTSManager




class WorkerThread(threading.Thread):
    def __init__(self, target, args=(), kwargs=None):
        super().__init__()
        self._target = target
        self._args = args
        self._kwargs = kwargs if kwargs is not None else {}
        self.stop_flag = threading.Event()

    def run(self):
        while not self.stop_flag.is_set():
            self._target(*self._args, **self._kwargs)  # Call the target function
            self.stop_flag.set()

    def stop(self):
        self.stop_flag.set()

class StreamingWorkerThread(threading.Thread):
    def __init__(self, target, args=(), kwargs=None):
        super().__init__()
        self._target = target
        self._args = args
        self._kwargs = kwargs if kwargs is not None else {}
        self.stop_flag = threading.Event()

    def run(self):
        self._target(*self._args, **self._kwargs)
        self.stop_flag.set()

    def stop(self):
        self.stop_flag.set()

class NoSelectTextInput(TextInput):
    """TextInput that doesn't select text on mouse movement"""
    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            # Don't call parent's on_touch_move to prevent text selection
            return True
        return super().on_touch_move(touch)

class ReadOnlyTextInput(TextInput):
    """Read-only TextInput that doesn't allow selection or cursor"""
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # Allow scrolling but prevent text selection
            return False
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            # Don't call parent's on_touch_move to prevent text selection
            return False
        return super().on_touch_move(touch)

class NoTrackToggleButton(ToggleButton):
    """ToggleButton that works well with trackpads and prevents unwanted selection"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._touch_started_here = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_started_here = True
            touch.grab(self)
            return super().on_touch_down(touch)
        return False

    def on_touch_move(self, touch):
        # Allow small movements (trackpad precision) but prevent large drags
        if touch.grab_current is self and self._touch_started_here:
            if hasattr(touch, 'ox') and hasattr(touch, 'oy'):
                # Calculate movement distance from original touch point
                dx = abs(touch.x - touch.ox)
                dy = abs(touch.y - touch.oy)
                # Allow small movements (trackpad finger adjustments)
                if dx < 20 and dy < 20:
                    return True
                # Large movements cancel the selection
                else:
                    touch.ungrab(self)
                    self._touch_started_here = False
                    return False
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self and self._touch_started_here:
            self._touch_started_here = False
            touch.ungrab(self)
            # Only trigger if touch ended on this button
            if self.collide_point(*touch.pos):
                return super().on_touch_up(touch)
        return False

class EntourageApp(App):

    def build(self):
        self.cleared = False
        self.oai = AICommunicator(memory=True)
        self.speaker = PollyInterface()
        self.tts_manager = self._initialize_tts_manager()
        self.audio = AudioInterface()
        self.listening = False
        self.response_queue = queue.Queue()
        self.streaming_active = False
        self.tts_worker = None  # Worker thread for TTS playback
        self.voice_input_used = False  # Track if current interaction used voice input
        self.submit_animation = None  # Track submit button animation
        self.original_submit_text = "Submit"  # Store original button text
        root = ChattorFlow()
        # Set initial welcome message or restore conversation
        Clock.schedule_once(lambda dt: self.initialize_conversation_display(root), 0.5)
        return root

    def load_kv(self, filename=None):
        # Load the improved KV file
        return super().load_kv(filename='Entourage.kv')

    def _initialize_tts_manager(self):
        """Initialize TTS manager with ElevenLabs first, Polly fallback"""
        # Try ElevenLabs first
        elevenlabs_manager = None
        try:
            elevenlabs_manager = TTSManager.from_config("elevenlabs")
            # Test ElevenLabs with a short phrase to verify credentials
            if self._test_tts_provider(elevenlabs_manager, "elevenlabs"):
                print("ElevenLabs TTS initialized and tested successfully")
                return elevenlabs_manager
            else:
                print("ElevenLabs TTS failed authentication test, falling back to Polly")
        except Exception as e:
            print(f"ElevenLabs TTS initialization failed: {e}, falling back to Polly")

        # Try Polly as fallback
        try:
            polly_manager = TTSManager.from_config("polly")
            if self._test_tts_provider(polly_manager, "polly"):
                print("Polly TTS initialized and tested successfully")
                return polly_manager
            else:
                print("Polly TTS failed authentication test, using original PollyInterface")
        except Exception as e:
            print(f"Polly TTS initialization failed: {e}, using original PollyInterface")

        return None

    def _test_tts_provider(self, tts_manager, provider_name):
        """Test TTS provider with a minimal request to verify credentials"""
        try:
            # Use a very short test phrase to minimize API usage
            test_text = "Test"
            voice_id = "Emma" if provider_name == "polly" else "21m00Tcm4TlvDq8ikWAM"  # Rachel's ElevenLabs ID

            # Try to get audio chunks but don't play them
            audio_chunks = tts_manager.tts_client.stream(test_text, voice_id)
            # Just check if we can get the first chunk without error
            next(audio_chunks)
            return True
        except Exception as e:
            print(f"{provider_name} test failed: {e}")
            return False

    def _speak_with_fallback(self, text, voice_id=None):
        """Speak text using available TTS with intelligent fallback"""
        # Determine actual text to synthesize (summarize if too long)
        actual_text = text
        if len(text.split(' ')) > 200:
            actual_text = self.oai.voice_summarize(text)

        # Get voice effects settings
        voice_effects = self._get_voice_effects()

        # Try current TTS manager first
        if self.tts_manager:
            try:
                # Pass voice effects to TTS manager
                if hasattr(self.tts_manager.tts_client, 'stream'):
                    # For ElevenLabs, use enhanced streaming with effects
                    self.tts_manager.speak(actual_text, voice_id or "Rachel", **voice_effects)
                else:
                    # Fallback for other TTS providers
                    self.tts_manager.speak(actual_text, voice_id or "Rachel")
                return
            except Exception as e:
                print(f"TTS failed with current provider: {e}")
                # Mark current TTS manager as failed
                self.tts_manager = None

        # Fallback to original PollyInterface as last resort
        print("Using original PollyInterface as fallback")
        try:
            self.speaker.say(actual_text)
        except Exception as e:
            print(f"Original PollyInterface also failed: {e}")
            print("All TTS systems have failed - audio output unavailable")

    def _get_voice_effects(self):
        """Get voice effects settings from UI sliders (if popup is open)"""
        try:
            # Try to find an open configuration popup
            for child in self.root.children:
                if hasattr(child, 'ids') and hasattr(child.ids, 'stability_slider'):
                    return {
                        'stability': child.ids.stability_slider.value,
                        'similarity_boost': 0.8,  # Fixed high quality
                        'style': child.ids.style_slider.value,
                        'use_speaker_boost': True,
                        'speed': child.ids.speed_slider.value if hasattr(child.ids, 'speed_slider') else 1.0
                    }
            # Default settings if no popup is open
            return {
                'stability': 0.5,
                'similarity_boost': 0.8,
                'style': 0.0,
                'use_speaker_boost': True,
                'speed': 1.0
            }
        except Exception as e:
            print(f"Error getting voice effects: {e}")
            return {'stability': 0.5, 'similarity_boost': 0.8, 'style': 0.0, 'use_speaker_boost': True}

    def _get_voice_id(self):
        """Get voice ID from session-specific settings"""
        try:
            # Directly read session file for reliability during startup
            with open('session_tracker.json', 'r') as f:
                sessions = json.load(f)
                # Get the active session
                active_session_key = self.oai.active_session_key if hasattr(self.oai, 'active_session_key') else None
                if not active_session_key:
                    # Find active session if not set
                    for session_name, session_data in sessions.items():
                        if session_data.get('currently_active'):
                            active_session_key = session_name
                            break

                if active_session_key and active_session_key in sessions:
                    voice_display_name = sessions[active_session_key].get('voice_id', 'Rachel')
                    return self._convert_display_name_to_voice_id(voice_display_name)

            return 'Rachel'  # Default if no active session found
        except Exception as e:
            print(f"Error getting voice_id: {e}")
            return 'Rachel'  # Default voice if any error

    def _convert_display_name_to_voice_id(self, display_name):
        """Convert display name from UI to actual ElevenLabs voice ID"""
        # Map display names to actual ElevenLabs voice IDs
        voice_mapping = {
            'Rachel (Default)': '21m00Tcm4TlvDq8ikWAM',  # Rachel
            'Rachel': '21m00Tcm4TlvDq8ikWAM',  # Rachel
            'Adam': '29vD33N1CtxCmqQRPOHJ',  # Drew (closest available)
            'Matilda': 'EXAVITQu4vr4xnSDxMaL',  # Sarah (closest available)
            'Ana': '9BWtsMINqrJLrRacOk9x',  # Aria (closest available)
            '🧙‍♂️ Old Wizard': '5Q0t7uMcjvnagumLfvZi',  # Paul (older male voice)
            '🤖 Android X.Y.Z.': 'CYw3kZ02Hs0563khs1Fj',  # Dave (robotic-sounding)
            '🧚‍♀️ Seer Morganna': 'EXAVITQu4vr4xnSDxMaL',  # Sarah (mystical female)
            '🎪 Timmy Medieval': 'D38z5RcWu1voky8WS1ja',  # Fin (young-sounding)
            '🐭 Michael Mouse': '2EiwWnXFnvU5JabPnv8n',  # Clyde (character voice)
            '👹 Evil Witch': 'AZnzlk1XvdvUeBnXmlld',  # Domi (darker voice)
            '🌟 Kawaii Aerisita': '9BWtsMINqrJLrRacOk9x',  # Aria (sweet voice)
            '😂 Lutz Laugh': 'CwhRBWXzGAHq8TQ4Fs17'  # Roger (cheerful voice)
        }
        return voice_mapping.get(display_name, '21m00Tcm4TlvDq8ikWAM')  # Default to Rachel

    def _get_character_display_name(self, voice_id):
        """Get character display name for conversation from voice ID"""
        # Map ElevenLabs voice IDs to character display names
        character_names = {
            '21m00Tcm4TlvDq8ikWAM': 'Rachel',  # Rachel
            '29vD33N1CtxCmqQRPOHJ': 'Adam',    # Drew (mapped to Adam)
            'EXAVITQu4vr4xnSDxMaL': 'Matilda', # Sarah (mapped to Matilda)
            '9BWtsMINqrJLrRacOk9x': 'Ana',     # Aria (mapped to Ana)
            '5Q0t7uMcjvnagumLfvZi': '🧙‍♂️ Wizard',    # Paul (Old Wizard)
            'CYw3kZ02Hs0563khs1Fj': '🤖 Android',     # Dave (Android)
            'D38z5RcWu1voky8WS1ja': '🎪 Timmy',       # Fin (Timmy)
            '2EiwWnXFnvU5JabPnv8n': '🐭 Mickey',      # Clyde (Michael Mouse)
            'AZnzlk1XvdvUeBnXmlld': '👹 Witch',       # Domi (Evil Witch)
            'CwhRBWXzGAHq8TQ4Fs17': '😂 Lutz'         # Roger (Lutz Laugh)
        }

        # For voices using Sarah ID, differentiate by context
        if voice_id == 'EXAVITQu4vr4xnSDxMaL':
            # Could be Matilda or Morganna - default to Matilda
            return character_names.get(voice_id, 'Matilda')
        elif voice_id == '9BWtsMINqrJLrRacOk9x':
            # Could be Ana or Aerisita - default to Ana
            return character_names.get(voice_id, 'Ana')

        return character_names.get(voice_id, 'Assistant')

    def on_stop(self):
        self.oai.export_chat_log()
        # Clean up animation if running
        if self.submit_animation:
            self.submit_animation.cancel(self.root.ids.submitter)
            self.submit_animation = None
        # Ensure TTS worker thread is stopped and cleaned up
        if self.tts_worker and self.tts_worker.is_alive():
            self.tts_worker.join()

    def evaluate_thread(self, prompt):
        self.oai.confirm_active_session()
        response = self.oai.evaluate(prompt)
        # Process streaming response
        self.process_streaming_response(response, prompt)

    def process_streaming_response(self, response, prompt):
        self.streaming_active = True
        first_chunk_received = False

        try:
            # Generator for text chunks from streaming response
            text_chunks = (chunk.choices[0].delta.content for chunk in response if chunk.choices[0].delta.content is not None)

            def update_ui(dt, text):
                # Create a temporary current exchange for display
                temp_history = self.oai.prompt_history[self.oai.active_session_key].copy()
                temp_history.append({"role": "assistant", "content": text})

                # Get formatted conversation with the temporary complete history
                conversation_parts = []
                current_exchange = {}

                for msg in temp_history:
                    role = msg.get('role', '')
                    content = msg.get('content', '').strip()

                    if not content:
                        continue

                    if role == 'user':
                        current_exchange = {'user': content}
                    elif role == 'assistant' and 'user' in current_exchange:
                        current_exchange['assistant'] = content
                        # Get character name for display - use stored voice_id from when message was created
                        # For historical messages, try to get voice from session data, fallback to current
                        try:
                            with open('session_tracker.json', 'r') as f:
                                sessions = json.load(f)
                                session_voice = sessions.get(self.oai.active_session_key, {}).get('voice_id', 'Rachel')
                            voice_id = self._convert_display_name_to_voice_id(session_voice)
                            character_name = self._get_character_display_name(voice_id)
                        except:
                            voice_id = self._get_voice_id()
                            character_name = self._get_character_display_name(voice_id)

                        conversation_parts.append(f"You: {current_exchange['user']}\n\n{character_name}: {current_exchange['assistant']}")
                        current_exchange = {}

                display_text = "\n\n".join(conversation_parts)
                self.root.ids.outputwidget.text = display_text
                # Auto-scroll to bottom
                Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.1)

            buffer = ""
            ui_text = ""

            # Stop any existing TTS worker
            if self.tts_worker and self.tts_worker.is_alive():
                self.tts_worker.join()

            # Process streaming response and update UI
            # TTS will be handled in on_streaming_complete if voice input was used
            for chunk in text_chunks:
                if not self.streaming_active:
                    break
                buffer += chunk
                ui_text = buffer
                Clock.schedule_once(lambda dt, text=ui_text: update_ui(dt, text), 0)

                # Stop spinner after first chunk
                if not first_chunk_received:
                    first_chunk_received = True
                    Clock.schedule_once(lambda dt: self.stop_submit_animation(), 0)

            # Add the complete response to history
            self.oai.prompt_history[self.oai.active_session_key].append({"role":"assistant","content":buffer})
            self.oai.save_context()

            # Schedule final processing
            Clock.schedule_once(lambda dt: self.on_streaming_complete(buffer), 0)
        except Exception as e:
            print(f"Error in streaming: {e}")
            self.streaming_active = False
            Clock.schedule_once(lambda dt: self.stop_submit_animation(), 0)

    def on_streaming_complete(self, response):
        self.streaming_active = False
        self.stop_submit_animation()

        # Only use TTS if the input came from voice recognition
        if self.voice_input_used:
            voice_id = self._get_voice_id()
            if len(response.split(' ')) > 200:
                # For long responses, summarize for voice output
                summary = self.oai.voice_summarize(response)
                self._speak_with_fallback(summary, voice_id)
            else:
                self._speak_with_fallback(response, voice_id)

        # Reset the voice input flag for next interaction
        self.voice_input_used = False

        # Scroll to bottom to show latest response
        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.1)

    def say_summary(self, prompt):
        response = self.oai.voice_summarize(prompt)
        if self.voice_input_used:
            voice_id = self._get_voice_id()
            self._speak_with_fallback(response, voice_id)

    def on_response(self, response):
        self.root.ids.outputwidget.text = response
        self.stop_submit_animation()

        # Only use TTS if the input came from voice recognition
        if self.voice_input_used:
            voice_id = self._get_voice_id()
            if len(response.split(' ')) > 200:
                summary = self.oai.voice_summarize(response)
                self._speak_with_fallback(summary, voice_id)
            else:
                self._speak_with_fallback(response, voice_id)

        # Reset the voice input flag for next interaction
        self.voice_input_used = False

    def start_submit_animation(self):
        """Start spinner animation on submit button"""
        submit_button = self.root.ids.submitter
        submit_button.text = "..."  # Simple text spinner
        submit_button.angle = 0  # Initialize angle property
        # Create smooth rotation animation
        self.submit_animation = Animation(angle=360, duration=0.8)
        self.submit_animation.repeat = True
        self.submit_animation.start(submit_button)

    def stop_submit_animation(self):
        """Stop spinner animation and restore submit button"""
        if self.submit_animation:
            self.submit_animation.cancel(self.root.ids.submitter)
            self.submit_animation = None
        submit_button = self.root.ids.submitter
        submit_button.text = self.original_submit_text
        submit_button.angle = 0  # Reset rotation

    def scroll_to_bottom(self):
        """Scroll the conversation view to the bottom"""
        try:
            scroll_view = self.root.ids.scroll_view
            scroll_view.scroll_y = 0  # 0 means bottom for ScrollView
        except Exception as e:
            print(f"Error scrolling to bottom: {e}")

    def get_conversation_history(self):
        """Get formatted conversation history for display"""
        try:
            # Ensure we have an active session
            self.oai.confirm_active_session()
            history = self.oai.prompt_history.get(self.oai.active_session_key, [])

            conversation_parts = []
            current_exchange = {}

            for msg in history:
                role = msg.get('role', '')
                content = msg.get('content', '').strip()

                if not content:
                    continue

                if role == 'user':
                    # Start new exchange
                    current_exchange = {'user': content}
                elif role == 'assistant' and 'user' in current_exchange:
                    # Complete the exchange
                    current_exchange['assistant'] = content
                    conversation_parts.append(f"You: {current_exchange['user']}\n\nAssistant: {current_exchange['assistant']}")
                    current_exchange = {}

            return "\n\n".join(conversation_parts)
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return ""

    def debug_conversation_history(self):
        """Debug method to print the raw conversation history structure"""
        try:
            self.oai.confirm_active_session()
            history = self.oai.prompt_history.get(self.oai.active_session_key, [])
            print(f"\n=== DEBUG: Conversation History ({len(history)} messages) ===")
            for i, msg in enumerate(history):
                role = msg.get('role', 'UNKNOWN')
                content = msg.get('content', '')[:50] + "..." if len(msg.get('content', '')) > 50 else msg.get('content', '')
                print(f"[{i}] Role: {role} | Content: {content}")
            print("=== END DEBUG ===\n")
        except Exception as e:
            print(f"Error debugging conversation history: {e}")

    def initialize_conversation_display(self, root):
        """Initialize the conversation display with either welcome message or restored history"""
        try:
            # Confirm active session and load history - ensure session is fully loaded
            self.oai.confirm_active_session()



            history = self.get_conversation_history()

            if history and history.strip():
                # If we have conversation history, display it with correct character names
                root.ids.outputwidget.text = history
                print(f"Restored conversation history for session: {self.oai.active_session_key}")
                # Scroll to bottom to show latest messages
                Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.2)
            else:
                # No history, show welcome message with character name
                voice_id = self._get_voice_id()
                character_name = self._get_character_display_name(voice_id)
                root.ids.outputwidget.text = f'Welcome to Entourage! I am {character_name}. How can I assist you today?'
                print(f"Started new conversation in session: {self.oai.active_session_key} with character: {character_name}")
        except Exception as e:
            print(f"Error initializing conversation display: {e}")
            # Fallback to welcome message
            root.ids.outputwidget.text = 'Welcome to Entourage! How can I assist you today?'

    def switch_conversation_display(self):
        """Switch conversation display when changing sessions"""
        try:
            # Update the system prompt for the new session
            self.oai.confirm_active_session()

            history = self.get_conversation_history()
            if history and history.strip():
                # Show conversation history for the new session
                self.root.ids.outputwidget.text = history
                print(f"Switched to session: {self.oai.active_session_key}")
                # Scroll to bottom to show latest messages
                Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.2)
            else:
                # No history in this session, show welcome
                self.root.ids.outputwidget.text = f'Welcome to session "{self.oai.active_session_key}"! How can I assist you today?'
                print(f"Switched to new session: {self.oai.active_session_key}")

                # Ensure system prompt is set for new session
                try:
                    system_prompt = self.oai.get_session_system_prompt()
                    if self.oai.active_session_key not in self.oai.prompt_history:
                        self.oai.prompt_history[self.oai.active_session_key] = [{"role":"system","content":system_prompt}]
                        self.oai.save_context()
                except Exception as sys_err:
                    print(f"Error setting system prompt for new session: {sys_err}")

        except Exception as e:
            print(f"Error switching conversation display: {e}")
            self.root.ids.outputwidget.text = 'Welcome to Entourage! How can I assist you today?'

    def submit(self):
        try:
            if self.worker:
                self.worker.stop()
                self.streaming_active = False
        except AttributeError:
            pass
        prompt = self.root.ids.inputwidget.text
        # Clear input box and prepare output for conversation display
        self.root.ids.inputwidget.text = ""

        # Show conversation history plus current prompt waiting for response
        temp_history = self.oai.prompt_history[self.oai.active_session_key].copy()
        temp_history.append({"role": "user", "content": prompt})

        # Get formatted conversation with the temporary history
        conversation_parts = []
        current_exchange = {}

        for msg in temp_history:
            role = msg.get('role', '')
            content = msg.get('content', '').strip()

            if not content:
                continue

            if role == 'user':
                current_exchange = {'user': content}
            elif role == 'assistant' and 'user' in current_exchange:
                current_exchange['assistant'] = content
                # Get character name for display
                voice_id = self._get_voice_id()
                character_name = self._get_character_display_name(voice_id)
                conversation_parts.append(f"You: {current_exchange['user']}\n\n{character_name}: {current_exchange['assistant']}")
                current_exchange = {}

        # Add the pending user message if there's no assistant response yet
        if 'user' in current_exchange and 'assistant' not in current_exchange:
            voice_id = self._get_voice_id()
            character_name = self._get_character_display_name(voice_id)
            conversation_parts.append(f"You: {current_exchange['user']}\n\n{character_name}: ")

        display_text = "\n\n".join(conversation_parts)
        self.root.ids.outputwidget.text = display_text

        # Auto-scroll to bottom
        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.1)
        self.worker = StreamingWorkerThread(target=self.evaluate_thread, args=(prompt,))
        self.worker.start()
        self.start_submit_animation()
        # Note: voice_input_used flag should already be set if this was triggered by voice

    def voicemode_toggle(self):
        self.oai.confirm_active_session()
        # TODO - refactor this to be more DRY
        self.listening = True if self.listening == False else False
        if self.listening:
            self.root.ids.vsession.text = 'Listening'
            self.root.ids.vsession.background_color = 0.812, 0.161, 0.169, 0.569

            self.audio.recording = True
        else:
            self.root.ids.vsession.text = 'Push to Talk'
            self.audio.recording = False
            self.root.ids.vsession.background_color = 1,1,1,1

        try:
            if self.worker:
                self.worker.stop()
                self.streaming_active = False
        except AttributeError:
            pass
        self.worker = WorkerThread(target=self.gather_vocal_audio_for_transcription, args=())
        self.worker.start()

    def gather_vocal_audio_for_transcription(self):
        if self.listening:
            self.audio.start_record_audio()
            myprompt = self.audio.transcribe_audio()
            Clock.schedule_once(lambda dt: setattr(self.root.ids.inputwidget, 'text', myprompt.text), 0)
            # Set flag to indicate this interaction used voice input
            self.voice_input_used = True
            Clock.schedule_once(lambda dt: self.submit(), 0.1)  # Small delay to ensure text is set
            self.listening = False

    def on_keyboard(self, instance, key, scancode, codepoint, modifier):
        # TODO - not implemented yet
        if modifier == ['shift'] and codepoint == '\n':
            # Add your text processing logic here
            self.submit()

    def first_clear(self):
        if self.cleared == False:
            self.root.ids.inputwidget.text = ''
            self.cleared = True

class ChattorFlow(FloatLayout):
    pass

class CustomDropDown(DropDown):
    pass

# Register custom TextInput classes with Factory
Factory.register('NoSelectTextInput', cls=NoSelectTextInput)
Factory.register('ReadOnlyTextInput', cls=ReadOnlyTextInput)
Factory.register('NoTrackToggleButton', cls=NoTrackToggleButton)

class ConfigurationPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        try:
            with open('session_tracker.json', 'r') as f:
                self.sessions = json.load(f)
        except FileNotFoundError:
            default_system_prompt = 'You are a witty and keen conversationalist. You try to keep your responses as short as possible but always try to be friendly and humorous. You regularly ask questions and make sure to respond with a clear and concise answer. You are a good listener and a good communicator'
            self.sessions = {
                'Default session': {
                    'currently_active': True,
                    'system_prompt': default_system_prompt,
                    'voice_id': 'Rachel',
                    'voice_effects': {
                        'stability': 0.5,
                        'speed': 1.0,
                        'style': 0.0
                    }
                }
            }
            with open('session_tracker.json', 'w') as f:
                json.dump(self.sessions, f)

        # Migrate existing sessions to new format
        self.migrate_sessions()

        for session in self.sessions:
            self.restore_sessions(session)
            # TODO - extend object that is passed into add_new_/restore_session to include
            # the currently_active flag, selected voice and other settings
        dropdown = CustomDropDown()
        mainbutton = self.ids.voicebutton
        mainbutton.bind(on_release=dropdown.open)
        #mainbutton.id = 'voicebutton'
        dropdown.bind(on_select=lambda instance, x: setattr(mainbutton, 'text', x))
        #self.ids.dropdown_layout.add_widget(mainbutton)

        # Load settings for the currently active session
        self.load_session_settings()

    def restore_sessions(self,session):
        button_layout = self.ids.button_layout
        if self.sessions[session].get('currently_active'):
            new_session_button = NoTrackToggleButton(group='sessions', text=f"{session}", size_hint_y=None, height=80, state='down')
        else:
            new_session_button = NoTrackToggleButton(group='sessions', text=f"{session}", size_hint_y=None, height=80)
        button_layout.add_widget(new_session_button)

    def add_new_session(self, bid=None):
        if bid is None:
            # generate uuid
            from uuid import uuid4
            bid = f"session-{str(uuid4())[:6]}"

        # Get default settings for new session
        default_system_prompt = 'You are a witty and keen conversationalist. You try to keep your responses as short as possible but always try to be friendly and humorous. You regularly ask questions and make sure to respond with a clear and concise answer. You are a good listener and a good communicator'
        self.sessions[bid] = {
            'currently_active': False,
            'system_prompt': default_system_prompt,
            'voice_id': 'Rachel',
            'voice_effects': {
                'stability': 0.5,
                'speed': 1.0,
                'style': 0.0
            }
        }

        button_layout = self.ids.button_layout
        if self.sessions[bid].get('currently_active'):
            new_session_button = NoTrackToggleButton(group='sessions', text=f"{bid}", size_hint_y=None, height=80, state='down', background_color=(0.812, 0.161, 0.169, 0.569))
        else:
            new_session_button = NoTrackToggleButton(group='sessions', text=f"{bid}", size_hint_y=None, height=80)

        button_layout.add_widget(new_session_button)

    def load_session_settings(self):
        """Load voice and system prompt settings for the currently active session"""
        active_session = None
        for session_name, session_data in self.sessions.items():
            if session_data.get('currently_active'):
                active_session = session_name
                break

        if active_session and active_session in self.sessions:
            session_data = self.sessions[active_session]

            # Set voice button text
            voice_id = session_data.get('voice_id', 'Rachel')
            self.ids.voicebutton.text = voice_id

            # Set system prompt text
            system_prompt = session_data.get('system_prompt', 'You are a witty and keen conversationalist. You try to keep your responses as short as possible but always try to be friendly and humorous.')
            self.ids.system_prompt_input.text = system_prompt

            # Load voice effects settings
            voice_effects = session_data.get('voice_effects', {})
            if hasattr(self.ids, 'stability_slider'):
                self.ids.stability_slider.value = voice_effects.get('stability', 0.5)
            if hasattr(self.ids, 'speed_slider'):
                self.ids.speed_slider.value = voice_effects.get('speed', 1.0)
            if hasattr(self.ids, 'style_slider'):
                self.ids.style_slider.value = voice_effects.get('style', 0.0)

    def migrate_sessions(self):
        """Migrate existing sessions to new format with system_prompt and voice_id"""
        default_system_prompt = 'You are a witty and keen conversationalist. You try to keep your responses as short as possible but always try to be friendly and humorous. You regularly ask questions and make sure to respond with a clear and concise answer. You are a good listener and a good communicator'

        sessions_updated = False
        for session_name, session_data in self.sessions.items():
            if 'system_prompt' not in session_data:
                session_data['system_prompt'] = default_system_prompt
                sessions_updated = True
            if 'voice_id' not in session_data:
                session_data['voice_id'] = 'Rachel'
                sessions_updated = True
            if 'voice_effects' not in session_data:
                session_data['voice_effects'] = {
                    'stability': 0.5,
                    'speed': 1.0,
                    'style': 0.0
                }
                sessions_updated = True

        # Save updated sessions if any changes were made
        if sessions_updated:
            with open('session_tracker.json', 'w') as f:
                json.dump(self.sessions, f)
            print("Migrated existing sessions to new format")

    def reset_system_prompt(self):
        """Reset system prompt to default"""
        default_prompt = 'You are a witty and keen conversationalist. You try to keep your responses as short as possible but always try to be friendly and humorous. You regularly ask questions and make sure to respond with a clear and concise answer. You are a good listener and a good communicator'
        self.ids.system_prompt_input.text = default_prompt

    def save_sessions(self):
        button_layout = self.ids.button_layout
        old_active_session = None
        new_active_session = None

        # Find which session was active and which is now active
        for session_name, session_data in self.sessions.items():
            if session_data.get('currently_active'):
                old_active_session = session_name

        for widget in button_layout.children:
            if self.sessions[widget.text].get('currently_active'):
                self.sessions[widget.text]['currently_active'] = False
            if widget.state == 'down':
                self.sessions[widget.text]['currently_active'] = True
                new_active_session = widget.text

        with open('session_tracker.json', 'w') as f:
            json.dump(self.sessions, f)

        # Update the conversation display if session changed
        if new_active_session and new_active_session != old_active_session:
            app = App.get_running_app()
            app.oai.confirm_active_session()
            app.switch_conversation_display()

        self.close_config()
        self.dismiss()

    def on_open(self):
        """Called when popup opens - refresh session settings"""
        super().on_open()
        self.load_session_settings()

    def close_config(self):
        # Get the currently active session
        active_session = None
        for session_name, session_data in self.sessions.items():
            if session_data.get('currently_active'):
                active_session = session_name
                break

        if active_session:
            # Save voice selection to the active session
            mainbutton = self.ids.voicebutton
            voice = mainbutton.text.split(' ')[0]
            if voice != 'Voice':
                self.sessions[active_session]['voice_id'] = voice

            # Save system prompt to the active session
            system_prompt = self.ids.system_prompt_input.text.strip()
            if system_prompt:
                self.sessions[active_session]['system_prompt'] = system_prompt

            # Save voice effects settings
            voice_effects = {}
            if hasattr(self.ids, 'stability_slider'):
                voice_effects['stability'] = self.ids.stability_slider.value
            if hasattr(self.ids, 'speed_slider'):
                voice_effects['speed'] = self.ids.speed_slider.value
            if hasattr(self.ids, 'style_slider'):
                voice_effects['style'] = self.ids.style_slider.value

            if voice_effects:
                self.sessions[active_session]['voice_effects'] = voice_effects

                # Update the session tracker file
                with open('session_tracker.json', 'w') as f:
                    json.dump(self.sessions, f)

        # Still maintain global config for backward compatibility
        try:
            with open('configuration.json','r') as infile:
                config = json.load(infile)
            mainbutton = self.ids.voicebutton
            voice = mainbutton.text.split(' ')[0]
            if voice != 'Voice':
                config['voice_id'] = voice
            with open('configuration.json','w') as outfile:
                json.dump(config, outfile)
        except:
            pass

    def delete_session(self):
        # iterate through all widgets and remove widget with property down
        button_layout = self.ids.button_layout
        for widget in button_layout.children:
            if widget.state == 'down':
                if widget.text == 'Default session':
                    return
                del(self.sessions[widget.text])
                button_layout.remove_widget(widget)

if __name__ == "__main__":
    EntourageApp().run()
