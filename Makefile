# -*- mode: makefile-gmake; coding: utf-8 -*-

DESTDIR ?= ~

all:

install:
	install -d $(DESTDIR)/usr/bin
	install -m 555 tools/rrp-shell.py $(DESTDIR)/usr/bin/rrp-shell

	install -d $(DESTDIR)/usr/share/arduino/libraries/RRP
	install -m 644 src/rrp.cpp $(DESTDIR)/usr/share/arduino/libraries/RRP
	install -m 644 src/rrp.h $(DESTDIR)/usr/share/arduino/libraries/RRP

	install -d $(DESTDIR)/usr/share/rrp
	install -m 644 tools/rrp-shell.config $(DESTDIR)/usr/share/rrp
