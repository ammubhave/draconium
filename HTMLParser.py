"""A parser for HTML and XHTML."""

# This file is based on sgmllib.py, but the API is slightly different.

# XXX There should be a way to distinguish between PCDATA (parsed
# character data -- the normal case), RCDATA (replaceable character
# data -- only char and entity references and end tags are special)
# and CDATA (character data -- only end tags are special).


import markupbase
import re

# Regular expressions used for parsing

interesting_normal = re.compile('[&<]')
incomplete = re.compile('&[a-z#]')

entityref = re.compile('&([a-z][-.a-z0-9]*)[^a-z0-9]')
charref = re.compile('&#(?:[0-9]+|[xX][0-9a-f]+)[^0-9a-f]')

starttagopen = re.compile('<[a-z]')
piclose = re.compile('>')
commentclose = re.compile(r'-->')

# see http://www.w3.org/TR/html5/tokenization.html#tag-open-state
# and http://www.w3.org/TR/html5/tokenization.html#tag-name-state
# note: if you change tagfind/attrfind remember to update locatestarttagend too
tagfind = re.compile('([a-z][^\t\n\r\f />\x00]*)(?:\s|/(?!>))*')
# this regex is currently unused, but left for backward compatibility
tagfind_tolerant = re.compile('[a-z][^\t\n\r\f />\x00]*')

attrfind = re.compile(
    r'((?<=[\'"\s/])[^\s/>][^\s/=>]*)(\s*=+\s*'
    r'(\'[^\']*\'|"[^"]*"|(?![\'"])[^>\s]*))?(?:\s|/(?!>))*')

locatestarttagend = re.compile(r"""
  <[a-z][^\t\n\r\f />\x00]*       # tag name
  (?:[\s/]*                          # optional whitespace before attribute name
    (?:(?<=['"\s/])[^\s/>][^\s/=>]*  # attribute name
      (?:\s*=+\s*                    # value indicator
        (?:'[^']*'                   # LITA-enclosed value
          |"[^"]*"                   # LIT-enclosed value
          |(?!['"])[^>\s]*           # bare value
         )
       )?(?:\s|/(?!>))*
     )*
   )?
  \s*                                # trailing whitespace
""", re.VERBOSE)
endendtag = re.compile('>')
# the HTML 5 spec, section 8.1.2.2, doesn't allow spaces between
# </ and the tag name, so maybe this should be fixed
endtagfind = re.compile('</([a-z][-.a-z0-9:_]*)>')


class HTMLParseError(Exception):
    """Exception raised for all parse errors."""

    def __init__(self, msg, position=(None, None)):
        assert msg
        self.msg = msg
        self.lineno = position[0]
        self.offset = position[1]

    def __str__(self):
        result = self.msg
        if self.lineno is not None:
            result = result + ", at line %d" % self.lineno
        if self.offset is not None:
            result = result + ", column %d" % (self.offset + 1)
        return result


