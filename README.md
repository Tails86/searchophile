# searchophile

Contains file search functionality, combining find, grep, and sed commands. This package is made
platform-independent by using the Python tools
[refind](https://pypi.org/project/refind/),
[greplica](https://pypi.org/project/greplica/), and
[sedeuce](https://pypi.org/project/sedeuce/).

## Contribution

Feel free to open a bug report or make a merge request on [github](https://github.com/Tails86/searchophile/issues).

## Installation
This project is uploaded to PyPI at https://pypi.org/project/searchophile/

To install, ensure you are connected to the internet and execute: `python3 -m pip install searchophile --upgrade`

Ensure Python's scripts directory is under the environment variable `PATH` in order to be able to execute the CLI tools properly from command line.

## CLI Tools

The following CLI commands are installed with this package. Execute --help on any of these commands
to get more information.

- search : search and display contents of files and optionally replace
- csearch : calls search with filtering for C/C++ code files (.h, .hpp, .c, .cpp, .cxx, .cc) and output line numbers
- pysearch : calls search with filtering for Python code files (.py) and output line numbers
- refind : find clone written in Python
- greplica : grep clone written in Python
- sedeuce : sed clone written in Python