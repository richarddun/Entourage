import os
#os.environ["KIVY_NO_ARGS"] = "1"
#os.environ["KIVY_NO_CONSOLELOG"] = "1"
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.dropdown import DropDown
from kivy.clock import Clock
from autrasyn import PollyInterface, AudioInterface
from oaiops import AICommunicator
import threading
import json
import queue
import time



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

class EntourageApp(App):

    def build(self):
        self.cleared = False
        self.oai = AICommunicator(memory=True)
        self.popup = Popup(title='Processing...', content=Label(text='Waiting for AI response...'), auto_dismiss=False, size_hint=(.8, .8))
        self.speaker = PollyInterface()
        self.audio = AudioInterface()
        self.listening = False
        self.response_queue = queue.Queue()
        self.streaming_active = False
        self.tts_worker = None  # Worker thread for TTS playback
        return ChattorFlow()

    def load_kv(self, filename=None):
        # Load the improved KV file
        return super().load_kv(filename='Entourage_improved.kv')

    def on_stop(self):
        self.oai.export_chat_log()
        # Ensure TTS worker thread is stopped and cleaned up
        if self.tts_worker and self.tts_worker.is_alive():
            self.speaker.streaming_active = False
            self.tts_worker.join()

    def evaluate_thread(self, prompt):
        self.oai.confirm_active_session()
        response = self.oai.evaluate(prompt)
        # Process streaming response
        self.process_streaming_response(response, prompt)

    def process_streaming_response(self, response, prompt):
        self.streaming_active = True

        try:
            # Generator for text chunks from streaming response
            text_chunks = (chunk.choices[0].delta.content for chunk in response if chunk.choices[0].delta.content is not None)

            def update_ui(dt, text):
                self.root.ids.outputwidget.text = text

            buffer = ""
            ui_text = ""

            # Stop any existing TTS worker
            if self.tts_worker and self.tts_worker.is_alive():
                self.speaker.streaming_active = False
                self.tts_worker.join()

            # Define a generator to yield text chunks for TTS worker
            def tts_text_generator():
                nonlocal buffer, ui_text
                for chunk in text_chunks:
                    if not self.streaming_active:
                        break
                    buffer += chunk
                    ui_text = buffer
                    yield chunk

            # Start TTS playback in a separate thread
            import threading
            self.speaker.streaming_active = True
            self.tts_worker = threading.Thread(target=self.speaker.say_streaming, args=(tts_text_generator(),))
            self.tts_worker.start()

            # Update UI progressively on main thread
            for chunk in tts_text_generator():
                if not self.streaming_active:
                    break
                Clock.schedule_once(lambda dt, text=ui_text: update_ui(dt, text), 0)

            # Wait for TTS worker to finish
            self.tts_worker.join()

            # Add the complete response to history
            self.oai.prompt_history[self.oai.active_session_key].append({"role":"assistant","content":buffer})
            self.oai.save_context()

            # Schedule final processing
            Clock.schedule_once(lambda dt: self.on_streaming_complete(buffer), 0)
        except Exception as e:
            print(f"Error in streaming: {e}")
            self.streaming_active = False
            self.speaker.streaming_active = False
            Clock.schedule_once(lambda dt: self.popup.dismiss(), 0)

    def on_streaming_complete(self, response):
        self.streaming_active = False
        self.popup.dismiss()
        if len(response.split(' ')) > 200:
            # For long responses, summarize for voice output
            summary = self.oai.voice_summarize(response)
            self.speaker.say(summary)
        else:
            self.speaker.say(response)

    def say_summary(self, prompt):
        response = self.oai.voice_summarize(prompt)
        self.speaker.say(response)

    def on_response(self, response):
        self.root.ids.outputwidget.text = response
        self.popup.dismiss()
        if len(response.split(' ')) > 200:
            self.say_summary(response)
        else:
            self.speaker.say(response)

    def submit(self):
        try:
            if self.worker:
                self.worker.stop()
                self.streaming_active = False
        except AttributeError:
            pass
        prompt = self.root.ids.inputwidget.text
        self.root.ids.outputwidget.text = ""  # Clear previous response
        self.worker = StreamingWorkerThread(target=self.evaluate_thread, args=(prompt,))
        self.worker.start()
        self.popup.open()

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
            Clock.schedule_once(lambda dt: self.submit(), 0)
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

class ConfigurationPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        try:
            with open('session_tracker.json', 'r') as f:
                self.sessions = json.load(f)
        except FileNotFoundError:
            self.sessions = {'Default session':{'currently_active':True}}
            with open('session_tracker.json', 'w') as f:
                json.dump(self.sessions, f)
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

    def restore_sessions(self,session):
        button_layout = self.ids.button_layout
        if self.sessions[session].get('currently_active'):
            new_session_button = ToggleButton(group='sessions', text=f"{session}", size_hint_y=None, height=80, state='down')
        else:
            new_session_button = ToggleButton(group='sessions', text=f"{session}", size_hint_y=None, height=80)
        button_layout.add_widget(new_session_button)

    def add_new_session(self, bid=None):
        if bid is None:
            # generate uuid
            from uuid import uuid4
            bid = f"session-{str(uuid4())[:6]}"
            self.sessions[bid] = {'currently_active':False}
        button_layout = self.ids.button_layout
        if self.sessions[bid].get('currently_active'):
            new_session_button = ToggleButton(group='sessions', text=f"{bid}", size_hint_y=None, height=80, state='down', background_color=(0.812, 0.161, 0.169, 0.569))
        else:
            new_session_button = ToggleButton(group='sessions', text=f"{bid}", size_hint_y=None, height=80)
        self.sessions[bid] = {'currently_active':False}

        button_layout.add_widget(new_session_button)


    def save_sessions(self):
        button_layout = self.ids.button_layout
        for widget in button_layout.children:
            if self.sessions[widget.text].get('currently_active'):
                self.sessions[widget.text]['currently_active'] = False
            if widget.state == 'down':
                self.sessions[widget.text]['currently_active'] = True
        with open('session_tracker.json', 'w') as f:
            json.dump(self.sessions, f)
        self.close_config()
        self.dismiss()

    def close_config(self):
        mainbutton = self.ids.voicebutton
        voice = mainbutton.text.split(' ')[0]
        if voice == 'Voice':
            return
        # save mainbutton.text property to json file under voice_id key
        with open('configuration.json','r') as infile:
            config = json.load(infile)
        config['voice_id'] = mainbutton.text.split(' ')[0]
        # save json file
        with open('configuration.json','w') as outfile:
            json.dump(config, outfile)
        #TODO - Bubble the change of session over the oaiops.py, somehow

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
