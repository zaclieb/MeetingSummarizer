import tkinter
from tkinter import messagebox
import tkinter.messagebox
import customtkinter
from tkinter import filedialog
import os
from PIL import Image, ImageOps
from audioRecorder import *
from wordDocument import *
from openAI import *
import threading

employees = [ "Laurie Bechelli", "Lisa Liebregts", "Tim Maxwell", "Kylie Mawson", "Grace Allen",
    "Tina Zdraveski", "Barb Stojkovski", "Maria Salpietro", "Nataliya Liakishev",
    "Cath Maybury", "Marita Gomes", "Amy Pethick", "Anne Carosin", "Rose Connell",
    "Paige Lanham", "Alba Roussety", "Kelly Sangiacomo", "Libby Dalglish", "Sara Blair",
    "Kali Koncurat", "Sonja Robertson", "Jan Nottle", "Karen Noone", "Chloe Phiri",
    "Maureen Hunt", "Lauren Di Girolami", "Natasha Strecker", "Sharon Wills", "Gabby Previti",
    "Helen Adamos", "Deb Harris", "Dee Hube", "Angela Cox", "Lisa Italiano", "Anna Rector",
    "Sharon Loncar", "Stella Antoine-Prosper", "Marc Zaffino", "Ywa Hay Byit", "Jordan Fuller",
    "Alli Glenister", "Marina Thompson", "Jodie Smith", "Maria Beaney", "Julie Cockman",
    "Jo Rodgers", "Helen Jerkovich", "Owen Miller", "Marie Gray", "Sam Boyce",
    "Kristy Mouchemore", "Steve Duncan", "Lisa Mueller", "Kash Raghwani", "Steve Tucker",
    "Sylvia Iggleden", "Kath Kilgallon", "Barbara Burton", "Jane Coniglio", "Frank Campione",
    "James Sandon"]
sortedEmployees = sorted(employees, key=lambda x: x.lower())
microphones = listMicrophoneInputs()

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Meeting Minute Summarizer")
        screenWidth = self.winfo_screenwidth()
        screenHeight = self.winfo_screenheight()
        self.geometry(f"{screenWidth}x{screenHeight}")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        logoPath = resourcePath('logo.png')
        logoIcon = resourcePath('icon.ico')
        self.angle = 0
        self.spinning = False
        self.spinningTaskId = None
        self.logoRawImage = Image.open(logoPath)
        self.iconbitmap(logoIcon)  
        self.logoImage = customtkinter.CTkImage(self.logoRawImage, size=(50, 50))

        self.navFrame = customtkinter.CTkFrame(self, corner_radius=0, width=2000)
        self.navFrame.grid(row=0, column=0, sticky="nsew")
        self.navFrame.grid_rowconfigure(4, weight=1)

        self.navLabel = customtkinter.CTkLabel(self.navFrame, 
                                          text="  ZacLIEB  ", 
                                          font=customtkinter.CTkFont(size=30, weight="bold"),
                                          image=self.logoImage, 
                                          compound="left")
        self.navLabel.grid(row=0, column=0, padx=(0,20), pady=20)
        self.navLabel.grid(row=0, column=0, padx=(10,20), pady=20)
        # self.startSpinningLogo()
        buttons = [
            ("  Home", "home", self.homeButtonEvent),
            ("  Summary", "summary", self.summaryButtonEvent)
            # ("  Settings", "settings", self.frame3ButtonEvent),
        ]

        for i, (text, name, command) in enumerate(buttons):
            btn = customtkinter.CTkButton(
                self.navFrame, text=text, corner_radius=0, height=40, font=customtkinter.CTkFont(size=17, weight="bold"),
                fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                anchor="ew", command=command
            )
            btn.grid(row=i + 1, column=0, sticky="ew")

        self.homeFrame = HomeFrame(self)
        self.summaryFrame = SummaryFrame(self)
        self.frame3 = ThirdFrame(self)
        self.selectFrameByName("home")
        self.homeFrame.setSummaryFrame(self.summaryFrame)
        self.summaryFrame.setHomeFrame(self.homeFrame)

    def selectFrameByName(self, name):
        for frame in [self.homeFrame, self.summaryFrame, self.frame3]:
            if frame.grid_info():
                frame.grid_forget()
        if name == "home":
            self.homeFrame.grid(row=0, column=1, sticky="nsew")
        elif name == "summary":
            self.summaryFrame.grid(row=0, column=1, sticky="nsew")
        elif name == "settings":
            self.frame3.grid(row=0, column=1, sticky="nsew")

    def homeButtonEvent(self):
        self.selectFrameByName("home")

    def summaryButtonEvent(self):
        self.selectFrameByName("summary")

    def frame3ButtonEvent(self):
        self.selectFrameByName("settings")

    def onClosing(self):
        print("Closing application...")
        self.homeFrame.stopAudioRecording()

        if hasattr(self.homeFrame.recorder, 'recordingThread') and self.homeFrame.recorder.recordingThread.is_alive():
            self.homeFrame.recorder.recordingThread.join()

        self.homeFrame.recorder.close()
        self.destroy()

    def startSpinningLogo(self):
        self.spinning = True
        self.angle += 10
        rotated_image = self.logoRawImage.rotate(self.angle)
        self.logoImage = customtkinter.CTkImage(rotated_image, size=(50, 50))
        self.navLabel.configure(image=self.logoImage)
        if self.spinning:
            self.spinningTaskId = self.after(50, self.startSpinningLogo)  

    def stopSpinningLogo(self):
        self.spinning = False
        if self.spinningTaskId:  
            self.after_cancel(self.spinningTaskId)  
            self.spinningTaskId = None
        self.logoImage = customtkinter.CTkImage(self.logoRawImage, size=(50, 50))
        self.navLabel.configure(image=self.logoImage)


