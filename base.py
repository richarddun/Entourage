from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
import openai
import os
import threading
from kivy.clock import Clock
from autrasyn import PollyInterface

class AICommunicator():

    def __init__(self) -> None:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.prompt_history = [{"role":"system","content":"You are a helpful assistant"}]

    def get_prompt_history(self):
        return self.prompt_history
    
    def clear_prompt_history(self):
        self.prompt_history = [{"role":"system","content":"You are a helpful assistant"}]

    def evaluate(self,prompt):
        self.prompt_history.append({"role":"user","content":f"{prompt}"})
        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = self.prompt_history
    )
        self.prompt_history.append({"role":"assistant","content":f"{response.choices[0].message.content.strip()}"})
        return response.choices[0].message.content.strip()

class ChattorApp(App):

    def build(self):
        self.cleared = False
        self.oai = AICommunicator()
        self.popup = Popup(title='Processing...', content=Label(text='Waiting for AI response...'), auto_dismiss=False, size_hint=(.8, .8))
        self.speaker = PollyInterface()
        return ChattorFlow()
    
    def evaluate_thread(self, prompt):
        response = self.oai.evaluate(prompt)
        Clock.schedule_once(lambda dt: self.on_response(response), 0)

    def on_response(self, response):
        self.root.ids.outputwidget.text = response
        self.popup.dismiss()
        self.speaker.say(response)

    def submit(self):
        prompt = self.root.ids.inputwidget.text
        threading.Thread(target=self.evaluate_thread, args=(prompt,)).start()
        self.popup.open()

    def on_keyboard(self, instance, key, scancode, codepoint, modifier):
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

