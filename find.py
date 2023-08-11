#!/usr/bin/python3

'''
Partially implements posix-style find command.
'''

import os
import sys
from enum import Enum
import fnmatch
import re
import subprocess

class FindType(Enum):
    DIRECTORY = 1
    FILE = 2
    SYMBOLIC_LINK = 3

class RegexType(Enum):
    PY = 0
    SED = 1
    EGREP = 2

class PathParser:
    def __init__(self, find_root, path_split=None):
        '''
        Initialize the PathParser object for use with Finder.
        Inputs: find_root - The root that we are interrogating
                path_split - When set, A 2-item tuple or list containing the head and tail of the
                             path; the head must begin with find_root and must be a directory
                             When not set, find_root is the path being interrogated
        '''
        self._find_root = find_root
        if path_split:
            if len(path_split) != 2:
                raise ValueError('path_split is not length of 2: {}'.format(path_split))
            elif not path_split[0].startswith(find_root):
                raise ValueError(
                    'Expected root "{}" to begin with find_root "{}"'.format(path_split[0], find_root)
                )
            self._root = path_split[0]
            self._name = path_split[1]
            self._rel_dir = self._root[len(find_root):]
            if self._rel_dir:
                self._rel_dir = os.path.normpath(self._rel_dir)
                if self._rel_dir.startswith(os.sep):
                    self._rel_dir = self._rel_dir[1:]
            self._full_path = os.path.join(self._root, self._name)
        else:
            self._root = ''
            self._rel_dir = ''
            self._name = find_root
            self._full_path = find_root

    @property
    def find_root(self):
        return self._find_root

    @property
    def root(self):
        return self._root

    @property
    def rel_dir(self):
        return self._rel_dir

    @property
    def name(self):
        return self._name

    @property
    def full_path(self):
        return self._full_path

    def get_type(self):
        if os.path.islink(self._full_path):
            return FindType.SYMBOLIC_LINK
        elif os.path.isdir(self._full_path):
            return FindType.DIRECTORY
        elif os.path.isfile(self._full_path):
            return FindType.FILE
        else:
            return None

    def get_rel_depth(self):
        if self._rel_dir is None:
            return 0
        elif not self._rel_dir:
            return 1
        depth = len(self._rel_dir.split(os.sep)) + 1
        return depth

class Action:
    def handle(self, path_parser):
        pass

class PrintAction(Action):
    def __init__(self, end=None):
        super().__init__()
        self._end = end

    def handle(self, path_parser):
        if self._end is not None:
            print(path_parser.full_path, end=self._end)
        else:
            print(path_parser.full_path)

class PyPrintAction(Action):
    def __init__(self, format, end=None):
        super().__init__()
        self._format = format
        self._end = end

    def handle(self, path_parser):
        d = {
            "full_path": path_parser.full_path,
            "root": path_parser.root,
            "rel_dir": path_parser.rel_dir,
            "name": path_parser.name,
            "find_root": path_parser.find_root
        }
        s = os.stat(path_parser.full_path)
        d.update({k: getattr(s, k) for k in dir(s) if k.startswith('st_')})
        print_out = self._format.format(**d)
        if self._end is not None:
            print(print_out, end=self._end)
        else:
            print(print_out)

class ExecuteAction(Action):
    def __init__(self, command):
        super().__init__()
        self._command = command

    def handle(self, path_parser):
        command = list(self._command)
        for i in range(len(command)):
            command[i] = command[i].replace('{}', path_parser.full_path)
        subprocess.run(command)

class DeleteAction(Action):
    def __init__(self):
        super().__init__()

    def handle(self, path_parser):
        # Handle all except "."
        if path_parser.full_path != '.':
            if os.path.isdir(path_parser.full_path):
                try:
                    os.rmdir(path_parser.full_path)
                except OSError as err:
                    print(str(err))
            else:
                try:
                    os.remove(path_parser.full_path)
                except OSError as err:
                    print(str(err))

class Matcher:
    def __init__(self):
        self._invert = False

    def is_match(self, path_parser):
        result = self._is_match(path_parser)
        if self._invert:
            result = not result
        return result

    def _is_match(self, path_parser):
        return False

    def set_invert(self, invert):
        self._invert = invert