class HomeFrame(customtkinter.CTkFrame):
    def __init__(self, parent):
        self.recorder = AudioRecorder()
        self.openAI = OpenAIResponse()
        self.summaryFrame = None
        super().__init__(parent, corner_radius=0, fg_color="transparent")

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self.transcriptTitle = customtkinter.CTkLabel(self, text="Transcript", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.transcriptTitle.grid(row=0, column=0, columnspan = 3, padx=20, pady=(20, 5), sticky="w")

        self.textBox = customtkinter.CTkTextbox(self, width=100, height=400)
        self.textBox.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="nsew")


        ##-----------Side Menu-----------------##
        self.sideMenu = customtkinter.CTkFrame(self, width=400)  
        self.sideMenu.grid(row=0, column=3, padx=(0 ,20), pady=(20, 20), sticky="nsew", rowspan=2)  
        self.sideMenu.grid_columnconfigure(0, weight=1)

        self.collectFile = customtkinter.CTkButton(self.sideMenu, command=self.displayFileContent, text="File")
        self.collectFile.grid(row=2, column=0, pady=(20, 0), padx=20, sticky="ew")

        self.sendAPI = customtkinter.CTkButton(self.sideMenu, command=self.runPrompts, text="            Summarise            ")
        self.sendAPI.grid(row=3, column=0, pady=(20, 0), padx=20, sticky="ew")

        self.startButton = customtkinter.CTkButton(self.sideMenu, text="Start Recording", fg_color="green", command=self.startAudioRecording)
        self.startButton.grid(row=4, column=0, padx=20, pady=(20, 0), sticky="ew")

        self.endButton = customtkinter.CTkButton(self.sideMenu, text="End Recording", fg_color="red",  command=self.stopAudioRecording)
        self.endButton.grid(row=5, column=0, padx=20, pady=(20, 0), sticky="ew")

        self.microphone = customtkinter.CTkOptionMenu(self.sideMenu, values=microphones, command=self.updateMicrophoneIndex)
        self.microphone.grid(row=6, column=0, padx=20, pady=(20, 0), sticky="ew")

        # self.recordingStatus = customtkinter.CTkProgressBar(self.sideMenu)
        # self.recordingStatus.grid(row=7, column=0, padx=20, pady=(20, 0), sticky="ew")
        # self.recordingStatus.configure(mode="indeterminate")
        # self.recordingStatus.set(0)

    def displayFileContent(self):
        filePath = filedialog.askopenfilename()
        if filePath:
            _, ext = os.path.splitext(filePath)
            if ext.lower() != '.txt':
                tkinter.messagebox.showerror('Invalid file type', 'Please select a text file (.txt)')
                return

            try:
                with open(filePath, 'r') as file:
                    data = file.read()
                self.textBox.delete("1.0", tkinter.END)
                self.textBox.insert("1.0", data)
            except FileNotFoundError:
                tkinter.messagebox.showerror('File not found', 'The selected file does not exist')
            except PermissionError:
                tkinter.messagebox.showerror('Permission error', 'Permission denied')
            except Exception as e:
                tkinter.messagebox.showerror('Unknown Error', f'An unknown error occurred: {str(e)}')
        else:
            print('No file selected')

    def runPrompts(self):
        def threadedFunction():
            textContent = self.textBox.get("1.0", "end-1c")

            if len(textContent) <= 1000:
                result = messagebox.askyesno("Confirmation", "The content is less than or equal to 1000 characters. Are you sure you want to continue?")
                
                if result: 
                    response = self.openAI.runPrompts(textContent)
                else:  
                    return
            else:
                response = self.openAI.runPrompts(textContent)

            self.after(0, postPrompts, response)

        def postPrompts(response):
            self.master.stopSpinningLogo()  # Stop spinning the logo
            if self.summaryFrame and response:
                print(response)
                messagebox.showinfo("Confirmation", "The Meeting Summary has been generated.")
                self.summaryFrame.populateSummary(response)
            else: 
                print("OpenAI Failed")
                messagebox.showinfo("Confirmation", "The Meeting Summary failed to be generated. Please Contact Zac.")
                self.summaryFrame.populateSummary(response)

        self.master.startSpinningLogo()  # Start spinning the logo
        threading.Thread(target=threadedFunction).start()



    def startAudioRecording(self):
        result = messagebox.askyesno("Start Audio Recording", "Are you sure you want to start audio recording?")
        
        if result:
            print("Starting audio recording...")
            self.collectFile.configure(state="disabled")
            self.sendAPI.configure(state="disabled")
            self.startButton.configure(state="disabled")

            self.recorder.startRecording()
            self.updateTextBox()
            self.master.startSpinningLogo()
        else:
            print("User cancelled audio recording.")

    def stopAudioRecording(self):
        self.collectFile.configure(state="normal")
        self.sendAPI.configure(state="normal")
        self.startButton.configure(state="normal")
        
        self.recorder.stopRecording()
        self.master.stopSpinningLogo()

    def updateMicrophoneIndex(self, selectedMicrophone):
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            deviceInfo = p.get_device_info_by_index(i)
            if deviceInfo["name"] == selectedMicrophone:
                self.recorder.setMicrophone(i)
                break
        p.terminate()

    def updateTextBox(self):
        while not self.recorder.transcriptionQueue.empty():
            transcribedText = self.recorder.transcriptionQueue.get()
            self.textBox.insert(tkinter.END, transcribedText)  
        
        self.after(1000, self.updateTextBox)

    def setSummaryFrame(self, frame):
        self.summaryFrame = frame

    def getTranscript(self):
        return self.textBox.get("1.0", "end").strip() 



