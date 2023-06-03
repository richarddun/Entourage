from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
import openai
import os
#import asyncio
#from kivy.base import EventLoop
from kivy.clock import Clock

class AICommunicator():

    def __init__(self) -> None:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.api_key = os.getenv("OPENAI_API_KEY")

    def evaluate(self,prompt):
        # send transcript to openAI for chat completion which will summarise the text
        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = [
        {"role":"system","content":"You are a helpful assistant"},
        {"role":"user","content":f"{prompt}"
    }
        ]
    )
        return response.choices[0].message.content.strip()

class ChattorApp(App):

    def build(self):
        return ChattorFlow()
    
    def submit(self):
        self.oai = AICommunicator()
        response = self.oai.evaluate(self.root.ids.inputwidget.text)
        #self.root.ids.outputwidget.text = '...Loading response'
        self.root.ids.outputwidget.text = response

    def submit_wrapper(self):
        Clock.schedule_once(lambda dt: self.submit())

class ChattorFlow(FloatLayout):
    pass

if __name__ == "__main__":
    ChattorApp().run()

