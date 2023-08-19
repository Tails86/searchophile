#!/usr/bin/env python3

import os
import sys
import argparse
from enum import Enum
import enum
import re

THIS_FILE_NAME = os.path.basename(__file__)

class FileIterable:
    ''' Base class for a custom file iterable '''
    # Limit each line to 128 kB which isn't human parsable at that size anyway
    LINE_BYTE_LIMIT = 128 * 1024

    def __iter__(self):
        return None

    def __next__(self):
        return None

    @property
    def name(self):
        return None

    @property
    def eof(self):
        return False

class AutoInputFileIterable(FileIterable):
    '''
    Automatically opens file on iteration and returns lines as bytes or strings.
    '''
    def __init__(self, file_path, file_mode='r', newline_str='\n'):
        self._file_path = file_path
        self._file_mode = file_mode
        self._newline_str = newline_str
        self._as_bytes = 'b' in file_mode
        if isinstance(self._newline_str, str):
            self._newline_str = self._newline_str.encode()
        self._fp = None
        if not self._as_bytes:
            # Force reading as bytes
            self._file_mode += 'b'

    def __iter__(self):
        # Custom iteration
        self._fp = open(self._file_path, self._file_mode)
        return self

    def __next__(self):
        # Custom iteration
        if self._fp:
            b = b''
            last_b = b' '
            end = b''
            newline_len = len(self._newline_str)
            while end != self._newline_str:
                last_b = self._fp.read(1)
                if last_b:
                    if len(b) < __class__.LINE_BYTE_LIMIT:
                        b += last_b
                    # else: overflow - can be detected by checking that the line ends with newline_str
                    end += last_b
                    end = end[-newline_len:]
                else:
                    # End of file
                    self._fp = None
                    break
            if b:
                if self._as_bytes:
                    return b
                else:
                    try:
                        return b.decode()
                    except UnicodeDecodeError:
                        return b
            else:
                self._fp = None
                raise StopIteration
        else:
            raise StopIteration

    @property
    def name(self):
        return self._file_path

    @property
    def eof(self):
        return (self._fp is None)

class StdinIterable(FileIterable):
    '''
    Reads from stdin and returns lines as bytes or strings.
    '''
    def __init__(self, as_bytes=False, end='\n'):
        self._as_bytes = as_bytes
        self._end = end
        if isinstance(self._end, str):
            self._end = self._end.encode()
        self._eof_detected = False

    def __iter__(self):
        # Custom iteration
        self._eof_detected = False
        return self

    def __next__(self):
        # Custom iteration
        if self._eof_detected:
            raise StopIteration
        b = b''
        end = b''
        end_len = len(self._end)
        while end != self._end:
            last_b = sys.stdin.buffer.read(1)
            if last_b:
                if len(b) < __class__.LINE_BYTE_LIMIT:
                    b += last_b
                # else: overflow - can be detected by checking that the line ends with end
                end += last_b
                end = end[-end_len:]
            else:
                self._eof_detected = True
                break
        if self._as_bytes:
            return b
        else:
            try:
                return b.decode()
            except UnicodeDecodeError:
                return b

    @property
    def name(self):
        return '(standard input)'

    @property
    def eof(self):
        return self._eof_detected

