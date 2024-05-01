from audioRecorder import *
from userInterface import *
from wordDocument import *

openai.api_key = ""

GUI = App()
GUI.protocol("WM_DELETE_WINDOW", GUI.onClosing)
GUI.mainloop()

## python -m PyInstaller --onefile --add-data="logo.png;." --add-data="C:/Users/Zac/OneDrive/Desktop/CurityAI/Meeting Minute/icon.ico;." --icon="C:/Users/Zac/OneDrive/Desktop/CurityAI/Meeting Minute/icon.ico" Application.py --windowed
