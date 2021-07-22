# break logs into lines and return list of lines as loaded logs
# IME log are mixed with multiple threads
# It is important to separate logs into each thread processing

from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from Preprocessing import *
from Win32_log_processing import *

class Root(Tk):
    def __init__(self):
        super(Root, self).__init__()
        self.title("IME log Interpreter  V1.0")
        self.minsize(640, 400)
        # self.wm_iconbitmap('icon.ico')

        # self.filename = "C:\\Users\\kufang\\Downloads\\IntuneManagementExtension-20210704-211516.log"

        self.labelFrame = ttk.LabelFrame(self, text="Open File")
        self.labelFrame.grid(column=0, row=1, padx=20, pady=20)
        self.label = ttk.Label(self.labelFrame, text="")
        self.label.grid(column=1, row=2)

        self.button()
        self.button_analyze()
        self.button_clear()
        self.text_output()

    def button(self):
        self.button = ttk.Button(self.labelFrame, text="Browse IME log File", command=self.fileDialog)
        self.button.grid(column=1, row=1)

    def button_analyze(self):
        self.button_analyze = ttk.Button(self.labelFrame, text="Start Analyzing", command=lambda: self.start_analyze(self.filename))
        self.button_analyze.grid(column=2, row=1)

    def button_clear(self):
        self.button_clear = ttk.Button(self.labelFrame, text="Clear Result", command=self.clear_result)
        self.button_clear.grid(column=2, row=2)

    def text_output(self):
        # Create text widget and specify size.
        self.text_output = Text(self.labelFrame, height=35, width=152, font=('Times New Roman',12))
        self.text_output.grid(column=1, row=3)

    def clear_result(self):
        self.text_output.delete("1.0","end")

    def fileDialog(self):
        self.filename = filedialog.askopenfilename(initialdir="/", title="Select A File",
                                                   filetype=(("IME log files", "*.log"), ("all files", "*.*")))
        self.label.configure(text="")
        self.label.configure(text=self.filename)

    def start_analyze(self, IME_log_path):
        processed_log = IMELog(IME_log_path)
        output = processed_log.generate_win32_app_log()
        self.text_output.delete("1.0","end")
        self.text_output.insert(END, output)


if __name__ == "__main__":
    root = Root()
    root.mainloop()
    #log = IMELog("C:\\test\\\ime reboot\\IntuneManagementExtension-20210713-102822.log")
    #log = IMELog("C:\\Users\\kufang\\Downloads\\Autopilot Logs from 001\\001\\Autopilot-001\\IntuneManagementExtension.log")
    #print(log.generate_win32_app_log())
    # start_process_by_log_path("C:\\Users\\kufang\\Downloads\\IntuneManagementExtension-20210704-211516.log")

