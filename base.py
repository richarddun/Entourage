from kivy.app import App
from kivy.uix.widget import Widget
from kivy.core.window import Window

class ChattorApp(App):
    def build(self):
        return ChattorFlow()
    
    def submit(self):
        self.print_widget_properties()

    def print_widget_properties(self):
        self.root.ids.outputwidget.text += self.root.ids.inputwidget.text

class ChattorFlow(Widget):
    pass

if __name__ == "__main__":
    ChattorApp().run()

