# MIT License
#
# Copyright (c) 2023 James Smith
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
This executable module is a wrapper for find, grep, and sed. It facilitates search and replace
across files on the file system with a limited list of options.
Compatibility: Linux

Examples:
> search.py 'the quick brown fox'
This will search all files under the pwd for the string "the quick brown fox" and display
equivalent find/grep command with results to stdout.
Output:
find . -type f -exec grep --color=auto -HF 'the quick brown fox' {} \;
(grep search results shown here)

> search.py 'hi mom' --name '*.py' -in
This will search all python files under the pwd for the string "hi mom", ignoring case and display
line number.
Output:
find . -type f -name '*.py' -exec grep --color=always -HinF 'hi mom' {} \;
(grep search results shown here)

> search.py coordinates[2] --regexwholename '^.*\.\(h\|hpp\|c\|cpp\)$' --replace coordinate_z
This will find all references to "coordinates[2]" in any file with the extension h, hpp, c, or cpp
and replace with "coordinate_z", prompting user for confirmation before proceeding.
Output:
find . -type f -regex '^.*\.\(h\|hpp\|c\|cpp\)$' -regextype sed -exec grep --color=always -HF 'coordinates[2]' {} \;
(grep search results shown here)
Would you like to continue? (y/n): y
find . -type f -regex '^.*\.\(h\|hpp\|c\|cpp\)$' -regextype sed | xargs sed -i 's=coordinates\[2\]=coordinate_z=g'
(sed result shown here)

