# py-cxx-builder

A Python library for building C++ extensions with cross-platform support for MSVC (Windows) and GCC (Linux/macOS).

## Installation

```bash
pip install py-cxx-builder
```

## Features

- Cross-platform support: MSVC on Windows, GCC on Linux/macOS
- Automatic detection of Python include directories
- Parallel compilation using multiprocessing
- Static library generation before linking
- Automatic dependency detection (header files)
- Generation of `compile_commands.json` for IDE integration

## Quick Start

```python
from py_cxx_builder import CXXBuilder
import glob

# Create a builder instance
builder = CXXBuilder()

# Add macros
builder.add_macro('MY_MACRO', 1)

# Add source files
builder.add_files(['src/module.cpp', 'src/utils.cpp'])

# Set the main extension file
builder.set_main_file('src/main.cpp')

# Add include directories
builder.include_dirs.append('include')

# Build the extension
builder.build('my_extension')
```

## API Reference

### CXXBuilder

The main class for building C++ extensions.

#### Methods

- `add_macro(key, value=None)`: Add a preprocessor macro
- `add_files(files, directory=None, kind=None)`: Add source files to compile
- `remove_files(files, directory=None)`: Remove source files from the build
- `set_main_file(fn, directory=None)`: Set the main extension source file
- `detect(hdr, lib, macros=None)`: Detect if a header exists and add library
- `build(name, nprocess=None)`: Build the extension module

#### Attributes

- `include_dirs`: List of include directories
- `libdirs`: List of library directories
- `macros`: List of preprocessor macros
- `libs`: List of libraries to link
- `extra_compile_args`: Extra compiler arguments
- `extra_link_args`: Extra linker arguments

## Platform-Specific Notes

### Windows (MSVC)

The builder automatically configures:
- `/O2` optimization
- `/std:c++20` standard
- Debug symbols with PDB files
- UTF-8 source encoding

### Linux/macOS (GCC)

The builder automatically configures:
- `-O2` optimization
- `-std=c++20` standard
- Position-independent code (`-fpic`)
- Dead code stripping

## Requirements

- Python >= 3.10
- setuptools >= 61.0
- A C++ compiler (MSVC on Windows, GCC on Linux/macOS)

## License

MIT License
