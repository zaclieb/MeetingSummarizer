import pyaudio
import wave
import threading
import time
from queue import Queue
import os
import openai
import sys
import logging
import requests

desktop = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
log_file_path = os.path.join(desktop, 'app.log')
#logging.basicConfig(filename=log_file_path, level=logging.DEBUG)

class AudioRecorder:
    def __init__(self):
        self.microphoneIndex = -1
        self.chunk = 1024
        self.sampleFormat = pyaudio.paInt16
        self.channels = 1
        self.fs = 44100
        self.frames = []
        self.chunkDuration = 30
        self.chunkFrameCount = int(self.fs * self.chunkDuration * self.channels)
        self.chunkCounter = 0
        self.p = pyaudio.PyAudio()
        self.isRecording = False
        self.transcriptionQueue = Queue()
        self.modelLock = threading.Lock()

    def setMicrophone(self, index):
        self.microphoneIndex = index

    def startRecording(self):
        if self.microphoneIndex == -1:
            print("No microphone selected. Using default microphone.")

        self.isRecording = True
        self.recordingThread = threading.Thread(target=self.recordAudio)
        self.recordingThread.start()

    def recordAudio(self):
        try:
            self.stream = self.p.open(
                format=self.sampleFormat,
                channels=self.channels,
                rate=self.fs,
                frames_per_buffer=self.chunk,
                input=True,
                input_device_index=self.microphoneIndex
            )
        except IOError as e:
            #logging.error(f"Could not start audio stream: {e}")
            return
        
        print("Recording started...")
        self.frames = []
        
        while self.isRecording:
            self.recordChunk()

        try:
            self.stream.stop_stream()
            self.stream.close()
        except IOError as e:
            pass
            logging.error(f"Could not stop audio stream: {e}")
        
        if self.frames:
            self.saveChunk()

    def stopRecording(self):
        self.isRecording = False
        time.sleep(0.5)
        print("Recording finished...")

    def close(self):
        self.p.terminate()

    def recordChunk(self):
        data = self.stream.read(self.chunk, exception_on_overflow=False)
        self.frames.append(data)

        if len(self.frames) * self.chunk >= self.chunkFrameCount:
            self.saveChunk()

    def saveChunk(self):
        try:
            if getattr(sys, 'frozen', False):
                applicationPath = sys._MEIPASS
            else:
                applicationPath = os.path.dirname(os.path.abspath(__file__))

            audioDirectory = os.path.join(applicationPath, 'Audio')
            if not os.path.exists(audioDirectory):
                os.makedirs(audioDirectory)
            
            wavFileName = f"chunk_{self.chunkCounter}.wav"
            wavFilePath = os.path.join(audioDirectory, wavFileName)
            #logging.error(wavFilePath)
            
            with wave.open(wavFilePath, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.p.get_sample_size(self.sampleFormat))
                wf.setframerate(self.fs)
                wf.writeframes(b''.join(self.frames))

            print(f"Saved {wavFileName}")

            threading.Thread(target=self.transcribeAudio2, args=(wavFilePath,)).start()

            self.frames = []
            self.chunkCounter += 1
        except Exception as e:
            pass
            #logging.error(f"Error in saveChunk: {e}")

    def transcribeAudio(self, filename):
        with self.modelLock:
            try:
                with open(filename, "rb") as audioFile:
                    transcript = openai.Audio.translate("whisper-1", audioFile)
                    resultText = transcript['text']
                
                self.transcriptionQueue.put(resultText)
                print(resultText)

                try:
                    os.remove(filename)
                    print(f"Deleted {filename}")
                except Exception as e:
                    print(f"Error deleting {filename}: {e}")
            except Exception as e:
                print(f"Error in transcribeAudio: {e}")

    def transcribeAudio2(self, filename):
        url = 'https://whisper.zaclieb.com/transcribe'
        files = {'file': open(filename, 'rb')}
        try:
            response = requests.post(url, files=files)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error transcribing audio: {e}")
            return None
        finally:
            files['file'].close()

def listMicrophoneInputs():
    p = pyaudio.PyAudio()
    microphones = []
    
    try:
        for i in range(p.get_device_count()):
            deviceInfo = p.get_device_info_by_index(i)
            
            if deviceInfo["maxInputChannels"] > 0:
                microphones.append(deviceInfo["name"])
    except Exception as e:
        print(f"Error listing microphones: {e}")
    finally:
        p.terminate()
    
    return microphones



def transcribeAudio2(filename):
    url = 'https://whisper.zaclieb.com/transcribe'
    files = {'file': open(filename, 'rb')}
    try:
        response = requests.post(url, files=files)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error transcribing audio: {e}")
        return None
    finally:
        files['file'].close()

if __name__ == "__main__":
    
    availableMics = listMicrophoneInputs()
    print("Available microphones:")
    for index, mic in enumerate(availableMics):
        print(f"{index}. {mic}")
    
    micIndex = int(input("Please select the microphone index you'd like to use: "))
    audioRecorder = AudioRecorder()
    audioRecorder.setMicrophone(micIndex)
    
    audioRecorder.startRecording()
    input("Press Enter to stop recording...\n")
    audioRecorder.stopRecording()
    audioRecorder.close()
    
    while not audioRecorder.transcriptionQueue.empty():
        transcribedText = transcribeAudio2(audioRecorder.transcriptionQueue.get())
        print(f"Transcribed text: {transcribedText}")
