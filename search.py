#!/usr/bin/python3

'''
This executable module is a wrapper for find, grep, and sed. It facilitates search and replace
across files on the file system with a limited list of options.
Compatibility: Linux

Examples:
> search.py 'the quick brown fox'
This will search all files under the pwd for the string "the quick brown fox" and display
equivalent find/grep command with results to stdout.
Output:
find . -type f | xargs grep --color=auto -HF "the quick brown fox"
(grep search results shown here)

> search.py 'hi mom' --name '*.py' -in
This will search all python files under the pwd for the string "hi mom", ignoring case and display
line number.
Output:
find . -type f -name "*.py" | xargs grep --color=auto -HinF "hi mom"
(grep search results shown here)

> search.py coordinates[2] --regexwholename '^.*\.\(h\|hpp\|c\|cpp\)$' --replace coordinate_z
This will find all references to "coordinates[2]" in any file with the extension h, hpp, c, or cpp
and replace with "coordinate_z", prompting user for confirmation before proceeding.
Output:
find . -type f -regex "^.*\.\(h\|hpp\|c\|cpp\)$" -regextype sed | xargs grep --color=auto -HF coordinates[2]
(grep search results shown here)
Would you like to continue? (y/n): y
find . -type f -regex "^.*\.\(h\|hpp\|c\|cpp\)$" -regextype sed | xargs sed -i s=coordinates\[2\]=coordinate_z=g
(sed result shown here)

> search.py '^this.*is [a-z] regex string [0-9]+$' --regexSearch --silent
This will search all files under the pwd for the regex string 
"^this.*is [a-z] regex string [0-9]+$" and print results to stdout without printing equivalent
find/grep command.
Output:
(grep search results shown here)
'''

import sys
import argparse
import subprocess
import string

def _print_command(command):
    '''
    Prints the given command to stdout, surrounding whatever arguments with quotes that require
    them.
    Inputs: command - The command list to print.
    '''
    command_copy = [item if not any([c in item for c in string.whitespace + '?*']) 
                    else '"{}"'.format(item) 
                    for item in command]
    print(' '.join(command_copy))
    
def _parse_args(cliargs):
    '''
    Parse arguments from command line into structure.
    Inputs: cliargs - The arguments provided to the command line.
    Returns: A structure which contains all of the parsed arguments.
    '''
    parser = argparse.ArgumentParser(description='Recursively search for files within a directory')
    parser.add_argument('search_string', type=str, help='Search for this string in files')
    parser.add_argument('-r', '--regexSearch', dest='regex', action='store_true',
                        help='Search as regex instead of string')
    parser.add_argument('--root', dest='root_dir', type=str, default='.', 
                        help='Root directory in which to search (default: .)')
    parser.add_argument('-a', '--name', dest='names', type=str, action='extend', nargs='+', 
                        default=[], help='File name globs used to narrow search')
    parser.add_argument('-w', '--wholename', '--wholeName', dest='whole_names', type=str,
                        action='extend', nargs='+', default=[],
                        help='Relative file path globs used to narrow search')
    parser.add_argument('-x', '--regexname', '--regexName', dest='regex_names', type=str,
                        action='extend', nargs='+', default=[],
                        help='File name regex globs used to narrow search')
    parser.add_argument('-e', '--regexwholename', '--regexWholeName', dest='regex_whole_names',
                        type=str, action='extend', nargs='+', default=[],
                        help='Relative file path regex globs used to narrow search')
    parser.add_argument('-i', '--ignoreCase', dest='ignore_case', action='store_true',
                        help='Ignore case when searching')
    parser.add_argument('-l', '--listFileNames', dest='list_file_names', action='store_true',
                        help='List matching file names only for search operation')
    parser.add_argument('-s', '--silent', dest='silent', action='store_true',
                        help='Silence superfluous information and only give the result of the '
                             'search or replace. If this is specified with replace operation, no '
                             'output will displayed unless there was an error.')
    parser.add_argument('-n', '--showLineNumber', dest='show_line', action='store_true',
                        help='Show line number in result')
    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument('--showColor', dest='show_color', action='store_true',
                             help='Set to display color in search output (default: auto)')
    color_group.add_argument('--noColor', dest='no_color', action='store_true',
                             help='Set to not display color in search output (default: auto)')
    parser.add_argument('--replace', dest='replace_string', type=str,
                        help='String to replace search string. If --regex is selected, this must '
                             'be as a sed replace string.')
    return parser.parse_args(cliargs)
    
