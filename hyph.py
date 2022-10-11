#!/usr/bin/env python

import re
import sys
from isbn_hyphenate import hyphenate

EXTRA_CHARS = re.compile(r'[^0-9Xx]+')

isbn = EXTRA_CHARS.sub('', sys.argv[1])
print(hyphenate(isbn))
