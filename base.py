from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
import openai
import os
from kivy.clock import Clock

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
        print(self.prompt_history)
        return response.choices[0].message.content.strip()

class ChattorApp(App):

    def build(self):
        self.cleared = False
        self.oai = AICommunicator()
        return ChattorFlow()
    
    def submit(self):
        #self.oai = AICommunicator()
        response = self.oai.evaluate(self.root.ids.inputwidget.text)
        #self.root.ids.outputwidget.text = '...Loading response'
        self.root.ids.outputwidget.text = response

    def submit_wrapper(self):
        Clock.schedule_once(lambda dt: self.submit())
    
    def first_clear(self):
        if self.cleared == False:
            self.root.ids.inputwidget.text = ''
            self.cleared = True
        

class ChattorFlow(FloatLayout):
    pass

if __name__ == "__main__":
    ChattorApp().run()

