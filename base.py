from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from autrasyn import PollyInterface, AudioInterface
from oaiops import AICommunicator
import threading

class WorkerThread(threading.Thread):
    def __init__(self, target, args):
        super().__init__(target=target, args=args)
        self.stop_flag = threading.Event()

    def run(self):
        while not self.stop_flag.is_set():
            self._target(*self._args, **self._kwargs)  # Call the target function
            self.stop_flag.set()

    def stop(self):
        self.stop_flag.set()

class ChattorApp(App):

    def build(self):
        self.cleared = False
        self.oai = AICommunicator()
        self.popup = Popup(title='Processing...', content=Label(text='Waiting for AI response...'), auto_dismiss=False, size_hint=(.8, .8))
        self.speaker = PollyInterface()
        self.audio = AudioInterface()
        self.listening = False
        return ChattorFlow()
    
    def evaluate_thread(self, prompt):
        response = self.oai.evaluate(prompt)
        Clock.schedule_once(lambda dt: self.on_response(response), 0)

    def say_summary(self, prompt):
        response = self.oai.voice_summarize(prompt)
        self.speaker.say(response)
        
    def on_response(self, response):
        self.root.ids.outputwidget.text = response
        self.popup.dismiss()
        print(len(response))
        if len(response) > 500:
            self.say_summary(response)
        else:
            self.speaker.say(response)

    def submit(self):
        try:
            if self.worker:  
                self.worker.stop()
        except AttributeError:
            pass
        prompt = self.root.ids.inputwidget.text
        self.worker = WorkerThread(target=self.evaluate_thread, args=(prompt,))
        self.worker.start()
        self.popup.open()
    
    def voicemode_toggle(self):
        # TODO - refactor this to be more DRY
        self.listening = True if self.listening == False else False
        print(f'toggled listening, now {self.listening}')
        if self.listening:
            self.root.ids.vsession.text = 'voice on'
            self.root.ids.vsession.background_color = 0.812, 0.161, 0.169, 0.569

            self.audio.recording = True
        else:
            self.root.ids.vsession.text = 'voice off'
            self.audio.recording = False
            self.root.ids.vsession.background_color = 1,1,1,1

        try:
            if self.worker:  
                self.worker.stop()
        except AttributeError:
            pass
        self.worker = WorkerThread(target=self.gather_vocal_audio_for_transcription, args=())
        self.worker.start()

    def gather_vocal_audio_for_transcription(self):
        if self.listening:
            print('start audio recording')
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

if __name__ == "__main__":
    ChattorApp().run()
