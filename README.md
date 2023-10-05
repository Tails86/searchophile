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

The following CLI commands are installed with this package.

- search : search and display contents of files and optionally replace
- csearch : calls search with filtering for C/C++ code files (.h, .hpp, .c, .cpp, .cxx, .cc) and output line numbers
- pysearch : calls search with filtering for Python code files (.py) and output line numbers
- [refind](https://pypi.org/project/refind/) : find clone written in Python
- [greplica](https://pypi.org/project/greplica/) : grep clone written in Python
- [sedeuce](https://pypi.org/project/sedeuce/) : sed clone written in Python

### Search CLI Help

```
usage: search [-h] [-s SEARCH_STRING_OPT] [-r] [-i] [-l] [-n] [--whole-word]
              [--no-grep-tweaks] [--show-color | --no-color] [--root ROOT_DIR] [-a NAME]
              [-w PATH] [-x REGEX_NAME] [-e REGEX_PATH] [-M MAX_DEPTH] [-m MIN_DEPTH]
              [--replace REPLACE_STRING] [-t] [--show-errors] [--version] [--dry-run]
              [search_string]

Recursively search for files within a directory

optional arguments:
  -h, --help            show this help message and exit

grep Options:
  search_string         Search for this string in files (as positional)
  -s SEARCH_STRING_OPT, --string SEARCH_STRING_OPT
                        Search for this string in files (as option)
  -r, --regex-search    Search as regex instead of string
  -i, --ignore-case     Ignore case when searching
  -l, --list-file-names
                        List matching file names only for search operation
  -n, --show-line-number
                        Show line number in result
  --whole-word, --wholeword
                        Search with whole word only
  --no-grep-tweaks      Don't make any tweaks to the output of grep
  --show-color          Set to display color in search output (default: auto)
  --no-color            Set to not display color in search output (default: auto)

find options:
  --root ROOT_DIR       Root directory in which to search (default: cwd)
  -a NAME, --name NAME  File name globs used to narrow search
  -w PATH, --wholename PATH, --whole-name PATH, --path PATH
                        Relative file path globs used to narrow search
  -x REGEX_NAME, --regexname REGEX_NAME, --regex-name REGEX_NAME
                        File name regex globs used to narrow search
  -e REGEX_PATH, --regexwholename REGEX_PATH, --regex-whole-name REGEX_PATH,
  --regexpath REGEX_PATH, --regex-path REGEX_PATH
                        Relative file path regex globs used to narrow search
  -M MAX_DEPTH, --maxdepth MAX_DEPTH, --max-depth MAX_DEPTH
                        Maximum find directory depth (default: inf)
  -m MIN_DEPTH, --mindepth MIN_DEPTH, --min-depth MIN_DEPTH
                        Minimum find directory depth (default: 0)

sed options:
  --replace REPLACE_STRING
                        String to replace search string. If --regex is selected, this must be
                        compatible with sed substitute replace string.

other options:
  -t, --silent          Silence information & confirmations generated by this script. If this
                        is specified with replace operation, no output will displayed unless
                        there was an error.
  --show-errors         Show all errors to stderr instead of suppressing
  --version             output version information and exit
  --dry-run, --dryrun   Print equivalent find/grep/sed commands and exit.

All regular expressions must be in "extended" form.
```