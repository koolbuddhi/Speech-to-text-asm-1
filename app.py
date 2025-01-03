from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import assemblyai as aai
import threading
import asyncio
from constant import assemblyai_api_key
import io
import wave
import time
from enum import Enum

app = Flask(__name__)
socketio = SocketIO(app)

aai.settings.api_key = assemblyai_api_key
transcriber = None  
session_id = None  
transcriber_lock = threading.Lock()  

prompt = """You are a medical transcript analyzer. Your task is to detect and format words/phrases that fit into the following five categories:

Protected Health Information (PHI): Change the font color to red using <span style="color: red;">. This includes personal identifying information such as names, ages, nationalities, gender identities, and organizations.
Medical Condition/History: Highlight the text in light green using <span style="background-color: lightgreen;">. This encompasses any references to illnesses, diseases, symptoms, or conditions.
Anatomy: Italicise the text using <em>. This covers any mentions of body parts or anatomical locations.
Medication: Highlight the text in yellow using <span style="background-color: yellow;">. This includes any references to prescribed drugs, over-the-counter medications, vitamins, or supplements.
Tests, Treatments, & Procedures: Change the font color to green using <span style="color: darkblue;">. This involves any mentions of medical tests, treatments, or procedures performed or recommended.
You will receive a medical transcript along with a list of entities detected by AssemblyAI. Use the detected entities to format the text accordingly and also identify and format any additional relevant medical conditions, anatomical references, medications, and procedures that are not included in the detected entities. Do not return anything except the original transcript which has been formatted. Don't write any additional prefacing text like "here's the formatted transcript" """

class TranscriptionMode(Enum):
    REALTIME = "realtime"
    ASYNC = "async"

# Global variables
current_mode = TranscriptionMode.REALTIME
is_active = False
CHUNK_DURATION = 5  # seconds
SAMPLE_RATE = 16000

def on_open(session_opened: aai.RealtimeSessionOpened):
    global session_id
    session_id = session_opened.session_id
    print("Session ID:", session_id)

def on_data(transcript: aai.RealtimeTranscript):
    if not transcript.text:
        return

    if isinstance(transcript, aai.RealtimeFinalTranscript):
        socketio.emit('transcript', {'text': transcript.text})
        asyncio.run(analyze_transcript(transcript.text))
    else:
        # Emit the partial transcript to be displayed in real-time
        socketio.emit('partial_transcript', {'text': transcript.text})


async def analyze_transcript(transcript):
   # result = aai.Lemur().task(
   #     prompt, 
   #     input_text = transcript,
   #     final_model=aai.LemurModel.claude3_5_sonnet
   # ) 

    print("Emitting formatted transcript for:", transcript)
    socketio.emit('formatted_transcript', {'text': transcript})  # for testing

    #socketio.emit('formatted_transcript', {'text': result.response})


def on_error(error: aai.RealtimeError):
    print("An error occurred:", error)

def on_close():
    global session_id
    session_id = None
    print("Closing Session")

def transcribe_real_time():
    global transcriber  
    transcriber = aai.RealtimeTranscriber(
        sample_rate=16_000,
        on_data=on_data,
        on_error=on_error,
        on_open=on_open,
        on_close=on_close
    )

    transcriber.connect()

    microphone_stream = aai.extras.MicrophoneStream(sample_rate=16_000)
    transcriber.stream(microphone_stream)

def record_and_transcribe_async():
    global is_active
    
    microphone_stream = aai.extras.MicrophoneStream(sample_rate=SAMPLE_RATE)
    frames = []
    chunk_start_time = time.time()
    
    for audio_chunk in microphone_stream:
        if not is_active:
            break
            
        frames.append(audio_chunk)
        current_time = time.time()
        
        # Check if we've recorded for CHUNK_DURATION seconds
        if current_time - chunk_start_time >= CHUNK_DURATION:
            # Save the audio chunk
            audio_data = io.BytesIO()
            with wave.open(audio_data, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(b''.join(frames))
            
            # Submit this chunk for transcription
            threading.Thread(target=transcribe_chunk, args=(audio_data.getvalue(),)).start()
            
            # Reset for next chunk
            frames = []
            chunk_start_time = current_time

def transcribe_chunk(audio_data):
    config = aai.TranscriptionConfig(
        language_code="si",
        speech_model=aai.SpeechModel.nano
    )
    
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_data, config)
    
    if transcript.status == aai.TranscriptStatus.completed:
        socketio.emit('transcript', {'text': transcript.text})
        asyncio.run(analyze_transcript(transcript.text))

@socketio.on('toggle_transcription')
def handle_toggle_transcription(mode=TranscriptionMode.REALTIME.value):
    global transcriber, session_id, is_active, current_mode
    
    # Update the current mode
    current_mode = TranscriptionMode(mode)
    
    with transcriber_lock:
        if is_active:
            # Stop current transcription
            is_active = False
            if current_mode == TranscriptionMode.REALTIME and transcriber:
                transcriber.close()
                transcriber = None
                session_id = None
        else:
            is_active = True
            if current_mode == TranscriptionMode.REALTIME:
                print("Starting realtime transcriber session")
                threading.Thread(target=transcribe_real_time).start()
            else:
                print("Starting async transcriber session")
                threading.Thread(target=record_and_transcribe_async).start()

@app.route('/')
def index():
    return render_template('index.html', modes=[mode.value for mode in TranscriptionMode])

if __name__ == '__main__':
    socketio.run(app, debug=True)