class AnsiFormat(Enum):
    '''
    Formatting which may be supplied to AnsiString.
    '''
    RESET='0'
    BOLD='1'
    FAINT='2'
    ITALIC='3'
    ITALICS=ITALIC # Alias
    UNDERLINE='4'
    SLOW_BLINK='5'
    RAPID_BLINK='6'
    SWAP_BG_FG='7'
    HIDE='8'
    CROSSED_OUT='9'
    DEFAULT_FONT='10'
    ALT_FONT_1='11'
    ALT_FONT_2='12'
    ALT_FONT_3='13'
    ALT_FONT_4='14'
    ALT_FONT_5='15'
    ALT_FONT_6='16'
    ALT_FONT_7='17'
    ALT_FONT_8='18'
    ALT_FONT_9='19'
    GOTHIC_FONT='20'
    DOUBLE_UNDERLINE='21'
    NO_BOLD_FAINT='22'
    NO_ITALIC='23'
    NO_UNDERLINE='24'
    NO_BLINK='25'
    PROPORTIONAL_SPACING='26'
    NO_SWAP_BG_FG='27'
    NO_HIDE='28'
    NO_CROSSED_OUT='29'
    NO_PROPORTIONAL_SPACING='50'
    FRAMED='51'
    ENCIRCLED='52'
    OVERLINED='53'
    NO_FRAMED_ENCIRCLED='54'
    NO_OVERLINED='55'
    SET_UNDERLINE_COLOR='58' # Must be proceeded by rgb values
    DEFAULT_UNDERLINE_COLOR='59'

    FG_BLACK='30'
    FG_RED='31'
    FG_GREEN='32'
    FG_YELLOW='33'
    FG_BLUE='34'
    FG_MAGENTA='35'
    FG_CYAN='36'
    FG_WHITE='37'
    FG_SET='38' # Must be proceeded by rgb values
    FG_DEFAULT='39'
    FG_ORANGE=FG_SET+';5;202'
    FG_PURPLE=FG_SET+';5;129'

    BG_BLACK='40'
    BG_RED='41'
    BG_GREEN='42'
    BG_YELLOW='43'
    BG_BLUE='44'
    BG_MAGENTA='45'
    BG_CYAN='46'
    BG_WHITE='47'
    BG_SET='48' # Must be proceeded by rgb values
    BG_DEFAULT='49'
    BG_ORANGE=BG_SET+';5;202'
    BG_PURPLE=BG_SET+';5;129'

