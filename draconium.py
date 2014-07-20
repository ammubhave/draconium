#!/usr/bin/env python
import argparse
import codecs
import os
from collections import namedtuple
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint

Tag = namedtuple('Tag', ['name', 'attrs', 'render'])


def _get_all_sources():
    SOURCES = []

    if config.SOURCES_FILES:
        for file in config.SOURCES_FILES:
            if not file.endswith(config.iext):
                file += config.iext
            SOURCES.append(config.SOURCES_FILES)

    if config.SOURCES_DIRS:
        for directory in config.SOURCES_DIRS:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith(".drac"):
                        SOURCES.append('%s/%s' % (root, file))

    SOURCES = set(SOURCES)
    return SOURCES


def _get_parser(out):
    class DraconiumParser(HTMLParser):
        def __init__(self):
            HTMLParser.__init__(self)
            self.stack = []
            self.out = out

        def handle_starttag(self, tag, attrs):
            if tag not in config.rules.tags:
                self.error('Tag %s not allowed' % tag)

            self.stack.append(Tag(
                name=tag,
                attrs=dict(attrs),
                render=lambda attrs, stack, body: config.rules.tags[tag].render(attrs, stack, body),
            ))

            #print "Start tag:", tag
            #for attr in attrs:
            #    print "     attr:", attr

        def handle_endtag(self, tag):
            data = ''
            last = self.stack.pop()

            while type(last) != Tag:
                data += last
                last = self.stack.pop()

            if last.name != tag:
                self.error('Unexpected %s, expected %s'
                           ' to close' % (tag, last.name))
            txt = last.render(
                attrs=last.attrs,
                stack=self.stack,
                body=data,
            )
            self.stack.append(txt)

        def handle_data(self, data):
            self.stack.append(data)
            #print "Data     :", data

        #def handle_comment(self, data):
            #print "Comment  :", data

        def handle_entityref(self, name):
            if name not in config.entityref_allowed:
                self.error('%s entity ref not allowed' % name)
            self.stack.append('&%s;' % name)
            c = unichr(name2codepoint[name])
            #print "Named ent:", c

        def handle_charref(self, name):
            self.stack.append('&%s;' % name)
            #if name.startswith('x'):
            #    c = unichr(int(name[1:], 16))
            #else:
            #    c = unichr(int(name))
            #print "Num ent  :", c

        def handle_eof(self):
            while len(self.stack) > 0:
                elem = self.stack.pop()
                if type(elem) != Tag:
                    self.out.write(elem)
                else:
                    self.error('Unrecognized data at the end')
            #print "EOF: " + str(self.stack)
            pass

    return DraconiumParser()


def process_file(file):
    tmpl = codecs.open(file[:-4] + config.oext, 'w', 'utf-8')
    parser = _get_parser(tmpl)
    txt = codecs.open(file, 'r', 'utf-8').read()
    if txt != '':  # Prevent no new line at EOF error
        parser.feed(txt)
        parser.close()
    tmpl.close()


def main():
    global config
    argparser = argparse.ArgumentParser(description=main.__doc__)
    argparser.add_argument('--config', dest='config', default='config.py',
                           help='the Draconium config file')
    argparser.add_argument('--iext', dest='iext',
                           help='file extension of draconium template')
    argparser.add_argument('--oext', dest='oext',
                           help='file extension of compiled template')
    args = argparser.parse_args()

    # Get Draconium config file
    if args.config.endswith('.py'):
        args.config = args.config[:-3]
    config = __import__(args.config)

    if args.iext:
        config.iext = args.iext
    if not hasattr(config, 'iext'):
        config.iext = 'drac'

    if args.oext:
        config.oext = args.oext
    if not hasattr(config, 'oext'):
        config.oext = 'tmpl'

    os.system('find . -name "*.pyc" -delete')
    print 'Compiling draconium cheetah .dtmpl templates...'
    os.system('cheetah c -R --iext dtmpl --nobackup')
    print

    SOURCES = _get_all_sources()
    print 'Compiling draconium templates...'
    for file in SOURCES:
        print '%s -> %s' % (file, file[:-len(config.iext)] + config.oext)
        process_file(file)

if __name__ == '__main__':
    main()
