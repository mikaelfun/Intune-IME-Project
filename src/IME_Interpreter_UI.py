'''
Developing plan:

install/availability deadline
reboot behavior and log continuity
restart grace period
dependency with auto install                done
dependency with detect only
precedency
assignment filter
UI scroll bar
UI with fonts style

WPJ and user context payload skip           done
Display DO and CDN download timeout         partly done
Display Install time out                    done
Remember last opened directory              done
Display download URL

'''
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from Preprocessing import *
from Win32_log_processing import *

class Root(Tk):
    def __init__(self):
        super(Root, self).__init__()
        self.title("IME log Interpreter  V2.0")
        self.minsize(640, 400)

        self.labelFrame = ttk.LabelFrame(self, text="Open File")
        self.labelFrame.grid(column=0, row=0, padx=5, pady=5)

        #self.topleftFrame = ttk.Frame(self.labelFrame, height=12, width=152,)
        #self.topleftFrame.grid(column=0, row=0, padx=20, pady=20,  sticky=NW)

        self.logFrame = ttk.LabelFrame(self.labelFrame, text="Converted Log", height=35, width=152,)
        self.logFrame.grid(column=0, row=2, padx=0, pady=10)

        self.ActionFrame = ttk.LabelFrame(self, text="Actions")
        self.ActionFrame.grid(column=1, row=0, padx=5, pady=5, sticky=NS)

        self.label = ttk.Label(self.labelFrame, text="")
        self.label.grid(column=0, row=1, sticky=W)

        self.button()
        self.button_analyze()
        self.button_clear()
        self.text_output()

        self.filename = ""

        self.scrollbar = ttk.Scrollbar(self.logFrame, orient='vertical', command=self.text_output.yview)
        self.scrollbar.grid(row=0, column=1, sticky=NS)
        self.text_output['yscrollcommand'] = self.scrollbar.set

    def button(self):
        self.button = ttk.Button(self.labelFrame, text="Browse IME log File", command=self.fileDialog)
        self.button.grid(column=0, row=0, sticky=NW)

    def button_analyze(self):
        self.button_analyze = ttk.Button(self.ActionFrame, text="Start Analyzing", command=lambda: self.start_analyze(self.filename))
        self.button_analyze.grid(column=0, row=0,sticky=NE)

    def button_clear(self):
        self.button_clear = ttk.Button(self.ActionFrame, text="Clear Result", command=self.clear_result)
        self.button_clear.grid(column=0, row=1 ,sticky=NE)

    def text_output(self):
        # Create text widget and specify size.
        self.text_output = Text(self.logFrame, height=35, width=152, font=('Times New Roman',12))
        self.text_output.grid(column=0, row=0)

    def clear_result(self):
        self.text_output.delete("1.0","end")

    def fileDialog(self):
        if not self.filename:
            self.filename = filedialog.askopenfilename(initialdir="/", title="Select A File",
                                                   filetype=(("IME log files", "*.log"), ("all files", "*.*")))
        else:
            self.filename = filedialog.askopenfilename(initialdir= self.filename, title="Select A File",
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

    #log = IMELog("G:\\Storage\\Document\\Projects\\2021 IME Interpreter Project\\Test Cases\\DO fail CDN mode download success.log")
    #log = IMELog("G:\\Storage\\Document\\Projects\\2021 IME Interpreter Project\\Test Cases\\Incomplete Application Poller without stop1.log")
    #log = IMELog("G:\\Storage\\Document\\Projects\\2021 IME Interpreter Project\\Test Cases\\Incomplete Application Poller without stop2.log")
    #log = IMELog("G:\\Storage\\Document\\Projects\\2021 IME Interpreter Project\\Test Cases\\Device Setup with restart 20 apps log only 3 showed.log")
    #log = IMELog("G:\\Storage\\Document\\Projects\\2021 IME Interpreter Project\\Test Cases\\Extended requirement script not met.log")


    #log = IMELog("C:\\Users\\kufang\\OneDrive - Microsoft\\Projects\\IME project\\test case logs\\15 apps filtered but only 3, Missing device setup apps.log")
    #log = IMELog("C:\\Users\\kufang\\OneDrive - Microsoft\\Projects\\IME project\\test case logs\\Device setup softreboot.log")
    #log = IMELog("C:\\Users\\kufang\\OneDrive - Microsoft\\Projects\\IME project\\test case logs\\IntuneforceHardreboot DeviceRestartBehavior 3.log")
    #log = IMELog("C:\\Users\\kufang\\OneDrive - Microsoft\\Projects\\IME project\\test case logs\\Intuneforcehardreboot with restart grace period, after restart.log")
    #log = IMELog("C:\\Users\\kufang\\OneDrive - Microsoft\\Projects\\IME project\\test case logs\\Incomplete Application Poller without stop1.log")
    #log = IMELog("C:\\Users\\kufang\\OneDrive - Microsoft\\Projects\\IME project\\test case logs\\IntuneManagementExtension (7) not working.log")
    #log = IMELog("D:\\kufang\\IME interpreter test log\\IntuneManagementExtension Dependency issue.log")
    #print(log.generate_win32_app_log())