class AnsiString:
    '''
    Represents an ANSI colorized/formatted string. All or part of the string may contain style and
    color formatting which may be used to print out to an ANSI-supported terminal such as those
    on Linux, Mac, and Windows 10+.

    Example 1:
    s = AnsiString('This string is red and bold string', [AnsiFormat.BOLD, AnsiFormat.FG_RED])
    print(s)

    Example 2:
    s = AnsiString('This string contains custom formatting', '38;2;175;95;95')
    print(s)

    Example 3:
    s = AnsiString('This string contains multiple color settings across different ranges')
    s.apply_formatting(AnsiFormat.BOLD, 5, 6)
    s.apply_formatting(AnsiFormat.BG_BLUE, 21, 8)
    s.apply_formatting([AnsiFormat.FG_ORANGE, AnsiFormat.ITALIC], 21, 14)
    print(s)

    Example 4:
    s = AnsiString('This string will be formatted bold and red')
    print('{:01;31}'.format(s))

    Example 5:
    s = AnsiString('This string will be formatted bold and red')
    # Use any name within AnsiFormat (can be lower or upper case representation of the name)
    print('{:bold;fg_red}'.format(s))

    Example 6:
    s = AnsiString('This string will be formatted bold and red')
    # The character '[' tells the format method to do no parsing/checking and use verbatim as codes
    print('{:[01;31}'.format(s))
    '''

    # The escape sequence that needs to be formatted with command str
    ANSI_ESCAPE_FORMAT = '\x1b[{}m'
    # The escape sequence which will clear all previous formatting (empty command is same as 0)
    ANSI_ESCAPE_CLEAR = ANSI_ESCAPE_FORMAT.format('')

    # Number of elements in each value of _color_settings dict
    SETTINGS_ITEM_LIST_LEN = 2
    # Index of _color_settings value list which contains settings to apply
    SETTINGS_APPLY_IDX = 0
    # Index of _color_settings value list which contains settings to remove
    SETTINGS_REMOVE_IDX = 1

    class Settings:
        '''
        Internal use only - mainly used to create a unique objects which may contain same strings
        '''
        def __init__(self, setting_or_settings):
            if not isinstance(setting_or_settings, list):
                settings = [setting_or_settings]
            else:
                settings = setting_or_settings

            for i, item in enumerate(settings):
                if isinstance(item, str):
                    # Use string verbatim
                    pass
                elif hasattr(item, 'value') and isinstance(item.value, str):
                    # Likely an enumeration - use the value
                    settings[i] = item.value
                else:
                    raise TypeError('Unsupported type for setting_or_settings: {}'.format(type(setting_or_settings)))

            self._str = ';'.join(settings)

        def __str__(self):
            return self._str

    def __init__(self, s='', setting_or_settings=None):
        self._s = s
        # Key is the string index to make a color change at
        # Each value element is a list of 2 lists
        #   index 0: the settings to apply at this string index
        #   index 1: the settings to remove at this string index
        self._color_settings = {}
        if setting_or_settings:
            self.apply_formatting(setting_or_settings)

    def assign_str(self, s):
        '''
        Assigns the base string.
        '''
        self._s = s

    @property
    def base_str(self):
        '''
        Returns the base string without any formatting set.
        '''
        return self._s

    @staticmethod
    def _insert_settings_to_dict(settings_dict, idx, apply, settings):
        if idx not in settings_dict:
            settings_dict[idx] = [[] for _ in range(__class__.SETTINGS_ITEM_LIST_LEN)]
        list_idx = __class__.SETTINGS_APPLY_IDX if apply else __class__.SETTINGS_REMOVE_IDX
        settings_dict[idx][list_idx].append(settings)

    def _insert_settings(self, idx, apply, settings):
        __class__._insert_settings_to_dict(self._color_settings, idx, apply, settings)

    def apply_formatting(self, setting_or_settings, start_idx=0, length=None):
        '''
        Sets the formatting for a given range of characters.
        Inputs: setting_or_settings - Can either be a single item or list of items;
                                      each item can either be a string or AnsiFormat type
                start_idx - The string start index where setting(s) are to be applied
                length - Number of characters to apply settings or None to apply until end of string

        Note: The desired effect may not be achieved if the same setting is applied over an
              overlapping range of characters.
        '''
        settings = __class__.Settings(setting_or_settings)

        # Apply settings
        self._insert_settings(start_idx, True, settings)

        if length is not None:
            # Remove settings
            self._insert_settings(start_idx + length, False, settings)

    def apply_formatting_for_match(self, setting_or_settings, match_object, group=0):
        '''
        Apply formatting using a match object generated from re
        '''
        s = match_object.start(group)
        e = match_object.end(group)
        self.apply_formatting(setting_or_settings, s, e - s)

    def clear_formatting(self):
        '''
        Clears all internal formatting.
        '''
        self._color_settings = {}

    def __str__(self):
        '''
        Returns an ANSI format string with only internal formatting set.
        '''
        return self.__format__(None)

    def __format__(self, __format_spec):
        '''
        Returns an ANSI format string with both internal and given formatting spec set.
        '''
        if not __format_spec and not self._color_settings:
            # No formatting
            return self._s

        out_str = ''
        current_settings = []
        last_idx = 0

        settings_dict = self._color_settings
        if __format_spec:
            # Make a local copy and add this temporary format spec
            settings_dict = dict(self._color_settings)

            if __format_spec.startswith("["):
                # Use the rest of the string as-is for settings
                format_settings = __class__.Settings(__format_spec[1:])
            else:
                # The format string contains names within AnsiFormat or integers, separated by semicolon
                formats = __format_spec.split(';')
                format_settings_strs = []
                for format in formats:
                    try:
                        ansi_format = AnsiFormat[format.upper()]
                    except KeyError:
                        try:
                            _ = int(format)
                        except ValueError:
                            raise ValueError(
                                'AnsiString.__format__ failed to parse format ({}); invalid name: {}'
                                .format(__format_spec, format)
                            )
                        else:
                            # Value is an integer - use the format verbatim
                            format_settings_strs.append(format)
                    else:
                        format_settings_strs.append(ansi_format.value)
                format_settings = __class__.Settings(';'.join(format_settings_strs))

            __class__._insert_settings_to_dict(settings_dict, 0, True, format_settings)

        for idx in sorted(settings_dict):
            if idx >= len(self._s):
                # Invalid
                break
            settings = settings_dict[idx]
            # Catch up output to current index
            out_str += self._s[last_idx:idx]
            last_idx = idx
            # Remove settings that it is time to remove
            for setting in settings[__class__.SETTINGS_REMOVE_IDX]:
                # setting object will only be matched and removed if it is the same reference to one
                # previously added - will raise exception otherwise which should not happen if the
                # settings dictionary and this method were setup correctly.
                current_settings.remove(setting)
            # Apply settings that it is time to add
            current_settings += settings[__class__.SETTINGS_APPLY_IDX]

            settings_to_apply = [str(s) for s in current_settings]
            if settings[__class__.SETTINGS_REMOVE_IDX] and settings_to_apply:
                # Settings were removed and there are settings to be applied -
                # need to reset before applying current settings
                settings_to_apply = [AnsiFormat.RESET.value] + settings_to_apply
            # Apply these settings
            out_str += __class__.ANSI_ESCAPE_FORMAT.format(';'.join(settings_to_apply))

        # Final catch up
        out_str += self._s[last_idx:]
        if current_settings:
            # Clear settings
            out_str += __class__.ANSI_ESCAPE_CLEAR

        return out_str