class HTMLParser(markupbase.ParserBase):
    """Find tags and other markup and call handler functions.

    Usage:
        p = HTMLParser()
        p.feed(data)
        ...
        p.close()

    Start tags are handled by calling self.handle_starttag() or
    self.handle_startendtag(); end tags by self.handle_endtag().  The
    data between tags is passed from the parser to the derived class
    by calling self.handle_data() with the data as argument (the data
    may be split up in arbitrary chunks).  Entity references are
    passed by calling self.handle_entityref() with the entity
    reference as the argument.  Numeric character references are
    passed to self.handle_charref() with the string containing the
    reference as the argument.
    """

    def __init__(self):
        """Initialize and reset this instance."""
        self.reset()

    def reset(self):
        """Reset this instance.  Loses all unprocessed data."""
        self.rawdata = ''
        self.lasttag = '???'
        self.interesting = interesting_normal
        markupbase.ParserBase.reset(self)

    def feed(self, data):
        r"""Feed data to the parser.

        Call this as often as you want, with as little or as much text
        as you want (may include '\n').
        """
        self.rawdata = self.rawdata + data
        self.goahead(0)

    def close(self):
        """Handle any buffered data."""
        self.goahead(1)

    def error(self, message):
        raise HTMLParseError(message, self.getpos())

    __starttag_text = None

    def get_starttag_text(self):
        """Return full source of start tag: '<...>'."""
        return self.__starttag_text

    # Internal -- handle data as far as reasonable.  May leave state
    # and data to be processed by a subsequent call.  If 'end' is
    # true, force handling all data as if followed by EOF marker.
    def goahead(self, end):
        rawdata = self.rawdata
        i = 0
        n = len(rawdata)
        while i < n:
            match = self.interesting.search(rawdata, i)  # < or & or TODO: #
            if match:
                j = match.start()
            else:
                j = n
            if i < j:
                self.handle_data(rawdata[i:j])
            i = self.updatepos(i, j)
            if i == n:
                break
            startswith = rawdata.startswith
            if startswith('<', i):
                if starttagopen.match(rawdata, i):  # < + letter
                    k = self.parse_starttag(i)
                elif startswith("</", i):
                    k = self.parse_endtag(i)
                elif startswith("<!--", i):
                    k = self.parse_comment(i)
                elif startswith("<?", i):
                    self.error('<? tags are not recognized')
                elif startswith("<!", i):
                    self.error('HTML declarations are not recognized')
                elif (i + 1) < n:
                    self.error('Unexpected < found, possible reasons:'
                               ' uppercase names, not used &lt;')
                else:
                    break
                if k < 0:
                    self.error('Unexpected < found, please escape using &lt;')
                i = self.updatepos(i, k)
            elif startswith("&#", i):
                match = charref.match(rawdata, i)
                if match:
                    name = match.group()[2:-1]
                    k = match.end()
                    if not startswith(';', k-1):
                        self.error('Expected ; after character ref')
                    self.handle_charref(name)
                    i = self.updatepos(i, k)
                    continue
                self.error('Unexpected &# found, please escape & using &amp;')
            elif startswith('&', i):
                match = entityref.match(rawdata, i)
                if match:
                    name = match.group(1)
                    k = match.end()
                    if not startswith(';', k-1):
                        self.error('Expected ; after entity ref')
                    self.handle_entityref(name)
                    i = self.updatepos(i, k)
                    continue
                self.error('Unexpected & found, please escape using &amp;')
            else:
                assert 0, "interesting.search() lied"
        # end while
        if end and i < n:
            self.handle_data(rawdata[i:n])
            i = self.updatepos(i, n)
        self.rawdata = rawdata[i:]
        if end:
            self.handle_eof()

    # Internal -- parse bogus comment, return length or -1 if not terminated
    # see http://www.w3.org/TR/html5/tokenization.html#bogus-comment-state
    def parse_bogus_comment(self, i, report=1):
        rawdata = self.rawdata
        if rawdata[i:i+2] not in ('<!', '</'):
            self.error('unexpected call to parse_comment()')
        pos = rawdata.find('>', i+2)
        if pos == -1:
            return -1
        if report:
            self.handle_comment(rawdata[i+2:pos])
        return pos + 1

    # Internal -- handle starttag, return end or -1 if not terminated
    def parse_starttag(self, i):
        self.__starttag_text = None
        endpos = self.check_for_whole_start_tag(i)
        if endpos < 0:
            return endpos
        rawdata = self.rawdata
        self.__starttag_text = rawdata[i:endpos]

        # Now parse the data between i+1 and j into a tag and attrs
        attrs = []
        match = tagfind.match(rawdata, i+1)
        assert match, 'unexpected call to parse_starttag()'
        k = match.end()
        self.lasttag = tag = match.group(1).lower()

        while k < endpos:
            m = attrfind.match(rawdata, k)
            if not m:
                break
            attrname, rest, attrvalue = m.group(1, 2, 3)
            if not rest:
                attrvalue = None
            elif attrvalue[:1] == '\'' == attrvalue[-1:]:
                self.error('Use double quotation marks " for attribute values')
            elif attrvalue[:1] == '"' == attrvalue[-1:]:
                attrvalue = attrvalue[1:-1]
            if attrvalue:
                attrvalue = self.unescape(attrvalue)
            attrs.append((attrname.lower(), attrvalue))
            k = m.end()

        end = rawdata[k:endpos].strip()
        if end not in (">", "/>"):
            lineno, offset = self.getpos()
            if "\n" in self.__starttag_text:
                lineno = lineno + self.__starttag_text.count("\n")
                offset = len(self.__starttag_text) \
                    - self.__starttag_text.rfind("\n")
            else:
                offset = offset + len(self.__starttag_text)
            self.handle_data(rawdata[i:endpos])
            return endpos
        if end.endswith('/>'):
            # XHTML-style empty tag: <span attr="value" />
            self.handle_startendtag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
        return endpos

    # Internal -- check to see if we have a complete starttag; return end
    # or -1 if incomplete.
    def check_for_whole_start_tag(self, i):
        rawdata = self.rawdata
        m = locatestarttagend.match(rawdata, i)
        if m:
            j = m.end()
            next = rawdata[j:j+1]
            if next == ">":
                return j + 1
            if next == "/":
                if rawdata.startswith("/>", j):
                    return j + 2
                if rawdata.startswith("/", j):
                    # buffer boundary
                    return -1
                # else bogus input
                self.updatepos(i, j + 1)
                self.error("malformed empty start tag")
            if next == "":
                # end of input
                return -1
            if next in ("abcdefghijklmnopqrstuvwxyz=/"
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                # end of input in or before attribute value, or we have the
                # '/' from a '/>' ending
                return -1
            if j > i:
                return j
            else:
                return i + 1
        raise AssertionError("we should not get here!")

    # Internal -- parse endtag, return end or -1 if incomplete
    def parse_endtag(self, i):
        rawdata = self.rawdata
        assert rawdata[i:i+2] == "</", "unexpected call to parse_endtag"
        match = endendtag.search(rawdata, i+1)  # >
        if not match:
            self.error('</ not closed')
        gtpos = match.end()
        match = endtagfind.match(rawdata, i)  # </ + tag + >
        if not match:
            self.error('Invalid end tag')

        elem = match.group(1)

        self.handle_endtag(elem)
        return gtpos

    # Overridable -- finish processing of start+end tag: <tag.../>
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    # Overridable -- handle start tag
    def handle_starttag(self, tag, attrs):
        pass

    # Overridable -- handle end tag
    def handle_endtag(self, tag):
        pass

    # Overridable -- handle character reference
    def handle_charref(self, name):
        pass

    # Overridable -- handle entity reference
    def handle_entityref(self, name):
        pass

    # Overridable -- handle data
    def handle_data(self, data):
        pass

    # Overridable -- handle comment
    def handle_comment(self, data):
        pass

    # Overridable -- handle declaration
    def handle_decl(self, decl):
        pass

    def unknown_decl(self, data):
        pass

    def handle_eof(self):
        pass

    # Internal -- helper to remove special character quoting
    entitydefs = None

    def unescape(self, s):
        if '&' not in s:
            return s

        def replaceEntities(s):
            s = s.groups()[0]
            try:
                if s[0] == "#":
                    s = s[1:]
                    if s[0] in ['x', 'X']:
                        c = int(s[1:], 16)
                    else:
                        c = int(s)
                    return unichr(c)
            except ValueError:
                return '&#'+s+';'
            else:
                # Cannot use name2codepoint directly, because HTMLParser supports apos,
                # which is not part of HTML 4
                import htmlentitydefs
                if HTMLParser.entitydefs is None:
                    entitydefs = HTMLParser.entitydefs = {'apos':u"'"}
                    for k, v in htmlentitydefs.name2codepoint.iteritems():
                        entitydefs[k] = unichr(v)
                try:
                    return self.entitydefs[s]
                except KeyError:
                    return '&'+s+';'

        return re.sub(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));", replaceEntities, s)
