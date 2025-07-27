import openai
import os
import json
import datetime
from dotenv import load_dotenv

class AICommunicator():

    def __init__(self,memory=False) -> None:
        # Load environment variables from .env file
        load_dotenv()

        # Initialize OpenAI client with API key from environment
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.terse = False
        self.load_json_configuration()
        self.reset_prompt_history(memory)
        self.active_session_key = 'Default session'

    def reset_prompt_history(self, memory = False):
        if memory is False:
            self.prompt_history[self.active_session_key] = [{"role":"system","content":f"{self.configuration['system_prompt']}"}]
        else:
            self.remember_last_context()
            #self.prompt_history = [{"role":"system","content":f"{override}"}]

    def remember_last_context(self):
        # read last saved chat context json file
        try:
            with open('all_chat_context.json', 'r') as f:
                self.prompt_history = json.load(f)
        except FileNotFoundError:
            self.prompt_history = {}
            with open('all_chat_context.json', 'w') as f:
                json.dump(self.prompt_history, f)

    def display_chat_log(self):
        # display chat log
        for message in self.prompt_history:
            print(message["role"],message["content"])

    def export_chat_log(self):
        self.save_context() # firstly save the actual log!
        # export chat log
        with open('chat_log.txt', 'a') as f:
            # add todays date and time with each export
            f.write(f"\n\n{'-'*20}\nExported on {datetime.datetime.now()}\n")
            for session in self.prompt_history:
                f.write(f"\n\n{'-'*20}\nSession ID : {session}\n")
                for message in self.prompt_history[session]:
                    # add role and content to file
                    f.write(f"> # {message['role']} # : {message['content']}\n")


    def save_context(self):
        # save current chat log
        with open('all_chat_context.json', 'w') as f:
            json.dump(self.prompt_history, f)


    def confirm_active_session(self):
        # open active_sessions.json and load the prompt_history from the session with
        # active: true
        try:
            with open('session_tracker.json', 'r') as f:
                active_sessions = json.load(f)
                for session in active_sessions:
                    if active_sessions[session]['currently_active'] is True:
                        self.active_session_key = session
        except FileNotFoundError:
            with open('session_tracker.json', 'w') as f:
                json.dump({'Default session':{'currently_active':True}}, f)

        try:
            test = self.prompt_history[self.active_session_key]
        except KeyError:
            self.prompt_history[self.active_session_key] = [{"role":"system","content":f"{self.configuration['system_prompt']}"}]
            self.save_context()
            self.confirm_active_session()

    def load_json_configuration(self):
        # load configuration json file
        # e.g. {'system_prompt': 'You are a witty and keen conversationalist.
        #        You try to keep your responses as short as possible
        #        but always try to be friendly and humorous.
        #        You regularly ask questions and make sure to respond with a clear and concise answer.
        #        You are a good listener and a good communicator'}
        try:
            with open('configuration.json', 'r') as f:
                self.configuration = json.load(f)
        except FileNotFoundError:
            with open('configuration.json', 'w') as f:
                json.dump({'system_prompt': 'You are a witty and keen conversationalist.   You try to keep your responses as short as possible  but always try to be friendly and humorous.   You regularly ask questions and make sure to respond with a clear and concise answer.   You are a good listener and a good communicator','voice_id': 'Emma'}, f)
            self.load_json_configuration()

    def get_prompt_history(self):
        return self.prompt_history

    def evaluate(self, prompt):
        # Add user message to history
        self.prompt_history[self.active_session_key].append({"role":"user","content":f"{prompt}"})

        # Create a streaming response
        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",  # Updated from gpt-3.5-turbo-16k to gpt-4.1-mini
            messages=self.prompt_history[self.active_session_key],
            stream=True
        )

        # Return the streaming response
        return response

    def evaluate_non_streaming(self, prompt):
        # Non-streaming version for voice summarization
        from openai import ChatCompletionMessage
        self.prompt_history[self.active_session_key].append({"role":"user","content":f"{prompt}"})
        # Convert dict messages to ChatCompletionMessage objects if needed
        messages = []
        for msg in self.prompt_history[self.active_session_key]:
            if isinstance(msg, dict):
                messages.append(ChatCompletionMessage(**msg))
            else:
                messages.append(msg)
        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",  # Updated from gpt-3.5-turbo-16k to gpt-4.1-mini
            messages=messages
        )
        self.prompt_history[self.active_session_key].append({"role":"assistant","content":f"{response.choices[0].message.content.strip()}"})
        return response.choices[0].message.content.strip()

    def voice_summarize(self, prompt):
        lnbrk = '\n'
        # Fix the escape sequence by removing the backslash and extra spaces
        summarizer = [{"role":"user","content":
                       f"Please summarise the following text in a way that would sound natural in a spoken conversation : {lnbrk}{prompt}"}]
        # Convert dict messages to ChatCompletionMessage objects if needed
        from openai import ChatCompletionMessage
        messages = []
        for msg in summarizer:
            if isinstance(msg, dict):
                messages.append(ChatCompletionMessage(**msg))
            else:
                messages.append(msg)
        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",  # Updated from gpt-3.5-turbo to gpt-4.1-mini
            messages=messages
        )
        #self.prompt_history.append({"role":"assistant","content":f"{response.choices[0].message.content.strip()}"})
        return response.choices[0].message.content.strip()