def _build_find_command(args):
    '''
    Builds the find with the given arguments.
    Inputs: args - The parser argument structure.
    Returns: The find command list.
    '''
    # Build the find command to filter only the files we want
    find_command = ['find', args.root_dir, '-type', 'f']
    name_options = []
    # The regex option searches the whole name, so add regex to match all directory names
    file_name_regex = ['.*/' + item for item in args.regex_names]
    all_regex_names = args.regex_whole_names + file_name_regex
    names_dict = {'-name': args.names,
                  '-wholename': args.whole_names,
                  '-regex': all_regex_names}
    for (name_arg, names) in names_dict.items():
        for name in names:
            # If something is already in name options list, add -o for "OR" operation
            if name_options:
                name_options.append('-o')
            name_options += [name_arg, name]
    # If any regex name is set, set regextype to sed
    if all_regex_names:
        name_options += ['-regextype', 'sed']
    find_command += name_options
    return find_command
    
def _build_grep_command(args):
    '''
    Builds the grep command with the given arguments.
    Inputs: args - The parser argument structure.
    Returns: The grep command list.
    '''
    # Build the grep command to search in the above files
    grep_command = ['xargs', 'grep']
    grep_color_option = '--color=auto'
    if args.show_color:
        grep_color_option = '--color=always'
    elif args.no_color:
        grep_color_option = '--color=never'
    grep_other_options = '-H'
    if args.ignore_case:
        grep_other_options += 'i'
    if args.list_file_names:
        grep_other_options += 'l'
    if args.show_line:
        grep_other_options += 'n'
    if args.regex:
        grep_other_options += 'E' # For grep "extended regex"
    else:
        grep_other_options += 'F' # Default to string search
    grep_command += [grep_color_option, grep_other_options, args.search_string]
    return grep_command
    
def _escape_chars(string, escape_chars_string, escape_char):
    '''
    Returns: A copy of string with all of the characters in escape_chars_string escaped with
             escape_char.
    '''
    string_copy = string
    # Escape the escape_char first
    if escape_char in escape_chars_string:
        string_copy = string_copy.replace(escape_char, escape_char + escape_char)
    # Escape the rest of the characters
    for char in escape_chars_string:
        if char != escape_char:
            string_copy = string_copy.replace(char, escape_char + char)
    return string_copy
    
def _build_replace_command(args):
    '''
    Builds the sed find/replace command with the given arguments.
    Inputs: args - The parser argument structure.
    Returns: The replace command list.
    '''
    search_string = args.search_string
    replace_string = args.replace_string
    if not args.regex:
        # Escape all special characters
        search_string = _escape_chars(search_string, '\\^$.*?[]', '\\')
        replace_string = _escape_chars(replace_string, '\\[]&', '\\')
    sed_script = 's={}={}=g{}'.format(search_string.replace('=', '\\='),
                                      replace_string.replace('=', '\\='),
                                      'i' if args.ignore_case else '')
    return ['xargs', 'sed', '-i', sed_script]

def main(cliargs):
    '''
    Main function for this module.
    Inputs: cliargs - The arguments given at command line, excluding the executable arg.
    Returns: 0 if processed normally
             1 if operation cancelled
             2 if invalid entry provided
    '''
    args = _parse_args(cliargs)
    find_command = _build_find_command(args)
    grep_command = _build_grep_command(args)
    # If not silent, print the CLI equivalent of what is about to be done
    if not args.silent:
        _print_command(find_command + ['|'] + grep_command)
    # Execute find to get all files
    find_process = subprocess.Popen(find_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    find_output, _ = find_process.communicate()
    if not args.replace_string or not args.silent:
        # Execute grep on those files and print result to stdout in realtime (ignore stderr)
        grep_process = subprocess.Popen(grep_command,
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        grep_process.communicate(input=find_output)
    if args.replace_string:
        replace_command = _build_replace_command(args)
        # If not silent, check if user wants to continue then print the CLI equivalent of what is
        # about to be done
        if not args.silent:
            input_str = input('Would you like to continue? (y/n): ')
            if input_str.lower() == 'n' or input_str.lower() == 'no':
                print('Cancelled')
                return 1
            elif input_str.lower() != 'y' and input_str.lower() != 'yes':
                print('Invalid entry: {}'.format(input_str))
                return 2
            # Continue otherwise
            _print_command(find_command + ['|'] + replace_command)
        # Execute the sed command to do the replace
        replace_process = subprocess.Popen(replace_command, stdin=subprocess.PIPE)
        replace_process.communicate(input=find_output)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