class DefaultMatcher(Matcher):
    def __init__(self):
        super().__init__()

    def _is_match(self, path_parser):
        # Match everything
        return True

class NameMatcher(Matcher):
    def __init__(self, pattern):
        super().__init__()
        self._pattern = pattern

    def _is_match(self, path_parser):
        return fnmatch.fnmatch(path_parser.name, self._pattern)

class WholeNameMatcher(Matcher):
    def __init__(self, pattern):
        super().__init__()
        self._pattern = pattern

    def _is_match(self, path_parser):
        return fnmatch.fnmatch(path_parser.full_path, self._pattern)

class RegexMatcher(Matcher):
    def __init__(self, pattern, regex_type):
        super().__init__()
        self._regex_type = regex_type

        # Convert given regex type to Python re type
        if self._regex_type == RegexType.SED:
            # Main difference between sed and re is escaping is inverted in meaning for some chars
            pattern = self._pattern_escape_invert(pattern, '+?|{}()')
        # else: just use pattern as-is for re

        self._pattern = pattern

    @staticmethod
    def _pattern_escape_invert(pattern, chars):
        for char in chars:
            escaped_char = '\\' + char
            pattern_split = pattern.split(escaped_char)
            new_pattern_split = []
            for piece in pattern_split:
                new_pattern_split.append(piece.replace(char, escaped_char))
            pattern = char.join(new_pattern_split)
        return pattern

    def _is_match(self, path_parser):
        try:
            m = re.search(self._pattern, path_parser.full_path)
            return (m is not None)
        except:
            return False

class TypeMatcher(Matcher):
    def __init__(self, type_list):
        super().__init__()
        self._type_list = type_list

    def _is_match(self, path_parser):
        return (path_parser.get_type() in self._type_list)

class LogicOperation(Enum):
    OR = 0
    AND = 1

class GatedMatcher(Matcher):
    def __init__(self, left_matcher, right_matcher, operation=LogicOperation.AND):
        super().__init__()
        self.operation = operation
        self.left_matcher = left_matcher
        self.right_matcher = right_matcher

    def _is_match(self, path_parser):
        if self.operation == LogicOperation.AND:
            return (
                self.left_matcher.is_match(path_parser)
                and self.right_matcher.is_match(path_parser)
            )
        else:
            return (
                self.left_matcher.is_match(path_parser)
                or self.right_matcher.is_match(path_parser)
            )

class Finder:
    def __init__(self):
        self._root_dirs = []
        self._min_depth = 0
        self._max_depth = None
        self._matcher = DefaultMatcher()
        self._current_logic = LogicOperation.AND
        self._invert = False
        self._actions = []

    def add_root_dir(self, root_dir):
        self._root_dirs.append(root_dir)

    def set_min_depth(self, min_depth):
        self._min_depth = min_depth

    def set_max_depth(self, max_depth):
        self._max_depth = max_depth

    def set_logic(self, logic):
        if isinstance(self._matcher, DefaultMatcher):
            return False
        self._current_logic = logic
        return True

    def set_invert(self, invert):
        self._invert = invert

    def add_action(self, action):
        self._actions.append(action)

    def append_matcher(self, matcher, set_logic=None, set_invert=None):
        if set_logic is not None:
            self.set_logic(set_logic)
        if set_invert is not None:
            self.set_invert(set_invert)

        matcher.set_invert(self._invert)

        if isinstance(self._matcher, DefaultMatcher):
            # Only default matcher set - replace with this matcher
            self._matcher = matcher
        elif isinstance(self._matcher, GatedMatcher):
            # Gated matcher already in place
            # Just append it - find command doesn't take precedence into account, even though it may say it does
            self._matcher = GatedMatcher(self._matcher, matcher, self._current_logic)
        else:
            self._matcher = GatedMatcher(self._matcher, matcher, self._current_logic)

        # Reset these settings back to defaults
        self._current_logic = LogicOperation.AND
        self._invert = False

    def set_matcher(self, matcher):
        self._matcher = matcher

    def _handle_path(self, path_parser, actions):
        if self._matcher.is_match(path_parser):
            for action in actions:
                action.handle(path_parser)

    def _is_depth_ok(self, depth):
        return (
            depth >= self._min_depth
            and (self._max_depth is None or depth <= self._max_depth)
        )

    def _is_path_depth_ok(self, root_dir, dir_path):
        path_parser = PathParser(root_dir, (dir_path, ''))
        depth = path_parser.get_rel_depth()
        return self._is_depth_ok(depth)

    def execute(self):
        root_dirs = self._root_dirs
        if not root_dirs:
            # Default to "."
            root_dirs = ['.']
        actions = self._actions
        if not actions:
            # Default to print
            actions = [PrintAction()]

        for root_dir in root_dirs:
            # Check just the root first
            if self._is_depth_ok(0):
                self._handle_path(PathParser(root_dir), actions)

            if os.path.isdir(root_dir):
                # Walk through each
                for root, dirs, files in os.walk(root_dir, followlinks=False):
                    if self._is_path_depth_ok(root_dir, root):
                        for entity in dirs + files:
                            self._handle_path(PathParser(root_dir, (root, entity)), actions)

