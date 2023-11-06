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
import importlib
import requests


class OnOffButton(ttk.Button):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.var = BooleanVar()
        self.var.set(False)
        self.configure(command=self.toggle)
        self.update_text()

    def toggle(self):
        self.var.set(not self.var.get())
        self.update_text()

    def update_text(self):
        if self.var.get():
            self.configure(text="On")
        else:
            self.configure(text="Off")


def download_file(url, filename):
    # Send a HTTP request to the URL
    r = requests.get(url, allow_redirects=True)

    # Write the content of the request to a file
    open(filename, 'wb').write(r.content)


class Root(Tk):
    def __init__(self):
        super(Root, self).__init__()
        self.title("IME log Interpreter  V4.0")
        self.minsize(1920, 850)

        self.labelFrame = ttk.LabelFrame(self, text="Log folder loaded", height=48, width=190)
        self.labelFrame.grid(column=0, row=0, padx=5, pady=5)

        self.log_frame = ttk.LabelFrame(self.labelFrame, text="Converted Log", height=48, width=190)
        self.log_frame.grid(column=0, row=2, padx=0, pady=10)

        self.action_frame = ttk.LabelFrame(self, text="Actions", height=48, width=60)
        # self.action_frame = ttk.Frame(self, height=15, width=100, )
        self.action_frame.grid(column=1, row=0, padx=5, pady=5, sticky=NS)

        self.label = ttk.Label(self.labelFrame, text="")
        self.label.grid(column=0, row=1, sticky=W)

        self.browse_button = None

        self.browse_button_init()

        self.button_analyze = None
        self.button_analyze_init()

        self.button_clear = None
        self.button_clear_init()

        self.enable_full_log = BooleanVar()
        self.enable_full_log.set(False)

        self.enable_full_log_label_frame = ttk.LabelFrame(self.action_frame, text="Enable full log", height=15, width=30)

        self.on_off_button = OnOffButton(self.enable_full_log_label_frame)
        self.full_log_button_init()

        self.text_output = ""
        self.text_output_init()

        self.log_folder_name = ""

        self.scrollbar = ttk.Scrollbar(self.log_frame, orient='vertical', command=self.text_output.yview)
        self.scrollbar.grid(row=0, column=1, sticky=NS)
        self.text_output['yscrollcommand'] = self.scrollbar.set

    def turn_on(self):
        self.enable_full_log.set(True)

    def turn_off(self):
        self.enable_full_log.set(False)

    def browse_button_init(self):
        self.browse_button = ttk.Button(self.action_frame, text="Browse IME log Folder", command=self.file_dialog)
        self.browse_button.grid(column=0, row=0, sticky=W)

    def button_analyze_init(self):
        self.button_analyze = ttk.Button(self.action_frame, text="Start Analyzing", command=lambda: self.start_analyze(self.log_folder_name))
        self.button_analyze.grid(column=0, row=3, sticky=W)

    def button_clear_init(self):
        self.button_clear = ttk.Button(self.action_frame, text="Clear Result", command=self.clear_result)
        self.button_clear.grid(column=0, row=1, sticky=W)

    def text_output_init(self):
        # Create text widget and specify size.
        self.text_output = Text(self.log_frame, height=48, width=190, font=('Consolas', 12))
        # Times New Roman
        self.text_output.grid(column=0, row=0)

    def full_log_button_init(self):
        self.enable_full_log_label_frame.grid(column=0, row=2, sticky=W)
        self.on_off_button.grid(column=0, row=0, sticky=W)

    def clear_result(self):
        self.text_output.delete("1.0", "end")

    def file_dialog(self):
        if self.log_folder_name == "":
            self.log_folder_name = filedialog.askdirectory(initialdir="/", title="Select A File")
        else:
            self.log_folder_name = filedialog.askdirectory(initialdir=self.log_folder_name, title="Select A File")
        self.label.configure(text="")
        self.label.configure(text=self.log_folder_name)

    def start_analyze(self, ime_log_folder_path):
        import imeinterpreter
        ime_interpreter_object = imeinterpreter.ImeInterpreter(ime_log_folder_path)
        processed_log = ime_interpreter_object.generate_ime_interpreter_log_output(self.on_off_button.var.get())
        self.text_output.delete("1.0", "end")
        self.text_output.insert(END, processed_log)
