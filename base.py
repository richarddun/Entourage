from kivy.app import App
from kivy.uix.widget import Widget

class ChattorApp(App):
    def build(self):
        return ChattorFlow()

class ChattorFlow(Widget):
    pass

if __name__ == "__main__":
    ChattorApp().run()

