from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize

ext_modules = [
    Extension("imeinterpreter", ["imeinterpreter.py"]),
]

setup(
    name="imeinterpreter",
    ext_modules=cythonize(ext_modules),
)

ext_modules = [
    Extension("emslifecycle", ["emslifecycle.py"]),
]

setup(
    name="emslifecycle",
    ext_modules=cythonize(ext_modules),
)

ext_modules = [
    Extension("applicationpoller", ["applicationpoller.py"]),
]

setup(
    name="applicationpoller",
    ext_modules=cythonize(ext_modules),
)

ext_modules = [
    Extension("subgraph", ["subgraph.py"]),
]

setup(
    name="subgraph",
    ext_modules=cythonize(ext_modules),
)

ext_modules = [
    Extension("constructinterpretedlog", ["constructinterpretedlog.py"]),
]

setup(
    name="constructinterpretedlog",
    ext_modules=cythonize(ext_modules),
)

ext_modules = [
    Extension("win32app", ["win32app.py"]),
]

setup(
    name="win32app",
    ext_modules=cythonize(ext_modules),
)

ext_modules = [
    Extension("logprocessinglibrary", ["logprocessinglibrary.py"]),
]

setup(
    name="logprocessinglibrary",
    ext_modules=cythonize(ext_modules),
)


ext_modules = [
    Extension("tkinterui", ["tkinterui.py"]),
]

setup(
    name="tkinterui",
    ext_modules=cythonize(ext_modules),
)