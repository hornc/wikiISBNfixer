#!/usr/bin/env python3

import argparse
import re
import requests
import sys
from isbn_hyphenate import hyphenate
from isbn_hyphenate.isbn_hyphenate import IsbnMalformedError

API = "https://en.wikipedia.org/w/api.php?action=query&prop=revisions&rvlimit=1&rvprop=content&format=json&titles="

#                        [[OCLC (identifier)|OCLC]]&nbsp;1183423539
OCLCBLOCK = re.compile(r'( *\[\[[^\|\[]*\|OCLC\]\][^0-9]*([0-9]+))')
OCLCBARE  = re.compile(r'( *OCLC[^=\|]([0-9]+))')

#                        [[ISSN (identifier)|ISSN]]&nbsp;0015-587X
ISSNBLOCK = re.compile(r'( *\[\[ISSN \(identifier\)\|ISSN\]\][^0-9]*([0-9]{4}-[0-9Xx]{4}))')
ISSNBARE  = re.compile(r'( *ISSN[^=\|]([0-9]{4}-[0-9Xx]{4}))')

# [[Doi (identifier)|doi]]:10.2307/j.ctt4cgmxc.17
DOIBLOCK = re.compile(r'(\[\[Doi \(identifier\)\|doi\]\]:([^ <]+[^ ,\.<\']))')
# DOI: https://doi.org/10.1075/cogls.00027.hov
DOIBARE  = re.compile(r'(?:[^=]|^)((?:DOI: |<nowiki>)?https?://doi.org/([^ <]+[^ ,\.<\'])(?:</nowiki>)?)')
DOISIMPLE = re.compile(r'(doi:([^ <]+[^ ,\.<\']))')


# [[ASIN (identifier)|ASIN]]&nbsp;B0026B3KAI
ASINBLOCK = re.compile(r'(\[\[ASIN \(identifier\)\|ASIN\]\][^0-9A-Z]*([0-9A-Z]+))')
AMAZON_LINK = re.compile(r'(\[https://www.amazon.*ISBN ([0-9xX-]+)[^0-9\]]*\])')
BOOKSELLER_LINK = re.compile(r'(\[http[^\]\[]*ISBN ([0-9xX -]+)[^0-9\]]*\])')

# ISBN 1326613804, 9781326613808  source: wiki:List of Philippine mythological figures
ISBN_DUAL = re.compile(r'((?:{{)?ISBN.[0-9xX]{10}(?:}})?, (97[0-9]{11}))')

ISBN_NOWIKI = re.compile(r'(\(?<nowiki>ISBN\s*([0-9xX -]+)</nowiki>\)?)')

# [[ISBN (identifier)|ISBN]] [[Special:BookSources/978-1-4314-0578-7|<bdi>978-1-4314-0578-7</bdi>]]
ISBN_SOURCES = re.compile(r'((?:\[\[[^\[]*)?ISBN(?:[^\]]*\]\][^\[]*)?\s*\[\[Special:BookSources/[0-9xX-]+\|[^0-9]*([0-9xX-]+)[^0-9\]]*\]\])')
SBN_SOURCES = re.compile(r'(\[\[SBN[^\]]*\]\][^\[]*\[\[Special:BookSources/[0-9xX-]+\|[^0-9]*([0-9xX-]+)[^0-9\]]*\]\])')


#[[Spezial:ISBN Suche/388022174X|ISBN 3-88022-174-X]]
ISBN_SOURCES_DE = re.compile(r'(\[\[(?:\:de\:)?Spezial:ISBN[ -]Suche/[0-9xX-]+\|[^0-9]*([0-9xX-]+)[^0-9\]]*\]\])')
ISBN_SOURCES_FR = re.compile(r'(\[\[:fr:Spécial:Ouvrages de référence/[0-9xX-]+\|[^0-9]*([0-9xX-]+)[^0-9\]]*\]\])')
ISBN_SOURCES_IT = re.compile(r'(\[\[:it:Speciale:RicercaISBN/[0-9xX-]+\|[^0-9]*([0-9xX-]+)[^0-9\]]*\]\])')
ISBN_SOURCES_NN = re.compile(r'((?:\[\[International Standard Book Number\|ISBN\]\] )\[\[Sp[eé][cz][^\/]*\/[0-9xX-]+\|[^0-9]*([0-9xX-]+)[^0-9\]]*\]\])')
ISBN_SOURCES_OTHER = re.compile(r'(\[\[Spe[cz][^\/]*\/([0-9xX-]+)\|(?:ISBN )?[0-9xX-]*\]\])')
ISBN_OTHER = re.compile(r'(\[\[Special:BookSources\|ISBN-1.: ([0-9xX-]+)[^0-9\]]*\]\])')


ISBN_EAN = re.compile(r'((?:ISBN/)?EAN:? (978[0-9-]+))')

ISBN_1x = re.compile(r'(ISBN.?1[30]:?\s?([0-9xX-]{10,}))')
ISBN_PLAIN = re.compile(r'[^{](\'*ISBN(?:&nbsp;|-1[03])?:?\'*[\s\|:]*([0-9–‐-]+[0-9xX]))', re.IGNORECASE)
ISBN_EQUALS = re.compile(r'[^\|]\s*(isbn\s*=\s*([0-9-]+[0-9xX]))', re.IGNORECASE)  # isbn= outside a template
HYPHENATE_EXISTING = re.compile(r'({{\s*ISBN\s*\|\s*([0-9xX-]+)}})')
ISBN_SPACED = re.compile(r'(ISBN ((97[89])? ?([0-9]+ )+[0-9xX]+))(?:[<,\.]|$)')
ISBN_BDI = re.compile(r'(ISBN <bdi>([0-9xX-]+)</bdi>)')