# Contains default color definitions when GREP_COLORS environment variable not defined
DEFAULT_GREP_ANSI_COLORS = {
    'mt':None,
    'ms':'01;31',
    'mc':'01;31',
    'sl':'',
    'cx':'',
    'rv':False,
    'fn':'35',
    'ln':'32',
    'bn':'32',
    'se':'36',
    'ne':False
}

def _pattern_escape_invert(pattern, chars):
    '''
    Inverts regex pattern escape characters. This is helpful to transform format string from basic
    to extended regex format (and vice-versa).
    ex: \( -> ( and ( -> \(
    '''
    for char in chars:
        escaped_char = '\\' + char
        pattern_split = pattern.split(escaped_char)
        new_pattern_split = []
        for piece in pattern_split:
            new_pattern_split.append(piece.replace(char, escaped_char))
        pattern = char.join(new_pattern_split)
    return pattern

def _parse_patterns(patterns):
    # Split for both \r\n and \n
    return [y for x in patterns.split('\r\n') for y in x.split('\n')]

class Grep:
    '''
    Contains all functionality to grep through files to find and print matching lines.
    '''
    class SearchType(Enum):
        FIXED_STRINGS = enum.auto()
        BASIC_REGEXP = enum.auto()
        EXTENDED_REGEXP = enum.auto()

    class ColorOutputMode(Enum):
        AUTO = enum.auto()
        ALWAYS = enum.auto()
        NEVER = enum.auto()

    def __init__(self, print_file=None):
        self.reset()
        self._print_file = print_file

    def reset(self):
        self._patterns = []
        self._files = []
        self._search_type = __class__.SearchType.BASIC_REGEXP
        self._ignore_case = False
        self._word_regexp = False
        self._line_regexp = False
        self._no_messages = False
        self._invert_match = False
        self._output_line_numbers = False
        self._output_file_name = False
        self._end = b'\n'
        self._results_sep = ':'
        self._name_num_sep = ':'
        self._color_output_mode = __class__.ColorOutputMode.AUTO

    def add_patterns(self, pattern_or_patterns):
        if isinstance(pattern_or_patterns, list):
            self._patterns.extend(pattern_or_patterns)
        elif isinstance(pattern_or_patterns, str):
            self._patterns.append(pattern_or_patterns)
        else:
            raise TypeError('Invalid type ({}) for pattern_or_patterns'.format(type(pattern_or_patterns)))

    def clear_patterns(self):
        self._patterns.clear()

    def add_files(self, file_or_files):
        if isinstance(file_or_files, list):
            self._files.extend(file_or_files)
        elif isinstance(file_or_files, str):
            self._files.append(file_or_files)
        else:
            raise TypeError('Invalid type ({}) for file_or_files'.format(type(file_or_files)))

    def clear_files(self):
        self._files = []

    @property
    def search_type(self):
        return self._search_type

    @search_type.setter
    def search_type(self, search_type):
        if not isinstance(search_type, __class__.SearchType):
            raise TypeError('Invalid type ({}) for search_type'.format(type(search_type)))
        self._search_type = search_type

    @property
    def ignore_case(self):
        return self._ignore_case

    @ignore_case.setter
    def ignore_case(self, ignore_case):
        self._ignore_case = ignore_case

    @property
    def word_regexp(self):
        return self._word_regexp

    @word_regexp.setter
    def word_regexp(self, word_regexp):
        self._word_regexp = word_regexp

    @property
    def line_regexp(self):
        return self._line_regexp

    @line_regexp.setter
    def line_regexp(self, line_regexp):
        self._line_regexp = line_regexp

    @property
    def no_messages(self):
        return self._no_messages

    @no_messages.setter
    def no_messages(self, no_messages):
        self._no_messages = no_messages

    @property
    def invert_match(self):
        return self._invert_match

    @invert_match.setter
    def invert_match(self, invert_match):
        self._invert_match = invert_match

    @property
    def output_line_numbers(self):
        return self._output_line_numbers

    @output_line_numbers.setter
    def output_line_numbers(self, output_line_numbers):
        self._output_line_numbers = output_line_numbers

    @property
    def output_file_name(self):
        return self._output_file_name

    @output_file_name.setter
    def output_file_name(self, output_file_name=True):
        self._output_file_name = output_file_name

    @property
    def results_sep(self):
        return self._results_sep

    @results_sep.setter
    def results_sep(self, results_sep):
        if not isinstance(results_sep, str):
            raise TypeError('Invalid type ({}) for results_sep'.format(type(results_sep)))
        self._results_sep = results_sep

    @property
    def name_num_sep(self):
        return self._name_num_sep

    @name_num_sep.setter
    def name_num_sep(self, name_num_sep):
        if not isinstance(name_num_sep, str):
            raise TypeError('Invalid type ({}) for name_num_sep'.format(type(name_num_sep)))
        self._name_num_sep = name_num_sep

    @property
    def color_output_mode(self):
        return self._color_output_mode

    @color_output_mode.setter
    def color_output_mode(self, color_output_mode):
        if not isinstance(color_output_mode, __class__.ColorOutputMode):
            raise TypeError('Invalid type ({}) for color_output_mode'.format(type(color_output_mode)))
        self._color_output_mode = color_output_mode

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, end):
        if isinstance(end, str):
            end = end.encode()
        self._end = end

    @staticmethod
    def _generate_color_dict():
        grep_color_dict = dict(DEFAULT_GREP_ANSI_COLORS)
        if 'GREP_COLORS' in os.environ:
            colors = os.environ['GREP_COLORS'].split(':')
            for color in colors:
                key_val = color.split('=', maxsplit=1)
                if len(key_val) == 2 and key_val[0] in grep_color_dict:
                    if isinstance(grep_color_dict[key_val[0]], bool):
                        grep_color_dict[key_val[0]] = key_val[1].lower() in ['1', 't', 'true', 'on']
                    else:
                        # The string must be integers separated by semicolon
                        is_valid = True
                        for item in key_val[1].split(';'):
                            try:
                                _ = int(item)
                            except ValueError:
                                is_valid = False
                                break
                        if is_valid:
                            grep_color_dict[key_val[0]] = key_val[1]
                        # else: value is ignored

        return grep_color_dict

    class LineParsingData:
        '''
        Holds various temporary state data in order to facilitate line parsing.
        '''
        def __init__(self):
            self._files = []
            self.line_format = ''
            self.patterns = []
            self.line_ending = b'\n'
            self.ignore_case = False
            self.fixed_string_parse = False
            self.color_enabled = False
            self.matching_color = None
            self.file = None
            self.file_iter = None
            self.line_data_dict = {}
            self.line = b''
            self.formatted_line = None
            self.line_idx = 0
            self.overflow_detected = False
            self.binary_detected = False
            self.num_matches = 0

        def set_color_mode(self, color_mode):
            self.color_enabled = False
            if color_mode == Grep.ColorOutputMode.ALWAYS:
                self.color_enabled = True
            elif color_mode == Grep.ColorOutputMode.AUTO:
                self.color_enabled = sys.stdout.isatty()

        @property
        def files(self):
            return self._files

        @files.setter
        def files(self, files):
            if not files:
                self._files = [StdinIterable(True, self.line_ending)]
            else:
                self._files = [AutoInputFileIterable(f, 'rb', self.line_ending) for f in files]

        def set_file(self, file):
            '''
            Prints any errors detected of previous file and sets the file currently being parsed
            '''
            self.binary_detected = False
            self.line_idx = 0
            self.num_matches = 0
            self.file = file
            if file:
                self.line_data_dict['filename'] = AnsiString(file.name)
                self.file_iter = iter(file)

        def next_line(self):
            '''
            Grabs the next line from the file and formats the line as necessary.
            Returns: True if line has been read or False if end of file reached.
            '''
            self.line_idx += 1
            try:
                self.line = next(self.file_iter)
            except StopIteration:
                # File is complete
                status_msgs = ''
                if self.binary_detected and self.num_matches > 0:
                    status_msgs += ' binary file matches'
                if self.overflow_detected:
                    if status_msgs:
                        status_msgs += ' and'
                    status_msgs += ' line overflow detected'
                if status_msgs:
                    print('{filename}: {status_msgs}'.format(status_msgs=status_msgs, **self.line_data_dict))
                return False

            # Remove the line ending if it is found
            if self.line.endswith(self.line_ending):
                self.line = self.line[:-len(self.line_ending)]
                self.overflow_detected = False
            else:
                # Only way this is acceptable is if we are done reading from file
                self.overflow_detected = not self.file.eof

            # Remove CR if ending starts with LF
            cr = b'\r'
            lf = b'\n'
            if self.line_ending.startswith(lf) and self.line.endswith(cr):
                self.line = self.line[:-1]

            try:
                str_line = self.line.decode()
            except UnicodeDecodeError:
                # Can't decode line
                # Note this is a bit more flexible as \x00 can be decoded by Python
                self.binary_detected = True
                self.formatted_line = AnsiString(self.line)
            else:
                # Make line lower case if fixed strings are used
                if self.ignore_case and self.fixed_string_parse:
                    str_line = str_line.lower()
                self.formatted_line = AnsiString(str_line)

            return True

        def match_found(self, file):
            '''
            Called when match is found in order to increment match count and print the line.
            '''
            self.num_matches += 1
            if not self.binary_detected:
                self.line_data_dict.update({
                    'num': AnsiString(str(self.line_idx+1)),
                    'line': self.formatted_line
                })
                print(self.line_format.format(**self.line_data_dict), file=file)

    def _init_line_parsing_data(self):
        '''
        Initializes line parsing data which makes up the local running state of Grep.execute().
        '''
        data = __class__.LineParsingData()

        data.ignore_case = self._ignore_case
        data.line_ending = self._end
        data.set_color_mode(self._color_output_mode)
        data.files = self._files

        if data.color_enabled:
            grep_color_dict = __class__._generate_color_dict()
            data.matching_color = grep_color_dict['mt']
            if data.matching_color is None:
                if self.invert_match:
                    # I don't get this setting because matching line isn't colored in this case
                    data.matching_color = grep_color_dict['mc']
                else:
                    data.matching_color = grep_color_dict['ms']
        else:
            data.matching_color = None

        if data.color_enabled and grep_color_dict['se']:
            name_num_sep = str(AnsiString(self._name_num_sep, grep_color_dict['se']))
            result_sep = str(AnsiString(self._results_sep, grep_color_dict['se']))
        else:
            name_num_sep = self._name_num_sep
            result_sep = self._results_sep

        data.patterns = self._patterns

        for i in range(len(data.patterns)):
            if self._search_type == __class__.SearchType.FIXED_STRINGS:
                if self._ignore_case:
                    data.patterns[i] = data.patterns[i].lower()
            elif self._search_type == __class__.SearchType.BASIC_REGEXP:
                # Transform basic regex string to extended
                # The only difference with basic is that escaping of some characters is inverted
                data.patterns[i] = _pattern_escape_invert(data.patterns[i], '?+{}|()')

            if self._word_regexp:
                if self._search_type == __class__.SearchType.FIXED_STRINGS:
                    # Transform pattern into regular expression
                    data.patterns[i] = r"\b" + re.escape(data.patterns[i]) + r"\b"
                else:
                    data.patterns[i] = r"\b" + data.patterns[i] + r"\b"
            elif self._line_regexp:
                if self._search_type == __class__.SearchType.FIXED_STRINGS:
                    # Transform pattern into regular expression
                    data.patterns[i] = re.escape(data.patterns[i])
            data.patterns[i] = data.patterns[i].encode()

        if self._word_regexp or self._line_regexp:
            # Force to regex parse
            data.fixed_string_parse = False
        else:
            data.fixed_string_parse = (self._search_type == __class__.SearchType.FIXED_STRINGS)

        data.line_format = ''
        if self._output_file_name:
            data.line_format += '{filename'
            if data.color_enabled and grep_color_dict['fn']:
                data.line_format += ':[' + grep_color_dict['fn']
            data.line_format += '}' + (name_num_sep if self._output_line_numbers else result_sep)
        if self._output_line_numbers:
            data.line_format += '{num'
            if data.color_enabled and grep_color_dict['ln']:
                data.line_format += ':[' + grep_color_dict['ln']
            data.line_format += '}' + result_sep
        data.line_format += '{line}'

        return data

    def _parse_line(self, data:LineParsingData):
        '''
        Parses a line from a file, formats line, and prints the line if match is found.
        '''
        print_line = False
        for pattern in data.patterns:
            if data.fixed_string_parse:
                loc = data.line.find(pattern)
                if loc >= 0:
                    print_line = not self._invert_match
                    if data.color_enabled and print_line:
                        while loc >= 0:
                            data.formatted_line.apply_formatting(data.matching_color, loc, len(pattern))
                            loc = data.line.find(pattern, loc + len(pattern))
                    else:
                        # No need to keep going through each pattern
                        break
                elif self._invert_match:
                    # Color setting is ignored in this case - just print it
                    print_line = True
            else:
                # Regular expression matching
                flags = 0
                if self._ignore_case:
                    flags = re.IGNORECASE
                if self._line_regexp:
                    m = re.fullmatch(pattern, data.line, flags)
                    if m is not None:
                        print_line = not self._invert_match
                        if data.color_enabled:
                            # This is going to just format the whole line
                            data.formatted_line.apply_formatting_for_match(data.matching_color, m)
                    elif self._invert_match:
                        # Color setting is ignored in this case - just print it
                        print_line = True
                else:
                    line_matches = False
                    for m in re.finditer(pattern, data.line, flags):
                        line_matches = True
                        print_line = not self._invert_match
                        if data.color_enabled:
                            data.formatted_line.apply_formatting_for_match(data.matching_color, m)
                        else:
                            # No need to keep iterating
                            break
                    if self._invert_match and not line_matches:
                        # Color setting is ignored in this case - just print it
                        print_line = True
                if print_line and (not data.color_enabled or self._invert_match):
                    # No need to keep going through each pattern
                    break
        if print_line:
            data.match_found(self._print_file)

    def execute(self):
        '''
        Executes Grep with all the assigned attributes.
        '''
        if not self._patterns:
            print('No patterns provided', file=sys.stderr)
            return 1

        data = self._init_line_parsing_data()

        for file in data.files:
            try:
                data.set_file(file)
            except EnvironmentError as ex:
                # This occurs if permission is denied
                if not self._no_messages:
                    print('{}: {}'.format(THIS_FILE_NAME, str(ex)), file=sys.stderr)
            else:
                while data.next_line():
                    self._parse_line(data)

        return 0

