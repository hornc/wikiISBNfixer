#!/bin/bash
datetag=$(date +'%Y%m%d')
wget "https://en.wikipedia.org/wiki/Wikipedia:WikiProject_Check_Wikipedia/ISBN_errors" -O ISBN_errors_${datetag}.html
wget "https://en.wikipedia.org/w/index.php?title=Wikipedia:WikiProject_Check_Wikipedia/ISBN_errors&action=history&limit=20" -O ISBN_errors_history_${datetag}.html

echo "Classes of ISBN issues (by first character)"
egrep -o '<li>[0-9]+ x ISBN..' <(egrep -v "ISBN\]\].\[\[" ISBN_errors_${datetag}.html) | sed 's/<li>[0-9]\+ x ISBN//' | sort | uniq -c | sed "s/^\s*\([0-9]\+\)/\1\t/;s/=/'=/"

echo
echo "Top articles with ISBN issues:"
egrep '<li>[0-9]+ x ISBN..' <(cat ISBN_errors_${datetag}.html) | egrep -o "\">[^<]*</a>" | sed 's/">//;s/<\/a>//' | sort | uniq -c | sed 's/^\s*\([0-9]\+\)/\1\t/' | sort -rg | head -n200


echo
echo "Page size by date:"
echo -e "Date\tPage Size"
fgrep data-mw-bytes ISBN_errors_history_${datetag}.html | egrep -o "ISBN errors\">..:.., [^<]+.*data-mw-bytes=\"[0-9]+"| sed 's/ISBN errors">..:.., \([^<]\+\).*data-mw-bytes="\([0-9]\+\)$/\1\t\2/'

