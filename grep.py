#!/usr/bin/env python3

import sys
import argparse

class AutoInputFileIterable:
    def __init__(self, file_path, file_mode='r', newline_str=None):
        self._file_path = file_path
        self._file_mode = file_mode
        self._newline_str = newline_str
        self._fp = None

    def __iter__(self):
        self._fp = open(self._file_path, self._file_mode, newline=self._newline_str)
        return self._fp.__iter__()

    def __next__(self):
        return self._fp.__next__()

    def name(self):
        return self._file_path

class StdinIterable:
    def __init__(self):
        pass

    def __iter__(self):
        return sys.stdin.__iter__()

    def __next__(self):
        return sys.stdin.__next__()

    def name(self):
        return '(standard input)'


def _parse_args(cliargs):
    parser = argparse.ArgumentParser('Partially implements grep command entirely in Python.')

    parser.add_argument('patterns', type=str, default=None,
                        help='Pattern(s) to search for; can contain multiple patterns separated by newlines.')
    parser.add_argument('file', type=str, nargs='*', default=[],
                        help='Files to search; will search from stdin if none specified')

    pattern_group = parser.add_argument_group('Pattern selection and interpretation')
    # pattern_group.add_argument('-E', '--extended-regexp', action='store_true',
    #                            help='PATTERNS are extended regular expressions')
    pattern_group.add_argument('-F', '--fixed-strings', action='store_true',
                               help='PATTERNS are strings')
    # pattern_group.add_argument('-G', '--basic-regexp', action='store_true',
    #                            help='PATTERNS are basic regular expressions')
    # pattern_group.add_argument('-e', '--regexp', dest='patterns', type=str, default=None,
    #                            help='use PATTERNS for matching')
    # pattern_group.add_argument('-f', '--file', type=str, default=None,
    #                            help='take PATTERNS from FILE')
    # pattern_group.add_argument('-i', '--ignore-case', action='store_true',
    #                            help='ignore case distinctions in patterns and data')
    # pattern_group.add_argument('--no-ignore-case', dest='ignore_case', action='store_false',
    #                            help='do not ignore case distinctions (default)')
    # pattern_group.add_argument('-w', '--word-regexp', action='store_true',
    #                            help='match only whole words')
    # pattern_group.add_argument('-x', '--line-regexp', action='store_true',
    #                            help='match only whole lines')
    # pattern_group.add_argument('-z', '--null-data', action='store_true',
    #                            help='a data line ends in 0 byte, not newline')

    # misc_group = parser.add_argument_group('Miscellaneous')
    # misc_group.add_argument('-s', '--no-messages', action='store_true', help='suppress error messages')
    # misc_group.add_argument('-v', '--invert-match', action='store_true', help='select non-matching lines')
    # misc_group.add_argument('-V', '--version', action='store_true', help='display version information and exit')

    output_ctrl_grp = parser.add_argument_group('Output control')
    # output_ctrl_grp.add_argument('-m', '--max-count', metavar='NUM', type=int, default=None,
    #                              help='stop after NUM selected lines')
    # output_ctrl_grp.add_argument('-b', '--byte-offset', action='store_true',
    #                              help='print the byte offset with output lines')

    # output_ctrl_grp.add_argument('-n', '--line-number', action='store_true', help='print line number with output lines')
    # output_ctrl_grp.add_argument('--line-buffered', action='store_true', help='flush output on every line')
    output_ctrl_grp.add_argument('-H', '--with-filename', action='store_true', help='print file name with output lines')
    # output_ctrl_grp.add_argument('-h', '--no-filename', action='store_true', help='suppress the file name prefix on output')
    # output_ctrl_grp.add_argument('--label', type=str, metavar='LABEL', help='use LABEL as the standard input file name prefix')
    # output_ctrl_grp.add_argument('-o', '--only-matching', action='store_true', help='show only nonempty parts of lines that match')
    # output_ctrl_grp.add_argument('-q', '--quiet', '--silent', action='store_true', help='suppress all normal output')
    # output_ctrl_grp.add_argument('--binary-files', type=str, metavar='TYPE', choices=['binary', 'text', 'without-match'],
    #                              help='assume that binary files are TYPE;\n'
    #                              'TYPE is \'binary\', \'text\', or \'without-match\'')
    # output_ctrl_grp.add_argument('-a', '--text', action='store_true', help='equivalent to --binary-files=text')
    # output_ctrl_grp.add_argument('-I', action='store_true', help='equivalent to --binary-files=without-match')
    # output_ctrl_grp.add_argument('-d', '--directories', type=str, metavar='ACTION', choices=['read', 'recurse', 'skip'],
    #                              help='how to handle directories;\n'
    #                              'ACTION is \'read\', \'recurse\', or \'skip\'')
    # output_ctrl_grp.add_argument('-D', '--devices=ACTION', type=str, metavar='ACTION', choices=['read', 'skip'],
    #                              help='how to handle devices, FIFOs and sockets;'
    #                              'ACTION is \'read\' or \'skip\'')
    # output_ctrl_grp.add_argument('-r', '--recursive', action='store_true', help='like --directories=recurse')
    # output_ctrl_grp.add_argument('-R', '--dereference-recursive', action='store_true', help='likewise, but follow all symlinks')
    # output_ctrl_grp.add_argument('--include', type=str, metavar='GLOB', help='search only files that match GLOB (a file pattern)')
    # output_ctrl_grp.add_argument('--exclude', type=str, metavar='GLOB', help='skip files that match GLOB')
    # output_ctrl_grp.add_argument('--exclude-from', type=str, metavar='FILE', help='skip files that match any file pattern from FILE')
    # output_ctrl_grp.add_argument('--exclude-dir', type=str, metavar='GLOB', help='skip directories that match GLOB')
    # output_ctrl_grp.add_argument('-L', '--files-without-match', action='store_true', help='print only names of FILEs with no selected lines')
    # output_ctrl_grp.add_argument('-l', '--files-with-matches', action='store_true', help='print only names of FILEs with selected lines')
    # output_ctrl_grp.add_argument('-c', '--count', action='store_true', help='print only a count of selected lines per FILE')
    # output_ctrl_grp.add_argument('-T', '--initial-tab', action='store_true', help='make tabs line up (if needed)')
    # output_ctrl_grp.add_argument('-Z', '--null', action='store_true', help='print 0 byte after FILE name')

    context_ctrl_grp = parser.add_argument_group('Context control')
    # context_ctrl_grp.add_argument('-B, --before-context=NUM', action='store_true', help='print NUM lines of leading context')
    # context_ctrl_grp.add_argument('-A, --after-context=NUM', action='store_true', help='print NUM lines of trailing context')
    # context_ctrl_grp.add_argument('-C, --context=NUM', action='store_true', help='print NUM lines of output context')
    context_ctrl_grp.add_argument('--color', '--colour', type=str, metavar='WHEN', nargs='?', default='auto',
                                  choices=['always', 'never', 'auto'],
                                  help='use markers to highlight the matching strings;\n'
                                  'WHEN is \'always\', \'never\', or \'auto\'')
    # context_ctrl_grp.add_argument('-U', '--binary', action='store_true', help='do not strip CR characters at EOL (MSDOS/Windows)')

    return parser.parse_args(cliargs)

def main(cliargs):
    args = _parse_args(cliargs)

    if not args.patterns:
        print('No patterns provided')
        return 1

    files = []
    if not args.file:
        files += [StdinIterable()]
    else:
        files += [AutoInputFileIterable(f) for f in args.file]

    patterns = args.patterns.split('\n')

    for file in files:
        for line in file:
            if line.endswith('\n'):
                end = ''
            else:
                end = '\n'
            for pattern in patterns:
                if pattern in line:
                    if args.with_filename:
                        print('{}: '.format(file.name()), end='')
                    print(line, end=end)
                    break


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
