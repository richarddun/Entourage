# gpt-client

Client interface to OpenAI's gpt3.5-turbo (as of right now) which requires : 

1. An openAI API key (for as long as oauth remains unsupported for API auth at any rate!), stored in system Env variables
2. An AWS keypair with Amazon Polly full access privileges, stored in system Env variables
3. AWS (boto3), Kivy and OpenAI python modules

Features : 

- Written entirely in python, using the [Kivy Framework](https://kivy.org) so eventually will be cross built for linux, pc, ios and android
- supports voice interface using openAI whisper and Amazon polly

![](https://github.com/richarddun/gpt-client/blob/master/gpt-client.png)
