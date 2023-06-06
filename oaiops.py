import openai
import os

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

