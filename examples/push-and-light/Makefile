# -*- mode: makefile-gmake; coding: utf-8 -*-

PROJECT_DIR   = ../../

BOARD_TAG     = atmega328
ARDUINO_DIR   = /usr/share/arduino
PORT         ?= /dev/ttyUSB0
MONITOR_PORT  = $(PORT)

USER_LIB_PATH = $(HOME)/Arduino/libraries
ARDUINO_LIBS  = TinkerKit SoftwareSerial RRP

CFLAGS       += -DADDR=$(ADDR)
CXXFLAGS      = $(CFLAGS)

all:

upload-all:
	rm -f build-atmega328/*.o
	$(MAKE) upload PORT=/dev/ttyUSB0 ADDR=1
	rm -f build-atmega328/*.o
	$(MAKE) upload PORT=/dev/ttyUSB1 ADDR=2
	rm -f build-atmega328/*.o
	$(MAKE) upload PORT=/dev/ttyUSB2 ADDR=3

include $(ARDUINO_DIR)/Arduino.mk