> search.py '^this.*is [a-z] regex string [0-9]+$' --regexSearch --silent
This will search all files under the pwd for the regex string
"^this.*is [a-z] regex string [0-9]+$" and print results to stdout without printing equivalent
find/grep command.
Output:
(grep search results shown here)
'''

import os
import sys
import argparse
import subprocess
import string

__version__ = '0.9.3'
PACKAGE_NAME = 'searchophile'

THIS_SCRIPT_PATH = os.path.abspath(os.path.realpath(__file__))
THIS_SCRIPT_DIR = os.path.dirname(THIS_SCRIPT_PATH)
FIND_CMD = 'refind'
GREP_CMD = 'greplica'
SED_CMD = 'sedeuce'

def _item_needs_quotes(item):
    '''
    Returns true iff the given item needs to be surrounded in quotes.
    '''
    return any([c in item for c in string.whitespace + '~`#$&*()|[]{};<>?!\\"']) or len(item) <= 0

def _which(cmd):
    paths = os.environ.get('PATH', '') + os.path.pathsep + os.environ.get('path', '')
    paths = paths.split(os.path.pathsep)
    dirs = [d for d in paths if os.path.isdir(d)]
    for dir_path in dirs:
        for item in [f for f in os.listdir(dir_path) if f == cmd]:
            item_path = os.path.join(dir_path, item)
            if os.path.isfile(item_path):
                return item_path
    return None

def _quotify_item(item):
    '''
    Quotifies a single item.
    '''
    # Once it's quoted, the only character to escape is a quote character. This is done by adding
    # an end quote, escaping the quote, and then starting a new quoted string.
    item_copy = '\'{}\''.format(_escape_chars(item, '\'', '\\', '\'\\{}\''))
    # A side effect of the above is that the string may contain superfluous empty strings at the
    # beginning or end, but we don't want to do this if the string was empty to begin with.
    # Note: I don't want to use shlex for this reason (it doesn't clean up its empty strings)
    if item_copy != '\'\'':
        if item_copy.startswith('\'\''):
            item_copy = item_copy[2:]
        if item_copy.endswith('\'\''):
            item_copy = item_copy[:-2]
    return item_copy

def _quotify_command(command):
    '''
    Surrounds the items in the given command with quotes iff it contains special characters and
    escapes strong quote characters when necessary.
    '''
    return [_escape_chars(item, '\'', '\\') if not _item_needs_quotes(item)
            else _quotify_item(item)
            for item in command]

def _print_command(command):
    '''
    Prints the given command to stdout.
    Inputs: command - The command list to print.
    '''
    print(' '.join(command))

def _parse_args(cliargs):
    '''
    Parse arguments from command line into structure.
    Inputs: cliargs - The arguments provided to the command line.
    Returns: A structure which contains all of the parsed arguments.
    '''
    parser = argparse.ArgumentParser(description='Recursively search for files within a directory')
    grep_group = parser.add_argument_group('grep Options')
    search_string_group = grep_group.add_mutually_exclusive_group()
    search_string_group.add_argument('search_string', default=None, nargs='?', type=str,
                                     help='Search for this string in files (as positional)')
    search_string_group.add_argument('-s', '--string', default=None, dest='search_string_opt',
                                     type=str, help='Search for this string in files (as option)')
    grep_group.add_argument('-r', '--regexSearch', dest='regex', action='store_true',
                            help='Search as regex instead of string')
    grep_group.add_argument('-i', '--ignoreCase', dest='ignore_case', action='store_true',
                            help='Ignore case when searching')
    grep_group.add_argument('-l', '--listFileNames', dest='list_file_names', action='store_true',
                            help='List matching file names only for search operation')
    grep_group.add_argument('-n', '--showLineNumber', dest='show_line', action='store_true',
                            help='Show line number in result')
    grep_group.add_argument('--wholeWord', '--wholeword', dest='whole_word', action='store_true',
                            help='Search with whole word only')
    grep_group.add_argument('--noGrepTweaks', dest='no_grep_tweaks', action='store_true',
                            help='Don\'t make any tweaks to the output of grep')
    color_group = grep_group.add_mutually_exclusive_group()
    color_group.add_argument('--showColor', dest='show_color', action='store_true',
                             help='Set to display color in search output (default: auto)')
    color_group.add_argument('--noColor', dest='no_color', action='store_true',
                             help='Set to not display color in search output (default: auto)')
    find_group = parser.add_argument_group('find options')
    find_group.add_argument('--root', dest='root_dir', type=str, default=None,
                            help='Root directory in which to search (default: cwd)')
    find_group.add_argument('-a', '--name', dest='names', type=str, action='append',
                            default=[], help='File name globs used to narrow search')
    find_group.add_argument('-w', '--wholename', '--wholeName', '--path', dest='whole_names',
                            type=str, action='append', default=[],
                            help='Relative file path globs used to narrow search')
    find_group.add_argument('-x', '--regexname', '--regexName', dest='regex_names', type=str,
                            action='append', default=[],
                            help='File name regex globs used to narrow search')
    find_group.add_argument('-e', '--regexwholename', '--regexWholeName', dest='regex_whole_names',
                            type=str, action='append', default=[],
                            help='Relative file path regex globs used to narrow search')
    find_group.add_argument('-M', '--maxdepth', '--maxDepth', dest='max_depth', type=int,
                            default=None, help='Maximum find directory depth (default: inf)')
    find_group.add_argument('-m', '--mindepth', '--minDepth', dest='min_depth', type=int,
                            default=0, help='Minimum find directory depth (default: 0)')
    sed_group = parser.add_argument_group('sed options')
    sed_group.add_argument('--replace', dest='replace_string', type=str,
                           help='String to replace search string. If --regex is selected, this '
                                'must be as a sed replace string.')
    other_group = parser.add_argument_group()
    silent_group = other_group.add_mutually_exclusive_group()
    silent_group.add_argument('-t', '--silent', dest='silent', action='store_true',
                        help='Silence information & confirmations generated by this script. If '
                             'this is specified with replace operation, no output will displayed '
                             'unless there was an error.')
    other_group.add_argument('--showErrors', dest='show_errors', action='store_true',
                             default=False, help='Show all errors to stderr instead of suppressing')
    silent_group.add_argument('--dryRun', '--dryrun', dest='dry_run', action='store_true',
                        help='Print equivalent find/grep/sed commands and exit.')

    args = parser.parse_args(cliargs)

    return args

def _build_find_command(args, for_printout):
    '''
    Builds the find with the given arguments.
    Inputs: args - The parser argument structure.
    Returns: The find command list.
    '''
    find_dir = args.root_dir
    if find_dir is None:
        find_dir = os.path.abspath('.')
    find_command = [FIND_CMD]
    # Build the find command to filter only the files we want
    find_command += [find_dir, '-type', 'f']
    name_options = []
    # The regex option searches the whole name, so add regex to match all directory names
    file_name_regex = ['.*/' + item.lstrip('^') for item in args.regex_names]
    all_regex_names = args.regex_whole_names + file_name_regex
    names_dict = {'-name': args.names,
                  '-path': args.whole_names,
                  '-regex': all_regex_names}
    for (name_arg, names) in names_dict.items():
        for name in names:
            # If something is already in name options list, add -o for "OR" operation
            if name_options:
                name_options.append('-o')
            name_options += [name_arg, name]
    # If any regex name is set, set regextype to sed
    if all_regex_names:
        find_command += ['-regextype', 'sed']
    find_command += name_options
    if args.max_depth is not None:
        find_command += ['-maxdepth', str(args.max_depth)]
    if args.min_depth > 0:
        find_command += ['-mindepth', str(args.min_depth)]
    return find_command

def _escape_chars(string, escape_chars_string, escape_char, escape_format=None):
    '''
    Returns: A copy of string with all of the characters in escape_chars_string escaped with
             escape_char.
    '''
    string_copy = string
    if escape_format is None:
        escape_format = escape_char + '{}'
    # Escape the escape_char first
    if escape_char in escape_chars_string:
        string_copy = string_copy.replace(escape_char, escape_format.format(escape_char))
    # Escape the rest of the characters
    for char in escape_chars_string:
        if char != escape_char:
            string_copy = string_copy.replace(char, escape_format.format(char))
    return string_copy

def _build_grep_command(args, for_printout):
    '''
    Builds the grep command with the given arguments.
    Inputs: args - The parser argument structure.
            for_printout - True iff this command is given as reference printout
    Returns: The grep command list.
    '''
    # Build the grep command to search in the above files
    grep_command = [GREP_CMD]
    if args.show_color:
        grep_color_option = '--color=always'
    elif args.no_color:
        grep_color_option = '--color=never'
    # Really, auto option is needed, but grep is piped internally, so grep will not provide color if
    # auto is selected. Therefore, auto is used if this command is built for reference printout.
    # Otherwise, color is determined based on if this command is outputting directly to the
    # terminal.
    elif for_printout:
        grep_color_option = '--color=auto'
    elif sys.stdout.isatty():
        grep_color_option = '--color=always'
    else:
        grep_color_option = '--color=never'
    grep_other_options = '-H'
    if args.ignore_case:
        grep_other_options += 'i'
    if args.list_file_names:
        grep_other_options += 'l'
    if args.show_line:
        grep_other_options += 'n'
    regex = args.regex
    search_string = args.search_string or args.search_string_opt
    if args.whole_word:
        grep_other_options += 'w'
    if regex:
        grep_other_options += 'E' # For grep "extended regex"
    else:
        grep_other_options += 'F' # Default to string search
    if not args.no_grep_tweaks and not for_printout:
        # greplica can handle colon separation tweak natively
        grep_command += ['--result-sep= : ']
    grep_command += [grep_color_option, grep_other_options, search_string]
    return grep_command

def _build_replace_command(args):
    '''
    Builds the sed find/replace command with the given arguments.
    Inputs: args - The parser argument structure.
    Returns: The replace command list.
    '''
    search_string = args.search_string or args.search_string_opt
    replace_string = args.replace_string
    if not args.regex:
        # Escape all special characters
        search_string = _escape_chars(search_string, '\\^$.*?[]', '\\')
        replace_string = _escape_chars(replace_string, '\\[]&', '\\')
    sed_script = 's={}={}=g{}'.format(search_string.replace('=', '\\='),
                                      replace_string.replace('=', '\\='),
                                      'i' if args.ignore_case else '')
    return [SED_CMD, '-i', '--', sed_script]

def _grep_output_tweaks(line, args, file_list):
    '''
    Adds a space after the colon before the result so that ctrl+click always works in vscode.
    Inputs: line - The grep output line to apply tweaks to.
            args - The parser argument structure.
            file_list - List of files found by the find command.
    Returns: The augmented grep line.
    '''
    line = line.decode()
    colon_pos = None
    start_pos = 0
    if line.startswith('\x1b'):
        # When color is enabled, the first \x1b[m marks the end of the file name - that's where we
        # should start searching for colons
        start_pos = line.find('\x1b[m')
        if start_pos < 0:
            # Failed to find the color marker
            start_pos = 0
        colon_pos = line.find(':', start_pos)
    else:
        colon_pos = line.find(':')
        # Keep going until all characters up to the found colon is a valid file name.
        # Not a perfect solution, but this is the best I can do to capture file names which have
        # colons in the name.
        while colon_pos >= 0 and line[:colon_pos] not in file_list:
            colon_pos = line.find(':', colon_pos+1)

    # If line number is shown, then we want the second colon
    if args.show_line and colon_pos >= 0:
        colon_pos = line.find(':', colon_pos+1)

    # Finally, add the space were it's needed
    if colon_pos >= 0:
        line = line[:colon_pos] + ' : ' + line[colon_pos+1:]

    return line.encode()

def grep_print_thread_fn(proc, tweaker_fn):
    for line in proc.stdout:
        sys.stdout.buffer.write(tweaker_fn(line))


def main(cliargs):
    '''
    Main function for this module.
    Inputs: cliargs - The arguments given at command line, excluding the executable arg.
    Returns: 0 if processed normally
             1 if operation cancelled
             2 if invalid entry provided
    '''
    args = _parse_args(cliargs)
    find_command = _build_find_command(args, False)
    grep_command = _build_grep_command(args, False)
    # If not silent, print the approximate CLI equivalent of what is about to be done
    if not args.silent:
        cmd_to_print = (
            _quotify_command(_build_find_command(args, True)) +
            ['-exec'] +
            _quotify_command(_build_grep_command(args, True)) +
            ['{}', '\';\'']
        )
        _print_command(cmd_to_print)
    if not args.dry_run:
        if args.show_errors:
            stderr = None
        else:
            # Suppress errors
            stderr = subprocess.PIPE
        # Execute find to get all files
        find_process = subprocess.Popen(find_command, stdout=subprocess.PIPE, stderr=stderr)
        find_output, _ = find_process.communicate()
        file_list = [x for x in find_output.decode().split(os.linesep) if x != '']
        if (not args.replace_string or not args.silent) and file_list:
            # Execute grep on those files and print result to stdout in realtime
            grep_process = subprocess.Popen(
                grep_command + ['--'] + file_list,
                stdout=None,
                stderr=stderr)

            # Wait until complete
            grep_process.wait()

    if args.replace_string:
        replace_command = _build_replace_command(args)
        # If not silent, check if user wants to continue then print the CLI equivalent of what is
        # about to be done
        if not args.silent:
            if not args.dry_run:
                if file_list:
                    input_str = input('Would you like to continue? (y/n): ')
                    if input_str.lower() == 'n' or input_str.lower() == 'no':
                        print('Cancelled')
                        return 1
                    elif input_str.lower() != 'y' and input_str.lower() != 'yes':
                        print('Invalid entry: {}'.format(input_str))
                        return 2
                else:
                    print('No matches found')
                # Continue otherwise
            _print_command(_quotify_command(find_command) + ['|', 'xargs'] + _quotify_command(replace_command))
        if not args.dry_run and file_list:
            # Execute the sed command to do the replace
            replace_process = subprocess.Popen(replace_command + file_list)
            replace_process.communicate(input=find_output)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