class SummaryFrame(customtkinter.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.documentSaver = DocumentProcessor()
        self.homeFrame = None

        # Configure Grid
        for i in [1, 3, 5]:
            self.grid_rowconfigure(i, weight=1)  # Equal weights for the text boxes
        self.grid_columnconfigure(0, weight=1)  # For column 1
        self.grid_columnconfigure(1, weight=1)

        self.summaryText = customtkinter.CTkScrollableFrame(self, width=210, height=800, fg_color="transparent", bg_color="transparent")
        self.summaryText.grid(row=0, column=0, rowspan=10, columnspan=2, padx=(15, 20), pady=(20, 20), sticky="nsew")  
        self.summaryText.grid_columnconfigure(1, weight=1)

        # Text Box 1
        self.overallSummaryTitle = customtkinter.CTkLabel(
            self.summaryText, text="Overall Summary", 
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.overallSummaryTitle.grid(row=0, column=0, padx=0, pady=(5, 10), sticky="w")
        self.overallSummaryText = customtkinter.CTkTextbox(self.summaryText, width=100, height=150)
        self.overallSummaryText.grid(row=1, column=0, columnspan=2, padx=0, pady=(0, 10), sticky="nsew")

        # Text Box 2
        self.topicsTitle = customtkinter.CTkLabel(
            self.summaryText, text="Topics Discussed", 
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.topicsTitle.grid(row=2, column=0, padx=0, pady=(5, 10), sticky="w")
        self.topicsText = customtkinter.CTkTextbox(self.summaryText, width=100, height=150)
        self.topicsText.grid(row=3, column=0, padx=0, columnspan=2, pady=(0, 10), sticky="nsew")

        # Text Box 3
        self.discussionTitle = customtkinter.CTkLabel(
            self.summaryText, text="Discussion", 
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.discussionTitle.grid(row=4, column=0, padx=0, pady=(5, 10), sticky="w")
        self.discussionText = customtkinter.CTkTextbox(self.summaryText, width=100, height=500)
        self.discussionText.grid(row=5, column=0, padx=0, pady=(0, 10), sticky="nsew", columnspan=2)

        # Text Box 4
        self.actionItemsTitle = customtkinter.CTkLabel(
            self.summaryText, text="Action Items", 
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.actionItemsTitle.grid(row=6, column=0, padx=0, pady=(5, 10), sticky="w")
        self.actionItemsText = customtkinter.CTkTextbox(self.summaryText, width=100, height=150)
        self.actionItemsText.grid(row=7, column=0, padx=0, pady=(0, 10), sticky="nsew", columnspan=2)

        # Text Box 5
        self.furtherDiscussionTitle = customtkinter.CTkLabel(
            self.summaryText, text="Further Discussion", 
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.furtherDiscussionTitle.grid(row=8, column=0, padx=0, pady=(5, 10), sticky="w")
        self.furtherDiscussionText = customtkinter.CTkTextbox(self.summaryText, width=100, height=150)
        self.furtherDiscussionText.grid(row=9, column=0, padx=0, pady=(0, 10), sticky="nsew", columnspan=2)


        #---------Meeting Information--------##
        self.meetingInformation = customtkinter.CTkScrollableFrame(self, width=210, height=800)
        self.meetingInformation.grid(row=0, column=2, rowspan=10, padx=(0, 20), pady=(20, 20), sticky="nsew")  
        self.meetingInformation.grid_columnconfigure(1, weight=1)
        
        self.employeeCheckBox = {employee: tkinter.BooleanVar() for employee in sortedEmployees}  # Assuming sortedEmployees is defined somewhere

        # # Filename Label
        # self.filenameLabel = customtkinter.CTkLabel(self.meetingInformation, text="File Name", font=customtkinter.CTkFont(size=20, weight="bold"))
        # self.filenameLabel.grid(row=0, column=0, columnspan=2, pady=(10, 0), padx=5, sticky="w")
        # self.filenameLabel.is_permanent = True
        
        # # Filename Field
        # self.filename = customtkinter.CTkEntry(self.meetingInformation, placeholder_text="File Name")
        # self.filename.grid(row=1, column=0, columnspan=2, pady=(10, 0), padx=5, sticky="we")

        # Save Button
        self.save = customtkinter.CTkButton(self.meetingInformation, command=self.saveWordDoc, text="Save", fg_color="green")
        self.save.grid(row=2, column=0, columnspan=2, pady=(10, 0), padx=5, sticky="we")

        # Room Label
        self.roomLabel = customtkinter.CTkLabel(self.meetingInformation, text="Room", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.roomLabel.grid(row=3, column=0, columnspan=2, pady=(10, 0), padx=5, sticky="w")
        self.roomLabel.is_permanent = True
        
        # Room Field
        self.roomLocation = customtkinter.CTkEntry(self.meetingInformation, placeholder_text="Room")
        self.roomLocation.grid(row=4, column=0, columnspan=2, pady=(10, 0), padx=5, sticky="we")

        # Search Label
        self.searchLabel = customtkinter.CTkLabel(self.meetingInformation, text="Attendees", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.searchLabel.grid(row=5, column=0, columnspan=2, pady=(10, 0), padx=5, sticky="w")
        self.searchLabel.is_permanent = True
        
        # Employee Search Label
        self.searchLabel = customtkinter.CTkLabel(self.meetingInformation, text="Employees", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.searchLabel.grid(row=6, column=0, columnspan=2, pady=(10, 0), padx=5, sticky="w")

        # Add Attendee Button
        self.extraAttendee = customtkinter.CTkButton(self.meetingInformation, command=self.addAttendee, text="Add Attendee")
        self.extraAttendee.grid(row=7, column=0, columnspan=2, pady=(10, 0), padx=5, sticky="we")
        
        # Employee Group Field
        self.employeeGroups = customtkinter.CTkOptionMenu(self.meetingInformation, values=["Staff", "PNF"])
        self.employeeGroups.grid(row=8, column=0, columnspan=2, pady=(10, 0), padx=5, sticky="we")

        # Employee Search Box
        self.searchVar = tkinter.StringVar()
        self.searchVar.trace("w", self.searchEmployees)
        self.searchBar = customtkinter.CTkEntry(self.meetingInformation, placeholder_text="Search Employees", textvariable=self.searchVar)
        self.searchBar.grid(row=9, column=0, columnspan=2, pady=(20, 20), padx=5, sticky="we")
        self.searchEmployees()
        
        
    def searchEmployees(self, *args):
        for widget in self.meetingInformation.winfo_children():
            if (isinstance(widget, customtkinter.CTkCheckBox) or isinstance(widget, customtkinter.CTkLabel)) and not getattr(widget, 'is_permanent', False):
                widget.destroy()


        search_term = self.searchVar.get().lower()
        match = [employee for employee in sortedEmployees if search_term in employee.lower()]
        
        rowCounter = 10 

        for employee in match:
            checkbox = customtkinter.CTkCheckBox(
                master=self.meetingInformation, 
                text="    " + employee,  # Added 4 spaces
                variable=self.employeeCheckBox[employee]
            )
            checkbox.grid(row=rowCounter, column=0, padx=(5,5), pady=(0, 20), sticky="w")
            rowCounter += 1

    def addAttendee(self):
        dialog = customtkinter.CTkInputDialog(text="Enter Attendee Name:", title="Extra Attendee")
        attendeeName = dialog.get_input()
        if attendeeName:
            global employees, sortedEmployees
            employees.append(attendeeName)
            sortedEmployees = sorted(employees, key=lambda x: x.lower())
            self.employeeCheckBox[attendeeName] = tkinter.BooleanVar(value=True) 
            self.searchEmployees()
        
    def getSelectedAttendees(self):
        selectedAttendees = [employee for employee, var in self.employeeCheckBox.items() if var.get()]
        return selectedAttendees

    def saveWordDoc(self):
        initialDIR = "C:/"  
        fileTypes = [("Word documents", "*.docx"), ("All files", "*.*")]
        fullSavePath = tkinter.filedialog.asksaveasfilename(initialdir=initialDIR, title="Select Save Location", filetypes=fileTypes, defaultextension=".docx")

        filename = os.path.splitext(os.path.basename(fullSavePath))[0]
        print(filename)

        savePath = os.path.dirname(fullSavePath)
        print(savePath)


        ## Get Fields ##
        attendees = self.getSelectedAttendees()
        formattedAttendees = "\n".join(f"- {name}" for name in attendees)
        room = self.roomLocation.get()
        overallSummary = self.overallSummaryText.get("1.0", "end").strip()
        topics = self.topicsText.get("1.0", "end").strip()
        discussion = self.discussionText.get("1.0", "end").strip()
        actionItems = self.actionItemsText.get("1.0", "end").strip()
        furtherDiscussion = self.furtherDiscussionText.get("1.0", "end").strip()

        ## Double Check ##
        emptyFields = []
        if not attendees: emptyFields.append("Attendees")
        if not filename: emptyFields.append("Filename")
        if not room: emptyFields.append("Room")
        if not overallSummary: emptyFields.append("Overall Summary")
        if not topics: emptyFields.append("Topics")
        if not discussion: emptyFields.append("Discussion")
        if not actionItems: emptyFields.append("Action Items")
        if not furtherDiscussion: emptyFields.append("Further Discussion")

        if emptyFields:
            empty_fields_str = "\n".join(emptyFields)
            proceed = messagebox.askyesno("Empty Fields Detected", f"The following fields are empty:\n{empty_fields_str}\n Do you want to proceed?")
            if not proceed:
                return

        try:
            ## Save Meeting Summary Word Doc File ##
            context = self.documentSaver.generateContext(overallSummary, topics, discussion, actionItems, furtherDiscussion, filename, room, formattedAttendees)
            self.documentSaver.saveDoc(context, filename, savePath)

            ## Save Trancript Text File ##
            transcript = self.homeFrame.getTranscript()
            self.documentSaver.saveTranscript(transcript, filename, savePath)

            # Notify the user of the successful save
            messagebox.showinfo("Success", "Files have been saved successfully!")

        except Exception as e:
            # If an error occurs, show it in a message box
            messagebox.showerror("Error", f"An error occurred while saving the files:\n{str(e)}")


    def populateSummary(self, response):
        if response:
            print("Received")

            ## Overall Summary ##
            self.overallSummaryText.delete("1.0", tkinter.END)
            self.overallSummaryText.insert("1.0", response['overallSummary'])

            ## Topics Discussed ##
            self.topicsText.delete("1.0", tkinter.END)
            topics = ', '.join([topic['topic'] for topic in response['dicussion']])
            self.topicsText.insert("1.0", topics)

            ## Discussion ##
            self.discussionText.delete("1.0", tkinter.END)
            for topic in response['dicussion']:
                self.discussionText.insert(tkinter.END, topic['topic'] + ":\n")
                for point in topic['discussion']:
                    self.discussionText.insert(tkinter.END, "- " + point + "\n")
                self.discussionText.insert(tkinter.END, "\n")

            ## Action Items ##
            self.actionItemsText.delete("1.0", tkinter.END)
            for item in response['actionItems']:
                self.actionItemsText.insert(tkinter.END, "- " + item + "\n")

            ## Further Discussion ##
            self.furtherDiscussionText.delete("1.0", tkinter.END)
            for topic in response['furtherDiscussion']:
                self.furtherDiscussionText.insert(tkinter.END, "- " + topic + "\n")

    def setHomeFrame(self, frame):
        self.homeFrame = frame



class ThirdFrame(customtkinter.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, corner_radius=0, fg_color="transparent")

        # Configure Grid for centering
        self.grid_rowconfigure(0, weight=1)  # centering vertically
        self.grid_rowconfigure(3, weight=1)  # Add extra row for centering
        self.grid_columnconfigure(0, weight=1)  # centering horizontally
        self.grid_columnconfigure(2, weight=1)

        # Create the image widget
        logoPath = resourcePath('logo.png')
        self.logoImage = customtkinter.CTkImage(Image.open(logoPath), size=(300, 300))
        
        # Create a label or some other container to hold the image
        self.image_container = customtkinter.CTkLabel(self, 
                                          text="  CurityAI  ", 
                                          font=customtkinter.CTkFont(size=200, weight="bold"),
                                          image=self.logoImage, 
                                          compound="left")  
        self.image_container.grid(row=1, column=1)
        

def resourcePath(relativePath):
    try:
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath(".")
    return os.path.join(basePath, relativePath)


if __name__ == "__main__":
    openai.api_key = ""
    app = App()
    app.mainloop()
