# testing hardcoded

# Start by making sure the `assemblyai` package is installed.
# If not, you can install it by running the following command:
# pip install -U assemblyai
#
# Note: Some macOS users may need to use `pip3` instead of `pip`.

import assemblyai as aai

# Replace with your API key
aai.settings.api_key = "2f9a249766b24b11b6f6bee6b1537469"

# URL of the file to transcribe
#FILE_URL = "https://assembly.ai/wildfires.mp3"

# You can also transcribe a local file by passing in a file path
FILE_URL = 'audio/sinhala-sample.mp3'

# You can change the model by setting the speech_model in the transcription config
config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.nano,language_code="si")

transcriber = aai.Transcriber(config=config)
transcript = transcriber.transcribe(FILE_URL)

if transcript.status == aai.TranscriptStatus.error:
    print(transcript.error)
else:
    print(transcript.text)