class Options(Enum):
    DOUBLEDASH = -1
    HELP = 0
    NOT = 1
    AND = 2
    OR = 3
    TYPE = 4
    MAX_DEPTH = 5
    MIN_DEPTH = 6
    REGEX_TYPE = 7
    NAME = 8
    WHOLE_NAME = 9
    REGEX = 10
    EXEC = 11
    PRINT = 12
    PRINT0 = 13
    PYPRINT = 14
    PYPRINT0 = 15
    DELETE = 16

class FinderParser:
    OPTION_DICT = {
        '--': Options.DOUBLEDASH,
        '-h': Options.HELP,
        '-help': Options.HELP,
        '--help': Options.HELP,
        '!': Options.NOT,
        '-not': Options.NOT,
        '-a': Options.AND,
        '-and': Options.AND,
        '-o': Options.OR,
        '-or': Options.OR,
        '-type': Options.TYPE,
        '-maxdepth': Options.MAX_DEPTH,
        '-mindepth': Options.MIN_DEPTH,
        '-regextype': Options.REGEX_TYPE,
        '-name': Options.NAME,
        '-wholename': Options.WHOLE_NAME,
        '-regex': Options.REGEX,
        '-exec': Options.EXEC,
        '-print': Options.PRINT,
        '-print0': Options.PRINT0,
        '-pyprint': Options.PYPRINT,
        '-pyprint0': Options.PYPRINT0,
        '-delete': Options.DELETE
    }

    def __init__(self):
        self._arg_idx = 0
        self._opt_idx = 0
        self._current_regex_type = RegexType.SED
        self._current_command = []

    @staticmethod
    def _print_help():
        print('''Partially implements find command in Python.

    Usage: find.py [path...] [expression...]

    default path is the current directory (.)

    operators
        ! EXPR
        -not EXPR  Inverts the resulting value of the expression
        EXPR EXPR
        EXPR -a EXPR
        EXPR -and EXPR  Logically AND the left and right expressions' result
        EXPR -o EXPR
        EXPR -or EXPR   Logically OR the left and right expressions' result

    normal options
        -help  Shows help and exit
        -maxdepth LEVELS  Sets the maximum directory depth of find (default: inf)
        -mindepth LEVELS  Sets the minimum directory depth of find (default: 0)
        -regextype TYPE  Set the regex type to py, sed, egrep (default: sed)

    tests
        -name PATTERN  Tests against the name of item using fnmatch
        -regex PATTERN  Tests against the path to the item using re
        -type [dfl]  Tests against item type directory, file, or link
        -wholename PATTERN  Tests against the path to the item using fnmatch

    actions
        -print  Print the matching path
        -print0  Print the matching path without newline
        -pyprint PYFORMAT  Print using python print() using named args find_root, root, rel_dir, name,
                        full_path, and st args from os.stat()
        -pyprint0 PYFORMAT  Same as pyprint except end is set to empty string
        -exec COMMAND ;  Execute the COMMAND where {} in the command is the matching path
        -delete  Deletes every matching path''')

    def _handle_option(self, opt, finder):
        ''' Called when option parsed, returns True iff arg is expected '''
        if opt == Options.HELP:
            self._print_help()
            sys.exit(0)
        elif opt == Options.NOT:
            finder.set_invert(True)
        elif opt == Options.AND:
            if not finder.set_logic(LogicOperation.AND):
                raise ValueError(
                    'invalid expression; you have used a binary operator \'{}\' with nothing before it.'.format(arg))
        elif opt == Options.OR:
            if not finder.set_logic(LogicOperation.OR):
                raise ValueError(
                    'invalid expression; you have used a binary operator \'{}\' with nothing before it.'.format(arg))
        elif opt == Options.PRINT:
            finder.add_action(PrintAction())
        elif opt == Options.PRINT0:
            finder.add_action(PrintAction(''))
        elif opt == Options.DELETE:
            finder.add_action(DeleteAction())
        else:
            # All other options require an argument
            return True
        return False

    def _handle_arg(self, opt, arg, finder):
        ''' Handle argument, returns True iff parsing is complete '''
        complete = True
        if opt is None or opt == Options.DOUBLEDASH:
            if arg.startswith('-') and not os.path.isdir(arg):
                raise ValueError('Unknown predicate: {}'.format(arg))
            elif self._opt_idx != 0 and opt != Options.DOUBLEDASH:
                raise ValueError('paths must precede expression: {}'.format(arg))
            else:
                finder.add_root_dir(arg)
        elif opt == Options.TYPE:
            types = []
            for c in arg:
                if c == 'f':
                    types.append(FindType.FILE)
                elif c == 'd':
                    types.append(FindType.DIRECTORY)
                elif c == 'l':
                    types.append(FindType.SYMBOLIC_LINK)
                # Don't require comma like find command, but also don't error out if they are included
                elif c != ',':
                    raise ValueError('Unsupported or unknown type {} in types string: {}'.format(c, arg))
            if not types:
                raise ValueError('No value given for type option')
            finder.append_matcher(TypeMatcher(types))
        elif opt == Options.MAX_DEPTH:
            try:
                max_depth = int(arg)
            except:
                raise ValueError('Invalid value given to max depth: {}'.format(arg))
            finder.set_max_depth(max_depth)
        elif opt == Options.MIN_DEPTH:
            try:
                min_depth = int(arg)
            except:
                raise ValueError('Invalid value given to min depth: {}'.format(arg))
            finder.set_min_depth(min_depth)
        elif opt == Options.REGEX_TYPE:
            if arg == 'py':
                self._current_regex_type = RegexType.PY
            elif arg == 'sed':
                self._current_regex_type = RegexType.SED
            elif arg == 'egrep':
                self._current_regex_type = RegexType.EGREP
                raise ValueError(
                    'Unknown regular expression type {}; valid types are py, sed, egrep.'.format(arg))
        elif opt == Options.NAME:
            finder.append_matcher(NameMatcher(arg))
        elif opt == Options.WHOLE_NAME:
            finder.append_matcher(WholeNameMatcher(arg))
        elif opt == Options.REGEX:
            finder.append_matcher(RegexMatcher(arg, self._current_regex_type))
        elif opt == Options.EXEC:
            if arg != ';':
                self._current_command += [arg]
                complete = False # Continue parsing until ;
            else:
                finder.add_action(ExecuteAction(self._current_command))
                self._current_command = []
        elif opt == Options.PYPRINT:
            finder.add_action(PyPrintAction(arg))
        elif opt == Options.PYPRINT:
            finder.add_action(PyPrintAction(arg, ''))
        return complete

    def main(self, cliargs):
        # Not a good idea to use argparse because find parses arguments in order and uses single dash options
        self._current_regex_type = RegexType.SED
        self._arg_idx = 0
        self._opt_idx = 0
        self._current_command = []
        finder = Finder()
        current_option = None
        for arg in cliargs:
            opt = FinderParser.OPTION_DICT.get(arg, None)
            if opt is None or current_option is not None:
                # This is an argument to an option
                if self._handle_arg(current_option, arg, finder):
                    current_option = None
            else:
                self._opt_idx += 1
                if self._handle_option(opt, finder):
                    current_option = opt
            self._arg_idx += 1
        if self._current_command:
            raise ValueError('arguments to option -exec must end with ;')
        finder.execute()
        return 0

if __name__ == "__main__":
    finderParser = FinderParser()
    sys.exit(finderParser.main(sys.argv[1:]))
