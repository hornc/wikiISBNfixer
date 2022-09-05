#!/bin/bash
# Script to fetch Wikipedia ISBN errors page and history
# and process the data to TSV for spreadsheet tabulation and charting.

datetag=$(date +'%Y%m%d')
historyLimit=20
topArticleLimit=200

wget "https://en.wikipedia.org/wiki/Wikipedia:WikiProject_Check_Wikipedia/ISBN_errors" -O ISBN_errors_${datetag}.html
wget "https://en.wikipedia.org/w/index.php?title=Wikipedia:WikiProject_Check_Wikipedia/ISBN_errors&action=history&limit=$historyLimit" -O ISBN_errors_history_${datetag}.html

echo "Classes of ISBN issues (by first character)"
manualLinks=$(fgrep -c 'x ISBN [[ISBN (identifier)|ISBN]]' ISBN_errors_${datetag}.html)
classes=$(egrep -o '<li>[0-9]+ x ISBN..' ISBN_errors_${datetag}.html | sed 's/<li>[0-9]\+ x ISBN//' | sort | uniq -c | sed "s/^\s*\([0-9]\+\)/\1\t/;s/=/'=/")
rawLinks=$(echo "$classes" | fgrep '[' | cut -f1)
otherLinks=$(($rawLinks - 2 * $manualLinks))

echo -e "Manual ISBN links\t$manualLinks"
echo -e "Other links\t$otherLinks"
echo "$classes" | fgrep -v '['

echo
echo "Top articles with ISBN issues:"
egrep '<li>[0-9]+ x ISBN..' <(cat ISBN_errors_${datetag}.html) | egrep -o "\">[^<]*</a>" | sed 's/">//;s/<\/a>//' | sort | uniq -c | sed 's/^\s*\([0-9]\+\)/\1\t/' | sort -rg | head -n$topArticleLimit


echo
echo "Page size by date:"
echo -e "Date\tPage Size"
fgrep data-mw-bytes ISBN_errors_history_${datetag}.html | egrep -o "ISBN errors\">..:.., [^<]+.*data-mw-bytes=\"[0-9]+"| sed 's/ISBN errors">..:.., \([^<]\+\).*data-mw-bytes="\([0-9]\+\)$/\1\t\2/'