# [[ISBN]] 3-87034-047-9
ISBN_LINK = re.compile(r'(\[\[(?:International Standard Book Number\|)?ISBN\]\]\s*([0-9xX-]+))')

# cite ISBN with stray LTR Unicode \u200e
CITE_ISBN = re.compile(r'(\|\s*isbn\s*=(?:\u200e)?\s*([0-9xX–-]+))')

# Journal book review ISBN:
REVIEW_TITLE = re.compile(r'(([Cc]ite journal[^}]+title\s*=\s*[^|]*ISBN[^|]*))')


# for https://en.wikipedia.org/wiki/Reem_Saleh_Al_Gurg
# (ISBN[[خاص:مصادر كتاب/9789948367512|9789948367512]])
#ISBNBLOCK = re.compile(r'(\(ISBN\[\[[^\|]+\|([0-9xX -]+)\]\]\))')

LIST_MARKER = re.compile(r'^([*#]+)([^*# ]|$)')


def isbn_template(isbn, sbn=False, table=False, **kwargs):
    isbn = isbn.replace('–', '-')
    isbn = isbn.replace(' ', '')
    if not sbn and len(isbn) == 9:
        isbn = '0' + isbn
    template = '{{ISBN|'
    if sbn:
        template = '{{SBN|'
    elif table:
        template = '{{ISBNT|'
    try:
        return template + hyphenate(isbn) + '}}'
    except IsbnMalformedError as e:
        return template + isbn + '}}'
    except Exception as e:
        print(f"{isbn}: {e}")
        raise e


def sbn_template(sbn):
    return isbn_template(sbn, sbn=True, **kwargs)


def cite_isbn(isbn, **kwargs):
    isbn = isbn.replace('–', '-')
    try:
        return '|isbn=' + hyphenate(isbn)
    except Exception as e:
        print(f"{isbn}: {e}")
        raise e


def quote_isbn(cite, **kwargs):
    return cite.replace('ISBN', '{{text|ISBN}}')


def oclc_template(ocn, **kwargs):
    # TODO: use {{OCLC search link| on --table
    return ' {{OCLC|' + ocn + '}}'


def issn_template(issn, **kwargs):
    # TODO: use {{ISSN link| on --table
    return ' {{ISSN|' + issn + '}}'


def asin_template(asin, **kwargs):
    return '{{ASIN|' + asin + '}}'


def doi_template(doi, **kwargs):
    return '{{doi|' + doi + '}}'


# (matcher regex, fixer fn.)
FIXERS = [
        (OCLCBLOCK, oclc_template),
        (OCLCBARE, oclc_template),
        (ISSNBLOCK, issn_template),
        (ISSNBARE, issn_template),
        (DOIBLOCK, doi_template),
        (DOIBARE, doi_template),
        (DOISIMPLE, doi_template),
        (ASINBLOCK, asin_template),
        (AMAZON_LINK, isbn_template),
        (BOOKSELLER_LINK, isbn_template),
        (REVIEW_TITLE, quote_isbn),
        (ISBN_DUAL, isbn_template),
        (ISBN_1x, isbn_template),
        (ISBN_SOURCES, isbn_template),
        (SBN_SOURCES, sbn_template),
        (ISBN_SOURCES_DE, isbn_template),
        (ISBN_SOURCES_FR, isbn_template),
        (ISBN_SOURCES_IT, isbn_template),
        (ISBN_SOURCES_NN, isbn_template),
        (ISBN_SOURCES_OTHER, isbn_template),
        (ISBN_OTHER, isbn_template),
        (ISBN_NOWIKI, isbn_template),
        (ISBN_LINK, isbn_template),
        (ISBN_BDI, isbn_template),
        (ISBN_EAN, isbn_template),
        (HYPHENATE_EXISTING, isbn_template),
        (CITE_ISBN, cite_isbn),
        (ISBN_SPACED, isbn_template),
        (ISBN_PLAIN, isbn_template),
        (ISBN_EQUALS, isbn_template),

]


def get_markup(r_json):
    for p, content in r_json.get('query').get('pages').items():
        return content.get('revisions')[0]['*']


def strip_small(s):
    return s.replace('<small>', '').replace('</small>', '')


def main():
    parser = argparse.ArgumentParser(description="Wikipedia article ISBN fixer / formatter.")
    parser.add_argument('article', help='Wikipedia article title to process.')
    parser.add_argument('--changes', '-c', help='Show only changes made.', action='store_true')
    parser.add_argument('--nobullet', '-B', help='No bullet spacing changes.', action='store_true')
    parser.add_argument('--raw', '-r', help='Show raw article markup without making any changes..', action='store_true')
    parser.add_argument('--table', '-t', help='Use ISBNT template for ISBNs within tables: https://en.wikipedia.org/wiki/Template:ISBNT', action='store_true')
    args = parser.parse_args()

    articlename = args.article

    r = requests.get(API + articlename)
    print(r) 
    f = get_markup(r.json())
    if args.raw:
        print(f)
        exit(0)

    changes = 0
    for line in f.split('\n'):
        orig = line
        # space after list items:
        if not args.nobullet:
            if m := LIST_MARKER.match(line):
                if len(line) == 1:
                    changes += 1
                    continue
                else:
                    line = line.replace(m[1], m[1] + ' ', 1)

        for regex, template_fn in FIXERS:
            all_m = regex.findall(line)
            for m in all_m:
                if m:  # If regex matches, replace the match m[0] with fn(m[1])
                    target = m[0]
                    template = template_fn(m[1], table=args.table)
                    line = line.replace(target, template)
                    line = strip_small(line)
        if line != orig:
            changes += 1
        if not args.changes or (line != orig):
            print(line)
    print()
    print('LINES CHANGED:', changes)


if __name__ == '__main__':
    main()
