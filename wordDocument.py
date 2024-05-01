from docxtpl import DocxTemplate
from pathlib import Path
import sys
import os
import platform
from datetime import datetime
import base64
from template import base64Template
import io
from docx import Document
from jinja2 import Environment

class DocumentProcessor:
    def __init__(self, templatePath="MMCPSTemplate.docx"):
        self.sections = [
            "Overall Summary",
            "Topics Discussed",
            "Topic",
            "Action Items",
            "To be Discussed"
        ]
        self.templatePath = templatePath


    def splitMeetingNotes(self, notes: str) -> dict:
        try:
            parsedData = {}
            for idx, section in enumerate(self.sections):
                if section == "Topic":
                    continue

                startIdx = notes.find(section + ":")
                endIdx = notes.find(self.sections[idx + 1] + ":") if idx + 1 < len(self.sections) else None

                if startIdx == -1:
                    raise ValueError(f"Section '{section}' not found in the notes.")
                
                parsedData[section] = notes[startIdx + len(section) + 1:endIdx].strip()

            topicsStartIdx = notes.find("Topic:")
            topicsEndIdx = parsedData.get("Action Items") and notes.find("Action Items:") or len(notes)
            topicsSection = notes[topicsStartIdx:topicsEndIdx].strip()

            topicEntries = topicsSection.split("Topic:")
            parsedData["Topic"] = []

            for topic in topicEntries:
                topicContent = topic.strip()
                if not topicContent:
                    continue
                
                topicName, topicDetail = topicContent.split(":\n", 1)
                parsedData["Topic"].append({
                    "name": topicName,
                    "content": topicDetail
                })

            return parsedData
        except Exception as e:
            print(f"Error while parsing meeting notes: {e}")
            return None


    def getDesktopPath(self):
        systemName = platform.system()
        if systemName == "Windows":
            return os.path.join(os.environ['USERPROFILE'], 'Desktop')
        elif systemName == "Darwin" or systemName == "Linux":
            return os.path.join(os.path.expanduser('~'), 'Desktop')
        else:
            return os.path.expanduser("~")
        

    def generateContext(self, overallSummary, topics, discussion, actionItems, furtherDicussion , documentName, room, attendees):
        try:
            now = datetime.now()
            day_name = now.strftime("%A")
            day = now.day
            month_name = now.strftime("%B")
            year = now.year
            formattedDate = f"{day_name}, {self.ordinal(day)} {month_name} {year}"

            context = {
                "minutes": documentName,
                "room": room,
                "date": formattedDate,
                "attendees": attendees,
                "topics": topics,
                "summary": overallSummary,
                "topicsDiscussion": discussion,
                "actionItems": actionItems,
                "furtherDiscussion": furtherDicussion
            }

            return context
        except Exception as e:
            print(f"Error while generating context: {e}")
            return None


    def saveDoc(self, context, fileName, savePath):
        try:
            # Base template decoding and document rendering remains unchanged
            decodedContent = base64.b64decode(base64Template)
            byteStream = io.BytesIO(decodedContent)
            doc = DocxTemplate(byteStream)
            doc.render(context)
            
            # Determine the file name
            if not fileName:
                fileName = "Meeting Minutes.docx"
            else:
                fileName += ".docx" if not fileName.endswith(".docx") else ""
            
            saveFilePath = os.path.join(savePath, fileName)
            
            doc.save(saveFilePath)
            
        except FileNotFoundError:
            print("Template file not found.")
        except Exception as e:
            print(f"Error while saving document: {e}")

    def saveTranscript(self, text, fileName, savePath):
        try:
            # Determine the file name
            if not fileName:
                fileName = "Meeting_Transcript.txt"
            else:
                fileName += ".txt" if not fileName.endswith(".txt") else ""

            saveFilePath = os.path.join(savePath, fileName)

            with open(saveFilePath, "w") as f:
                f.write(text)

        except FileNotFoundError:
            print("File path not found.")
        except Exception as e:
            print(f"Error while saving transcript: {e}")



    def ordinal(self, n):
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        return str(n) + suffix

    def resourcePath(self, relativePath):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relativePath)



if __name__ == "__main__":
    processor = DocumentProcessor()

    with open("exampleFormattedMeeting.txt", "r") as f:
        notes = f.read()

    parsedData = processor.splitMeetingNotes(notes=notes)
    context = processor.generateContext("test", "test", "test", "Test", "Test", "Test Meeting", "Zac's Room", "- Zachary\t- Lisa\t- Anamaria\t- Arno Liebregts\n- Maddy Liberegts\t- Taylor Liebregts")
    processor.saveDoc(context, "testOutput", "C:/Users/Zac/OneDrive/Desktop")



