#!/bin/bash

# Copy content result of article_fix.py script to clipboard
# (Requires xclip)

./article_fix.py "$@" | tee >(tail -n+2 | head -n-2 | xclip -selection clipboard)

read -p "Done? -- $1"
