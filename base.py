from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window

class ChattorApp(App):
    def build(self):
        return ChattorFlow()
    
    def submit(self):
        self.print_widget_properties()
        pass

    def print_widget_properties(self):
        #print(self.root.ids)
        self.root.ids.outputwidget.text += (self.root.ids.inputwidget.text + "\n")

class ChattorFlow(FloatLayout):
    pass

if __name__ == "__main__":
    ChattorApp().run()

