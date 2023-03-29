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
from logprocessinglibrary import *
from constructinterpretedlog import *
from imeinterpreter import *


class Root(Tk):
    def __init__(self):
        super(Root, self).__init__()
        self.title("IME log Interpreter  V3.0")
        self.minsize(640, 400)

        self.labelFrame = ttk.LabelFrame(self, text="Open File")
        self.labelFrame.grid(column=0, row=0, padx=5, pady=5)

        #self.topleftFrame = ttk.Frame(self.labelFrame, height=12, width=152,)
        #self.topleftFrame.grid(column=0, row=0, padx=20, pady=20,  sticky=NW)

        self.log_frame = ttk.LabelFrame(self.labelFrame, text="Converted Log", height=35, width=152, )
        self.log_frame.grid(column=0, row=2, padx=0, pady=10)

        self.action_frame = ttk.LabelFrame(self, text="Actions")
        self.action_frame.grid(column=1, row=0, padx=5, pady=5, sticky=NS)

        self.label = ttk.Label(self.labelFrame, text="")
        self.label.grid(column=0, row=1, sticky=W)

        self.browse_button = None

        self.browse_button_init()

        self.button_analyze = None
        self.button_analyze_init()

        self.button_clear = None
        self.button_clear_init()

        self.button_enable_full_log = False

        self.text_output = ""
        self.text_output_init()

        self.log_folder_name = ""

        self.scrollbar = ttk.Scrollbar(self.log_frame, orient='vertical', command=self.text_output.yview)
        self.scrollbar.grid(row=0, column=1, sticky=NS)
        self.text_output['yscrollcommand'] = self.scrollbar.set

    def browse_button_init(self):
        self.browse_button = ttk.Button(self.labelFrame, text="Browse IME log File", command=self.file_dialog)
        self.browse_button.grid(column=0, row=0, sticky=NW)

    def button_analyze_init(self):
        self.button_analyze = ttk.Button(self.action_frame, text="Start Analyzing", command=lambda: self.start_analyze(self.log_folder_name))
        self.button_analyze.grid(column=0, row=0,sticky=NE)

    def button_clear_init(self):
        self.button_clear = ttk.Button(self.action_frame, text="Clear Result", command=self.clear_result)
        self.button_clear.grid(column=0, row=1, sticky=NE)

    def text_output_init(self):
        # Create text widget and specify size.
        self.text_output = Text(self.log_frame, height=35, width=CONST_LOGGING_LENGTH, font=('Consolas', 12))
        # Times New Roman
        self.text_output.grid(column=0, row=0)

    def clear_result(self):
        self.text_output.delete("1.0","end")

    def file_dialog(self):
        if self.log_folder_name == "":
            self.log_folder_name = filedialog.askdirectory(initialdir="/", title="Select A File")
        else:
            self.log_folder_name = filedialog.askdirectory(initialdir=self.log_folder_name, title="Select A File")
        self.label.configure(text="")
        self.label.configure(text=self.log_folder_name)

    def start_analyze(self, ime_log_folder_path):
        ime_interpreter_object = ImeInterpreter(ime_log_folder_path)
        processed_log = ime_interpreter_object.generate_ime_interpreter_log_output(self.button_enable_full_log)
        self.text_output.delete("1.0", "end")
        self.text_output.insert(END, processed_log)
