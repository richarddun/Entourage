from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from autrasyn import PollyInterface, AudioInterface
import openai
import os
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

class AICommunicator():

    def __init__(self,temperament=None) -> None:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.terse = False
        self.reset_prompt_history(temperament)

    def get_prompt_history(self):
        return self.prompt_history
    
    def reset_prompt_history(self,temperament):
        if temperament is None:
            self.prompt_history = [{"role":"system","content":"You are a witty and keen conversationalist.  You try to keep your responses as short as possible but always try to be friendly and humorous.  You regularly ask questions and make sure to respond with a clear and concise answer.  You are a good listener and a good communicator"}]
        else:
            self.prompt_history = [{"role":"system","content":f"{temperament}"}]

    def evaluate(self,prompt):
        #TODO - implement streaming response
        self.prompt_history.append({"role":"user","content":f"{prompt}"})
        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = self.prompt_history
    )
        self.prompt_history.append({"role":"assistant","content":f"{response.choices[0].message.content.strip()}"})
        return response.choices[0].message.content.strip()
    
    def voice_summarize(self,prompt):
        lnbrk = '\n'
        summarizer = [{"role":"user","content":
                       f"Please summarise the following text\
                          in a way that would sound natural in a spoken conversation : {lnbrk}{prompt}"}]
        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = summarizer
    )
        #self.prompt_history.append({"role":"assistant","content":f"{response.choices[0].message.content.strip()}"})
        return response.choices[0].message.content.strip()


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
        if len(response) > 100:
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

