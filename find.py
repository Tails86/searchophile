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

class Action:
    def handle(self, path):
        pass

class PrintAction(Action):
    def handle(self, path):
        print(path)

class ExecuteAction(Action):
    def __init__(self, command):
        super().__init__()
        self._command = command

    def handle(self, path):
        command = list(self._command)
        for i in range(len(command)):
            command[i] = command[i].replace('{}', path)
        subprocess.run(command)

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
            self._root = None
            self._rel_dir = None
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
                action.handle(path_parser.full_path)

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

def _to_option(s):
    if s == '-h' or s == '-help' or s == '--help':
        return Options.HELP
    elif s == '!' or s == '-not':
        return Options.NOT
    elif s == '-a' or s == '-and':
        return Options.AND
    elif s == '-o' or s == '-or':
        return Options.OR
    elif s == '-type':
        return Options.TYPE
    elif s == '-maxdepth':
        return Options.MAX_DEPTH
    elif s == '-mindepth':
        return Options.MIN_DEPTH
    elif s == '-regextype':
        return Options.REGEX_TYPE
    elif s == '-name':
        return Options.NAME
    elif s == '-wholename':
        return Options.WHOLE_NAME
    elif s == '-regex':
        return Options.REGEX
    elif s == '-exec':
        return Options.EXEC
    elif s == '-print':
        return Options.PRINT
    return None

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
    --help  Shows help and exit
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
    -exec COMMAND ;  Execute the COMMAND where {} in the command is the matching path''')

def main(cliargs):
    # Not a good idea to use argparse because find parses arguments in order and uses single dash options
    current_regex_type = RegexType.SED
    arg_idx = 0
    opt_idx = 0
    finder = Finder()
    current_option = None
    current_command = []
    for arg in cliargs:
        opt = _to_option(arg)
        if opt is None or current_option is not None:
            # This is an argument to an option
            reset_option = True
            if current_option is None:
                if arg.startswith('-') and not os.path.isdir(arg):
                    raise ValueError('Unknown predicate: {}'.format(arg))
                elif opt_idx != 0:
                    raise ValueError('paths must precede expression: {}'.format(arg))
                else:
                    finder.add_root_dir(arg)
            elif current_option == Options.TYPE:
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
            elif current_option == Options.MAX_DEPTH:
                try:
                    max_depth = int(arg)
                except:
                    raise ValueError('Invalid value given to max depth: {}'.format(arg))
                finder.set_max_depth(max_depth)
            elif current_option == Options.MIN_DEPTH:
                try:
                    min_depth = int(arg)
                except:
                    raise ValueError('Invalid value given to min depth: {}'.format(arg))
                finder.set_min_depth(min_depth)
            elif current_option == Options.REGEX_TYPE:
                if arg == 'py':
                    current_regex_type = RegexType.PY
                elif arg == 'sed':
                    current_regex_type = RegexType.SED
                elif arg == 'egrep':
                    current_regex_type = RegexType.EGREP
                    raise ValueError(
                        'Unknown regular expression type {}; valid types are py, sed, egrep.'.format(arg))
            elif current_option == Options.NAME:
                finder.append_matcher(NameMatcher(arg))
            elif current_option == Options.WHOLE_NAME:
                finder.append_matcher(WholeNameMatcher(arg))
            elif current_option == Options.REGEX:
                finder.append_matcher(RegexMatcher(arg, current_regex_type))
            elif current_option == Options.EXEC:
                if arg != ';':
                    current_command += [arg]
                    reset_option = False
                else:
                    finder.add_action(ExecuteAction(current_command))
                    current_command = []

            if reset_option:
                current_option = None
        else:
            opt_idx += 1
            if opt == Options.HELP:
                _print_help()
                return 0
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
            elif current_option is None:
                # All other options requre an argument
                current_option = opt
        arg_idx += 1
    if current_command:
        raise ValueError('arguments to option -exec must end with ;')
    finder.execute()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