class GrepArgParser:
    '''
    Used to parse command line arguments for Grep.
    '''
    def __init__(self):
        self._parser = argparse.ArgumentParser(description='Partially implements grep command entirely in Python.')
        self._parser.add_argument('patterns_positional', type=str, nargs='?', default=None, metavar='PATTERNS',
                            help='Pattern(s) to search for; can contain multiple patterns separated by newlines. '
                            'This is required if --regexp or --file are not specified.')
        self._parser.add_argument('file', type=str, nargs='*', default=[],
                            help='Files to search; will search from stdin if none specified')

        pattern_group = self._parser.add_argument_group('Pattern selection and interpretation')
        pattern_type = pattern_group.add_mutually_exclusive_group()
        pattern_type.add_argument('-E', '--extended-regexp', action='store_true',
                                help='PATTERNS are extended regular expressions')
        pattern_type.add_argument('-F', '--fixed-strings', action='store_true',
                                help='PATTERNS are strings')
        pattern_type.add_argument('-G', '--basic-regexp', action='store_true',
                                help='PATTERNS are basic regular expressions')
        pattern_group.add_argument('-e', '--regexp', dest='patterns_option', metavar='PATTERNS', type=str,
                                default=None,
                                help='use PATTERNS for matching')
        pattern_group.add_argument('-f', '--file', metavar='FILE', dest='patterns_file', type=str, default=None,
                                help='take PATTERNS from FILE')
        pattern_group.add_argument('-i', '--ignore-case', action='store_true',
                                help='ignore case distinctions in patterns and data')
        pattern_group.add_argument('--no-ignore-case', dest='ignore_case', action='store_false',
                                help='do not ignore case distinctions (default)')
        pattern_group.add_argument('-w', '--word-regexp', action='store_true',
                                help='match only whole words')
        pattern_group.add_argument('-x', '--line-regexp', action='store_true',
                                help='match only whole lines')
        pattern_group.add_argument('-z', '--null-data', action='store_true',
                                   help='a data line ends in 0 byte, not newline')

        misc_group = self._parser.add_argument_group('Miscellaneous')
        misc_group.add_argument('-s', '--no-messages', action='store_true', help='suppress error messages')
        misc_group.add_argument('-v', '--invert-match', action='store_true', help='select non-matching lines')
        # misc_group.add_argument('-V', '--version', action='store_true', help='display version information and exit')

        output_ctrl_grp = self._parser.add_argument_group('Output control')
        # output_ctrl_grp.add_argument('-m', '--max-count', metavar='NUM', type=int, default=None,
        #                              help='stop after NUM selected lines')
        # output_ctrl_grp.add_argument('-b', '--byte-offset', action='store_true',
        #                              help='print the byte offset with output lines')

        output_ctrl_grp.add_argument('-n', '--line-number', action='store_true', help='print line number with output lines')
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
        output_ctrl_grp.add_argument('--result-sep', type=str, metavar='SEP', default=': ',
                                    help='String to place between header info and and search output')
        output_ctrl_grp.add_argument('--name-num-sep', type=str, metavar='SEP', default=':',
                                    help='String to place between file name and line number when both are enabled')

        context_ctrl_grp = self._parser.add_argument_group('Context control')
        # context_ctrl_grp.add_argument('-B, --before-context=NUM', action='store_true', help='print NUM lines of leading context')
        # context_ctrl_grp.add_argument('-A, --after-context=NUM', action='store_true', help='print NUM lines of trailing context')
        # context_ctrl_grp.add_argument('-C, --context=NUM', action='store_true', help='print NUM lines of output context')
        context_ctrl_grp.add_argument('--color', '--colour', type=str, metavar='WHEN', nargs='?', default='auto', dest='color',
                                    choices=['always', 'never', 'auto'],
                                    help='use markers to highlight the matching strings;\n'
                                    'WHEN is \'always\', \'never\', or \'auto\'')
        # context_ctrl_grp.add_argument('-U', '--binary', action='store_true', help='do not strip CR characters at EOL (MSDOS/Windows)')

    def parse(self, cliargs, grep_object:Grep):
        '''
        Parses command line arguments into the given Grep object
        '''
        grep_object.reset()
        args = self._parser.parse_args(cliargs)

        if not args:
            return False

        # Pars patterns from all of the different options into a single list of patterns
        patterns = []
        if args.patterns_option is not None:
            # Set patterns to the option
            patterns.extend(_parse_patterns(args.patterns_option))
            # The first positional (patterns_positional) is a file
            args.file.insert(0, args.patterns_positional)
        elif args.patterns_positional is not None:
            # Set patterns to the positional
            patterns.extend(_parse_patterns(args.patterns_positional))

        if args.patterns_file is not None:
            if not os.path.isfile(args.patterns_file):
                print('Error: {} is not a file'.format(args.patterns_file), file=sys.stderr)
                return False
            with open(args.patterns_file, 'r') as fp:
                patterns.extend(_parse_patterns(fp.read()))

        if not patterns:
            self._parser.print_usage()
            print('Try --help for more information', file=sys.stderr)
            return False

        grep_object.add_patterns(patterns)

        if args.file:
            grep_object.add_files(args.file)

        if args.extended_regexp:
            grep_object.search_type = Grep.SearchType.EXTENDED_REGEXP
        elif args.fixed_strings:
            grep_object.search_type = Grep.SearchType.FIXED_STRINGS
        else:
            # Basic regexp is default if no type specified
            grep_object.search_type = Grep.SearchType.BASIC_REGEXP

        grep_object.ignore_case = args.ignore_case
        grep_object.word_regexp = args.word_regexp
        grep_object.line_regexp = args.line_regexp
        grep_object.no_messages = args.no_messages
        grep_object.invert_match = args.invert_match
        grep_object.output_line_numbers = args.line_number
        grep_object.output_file_name = args.with_filename

        if args.null_data:
            grep_object.end = b'\x00'
        else:
            grep_object.end = b'\n'
        grep_object.results_sep = args.result_sep
        grep_object.name_num_sep = args.name_num_sep

        if args.color == 'always':
            grep_object.color_output_mode = Grep.ColorOutputMode.ALWAYS
        elif args.color == 'never':
            grep_object.color_output_mode = Grep.ColorOutputMode.NEVER
        else:
            grep_object.color_output_mode = Grep.ColorOutputMode.AUTO

        return True

def main(cliargs):
    '''
    Performs Grep with given command line arguments
    Returns: 0 on success, non-zero integer on failure
    '''
    grep = Grep()
    grep_arg_parser = GrepArgParser()
    if not grep_arg_parser.parse(cliargs, grep):
        return 1
    else:
        return grep.execute()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
