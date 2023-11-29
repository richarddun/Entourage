from multiprocessing import Process, Queue, Lock, Value
import pyaudio
import openai
import time
from autrasyn import PollyInterface

def record_audio(q,rlock,rval):
    chunk_duration = 4  # Duration of each audio chunk in seconds
    sample_rate = 44100  # Sample rate of the audio
    chunk_size = int(sample_rate * chunk_duration)  # Size of each chunk in frames

    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    # Open audio stream
    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=sample_rate,
                        input=True,
                        frames_per_buffer=chunk_size)

    # Keep the recording process running
    streaming_stopped = False
    with rlock:
        while rval.value:
            # Read audio data from the stream
            data = stream.read(chunk_size)

            # Enqueue the audio chunk to the queue
            q.put(data)
    return

def transcribe_audio_chunks(qin,qout):
    """
    Fetch audio from the queue and send it to the OpenAI API for transcription
    """
    while True:
        try:
            transcript = openai.Audio.transcribe("whisper-1", qin.get(timeout=4))
            # Write the audio chunk to the pipeline
            qout.put(transcript)
        except qin.empty:
            break

def complete_chat(qin,qout,rlock,rval):
    """
    Fetch partially completed openAI whisper transcriptions
    """
    chatstr = ''
    # TODO - implement and handle streaming responses from OpenAI chat completion
    while True:
        if qin.empty:
            with rlock:
                if not rval.value: # if we have stopped recording just assemble the prompt at the end
                    response = openai.ChatCompletion.create(model="gpt-3.5-turbo-16k",
                                                            messages={"role":"user","content":f"{chatstr}"})
                    qout.put(response)
                    break
        else:
            tmsg = qin.get(timeout=4)
            chatstr += (' ' + tmsg) # should break up all the fragmented transcripts with a space

def synthesize_audio(speech_eng,qin,qout):
    """
    Fetch audio from the chat completion queue and send it to the Polly API for synthesis
    """
    while True:
        try:
            speech_eng.say(qin.get(timeout=4))
        except qin.empty:
            break


if __name__ == '__main__':
    recorder_on = Value('b', True) 
    recording_lock = Lock()
    speech_engine = PollyInterface()

    # Create a multiprocessing Queue for storing the audio chunks
    audio_queue = Queue()
    # Create a multiprocessing Queue for storing the transcriptions
    transcript_queue = Queue()
    # Create a multiprocessing Queue for storing the chat responses
    chat_queue = Queue()
    # Create a multiprocessing Queue for Polly synthesis
    synth_queue = Queue()

    # Start the audio recording process
    audio_process = Process(target=record_audio, args=(audio_queue,recording_lock,recorder_on))
    audio_process.start()
    time.sleep(10)

    with recording_lock:
        recorder_on.value = False
    # Stop the recording process 
    audio_process.join()

    # Start the transcription process
    transcribe_process = Process(target=transcribe_audio_chunks, args=(audio_queue, transcript_queue))
    transcribe_process.start()

    # Start the chat process
    chat_process = Process(target=complete_chat, args=(transcript_queue,
                                                       synth_queue,
                                                       recording_lock, 
                                                       recorder_on)
                            )
    chat_process.start()
    chat_process.join()
    # Stop the transcription process
    transcribe_process.join()
    # Start speech synthesis process
    synthesis_process = Process(target=synthesize_audio, args=(speech_engine, chat_queue, synth_queue))
    synthesis_process.start()
    synthesis_process.join()



