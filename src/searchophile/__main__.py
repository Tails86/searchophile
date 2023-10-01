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

import sys
from .search import main as search_main

def main(cliargs=None) -> int:
    ''' Search main using arguments from sys.argv '''
    if cliargs is None:
        cliargs = sys.argv[1:]

    try:
        return search_main(cliargs)
    except KeyboardInterrupt:
        # User quit - no need to print error, just exit gracefully
        print('')
        return 0

def csearch_main() -> int:
    ''' Search main specifically for C-file extensions '''
    return main(['-n', '--regexpath', '^.*\.(h|hpp|c|cpp|cxx|cc)$'] + sys.argv[1:])

def pysearch_main() -> int:
    ''' Search main specifically for C-file extensions '''
    return main(['-n', '--name', '*.py'] + sys.argv[1:])

if __name__ == '__main__':
    # Execute above
    sys.exit(main())
