// -*- mode: c++; coding: utf-8 -*-

#include <Arduino.h>
#include <RRP.h>

// FIXME: add support for responses

const char* MAGIC = "RRP";

RS485Driver::RS485Driver(byte rtsPin, byte rxPin, byte txPin, byte myAddress) :
    _rtsPin(rtsPin),
    _rs485(rxPin, txPin),
    _myAddress(myAddress) {
}

void
RS485Driver::begin(uint16_t speed) {
    _rs485.begin(speed);

    // set as reader
    pinMode(_rtsPin, OUTPUT);
    digitalWrite(_rtsPin, LOW);
}


byte
RS485Driver::available() {
    _process();
    return _message.size;
}

void
RS485Driver::receive_from(byte* address, byte** data, byte* size) {
    _process();

    *address = _message.source;
    *data = _message.data;
    *size = _message.size;

    _message.size = 0;
}

#define GETC_OR_CONTINUE(c) do {		\
    if (!_getc((char*)&c))			\
	continue;				\
    } while(0);

byte
RS485Driver::send_to(const byte to, const byte* data, const byte size) {
    _process();

    uint32_t now = millis();
    do {
	if (!_wait_magic())
	    continue;

	byte source, destination, type;
	GETC_OR_CONTINUE(source);
	GETC_OR_CONTINUE(destination);
	GETC_OR_CONTINUE(type);

	// if message is not for me, discard it
	if (destination != _myAddress) {
	    if (type == RRP_REQUEST || type == RRP_RESPONSE) {
		byte c, size;
		GETC_OR_CONTINUE(size);
		for (byte i=0; i<size; i++)
		    GETC_OR_CONTINUE(c);
	    }
	    continue;
	}

	// only process it if is a TOKEN message
	if (type != RRP_TOKEN)
	    continue;

	// send message
	digitalWrite(_rtsPin, HIGH);
	byte body[4] = {_myAddress, to, RRP_REQUEST, size};
	_rs485.write(MAGIC);
	_rs485.write(body, 4);
	_rs485.write(data, size);
	_rs485.flush();
	digitalWrite(_rtsPin, LOW);

	return size;

    } while(abs(millis() - now) < 200);

    return 0;
}

void
RS485Driver::_enter_sync_mode() {
    // flush input queue
    char c;
    while (_getc(&c));

    // wait some time to arrive data
    uint32_t now = millis();
    do {
	if (!_wait_magic())
	    continue;

	byte source, destination, type;
	GETC_OR_CONTINUE(source);
	GETC_OR_CONTINUE(destination);
	GETC_OR_CONTINUE(type);

	// if message is not for me, discard it
	if (destination != _myAddress) {
	    if (type == RRP_REQUEST || type == RRP_RESPONSE) {
		byte c, size;
		GETC_OR_CONTINUE(size);
		for (byte i=0; i<size; i++)
		    GETC_OR_CONTINUE(c);
	    }
	    continue;
	}

	// only process it if is a SYN message
	if (type != RRP_SYN)
	    continue;

	// send an OK response
	digitalWrite(_rtsPin, HIGH);
	byte message[3] = {_myAddress, 0, RRP_OK};
	_rs485.write(MAGIC);
	_rs485.write(message, 3);
	_rs485.flush();
	digitalWrite(_rtsPin, LOW);
	return;

    } while(abs(millis() - now) < 15000);
}

#define GETC_OR_RETURN(c) do {			\
    if (!_getc((char*)&c))			\
	return;					\
    } while(0);

void
RS485Driver::_on_request(byte source) {
    _message.source = source;
    _message.size = 0;
    GETC_OR_RETURN(_message.size);

    for(byte i=0; i<_message.size; i++) {
	if (!_getc((char*)(_message.data + i))) {
	    _message.size = 0;
	    return;
	}
    }
}

void
RS485Driver::_on_response(byte source) {
    // FIXME: not implemented
}

void
RS485Driver::_process() {
    while (_rs485.available()) {
	if (!_wait_magic())
	    return;

	byte source, destination, type;
	GETC_OR_RETURN(source);
	GETC_OR_RETURN(destination);
	GETC_OR_RETURN(type);

	// if message is not for me, discard it
	if (destination != _myAddress && destination != RRP_BROADCAST_ADDR) {
	    if (type == RRP_REQUEST || type == RRP_RESPONSE) {
		byte c, size;
		GETC_OR_RETURN(size);
		for (byte i=0; i<size; i++)
		    GETC_OR_RETURN(c);
	    }
	    continue;
	}

	if (type == RRP_DISCOVER)
	    return _enter_sync_mode();

	else if (type == RRP_REQUEST)
	    _on_request(source);

	else if (type == RRP_RESPONSE)
	    _on_response(source);
    }
}

bool
RS485Driver::_wait_magic() {
    byte index = 0;
    char c;

    while (index < 3) {
	if (!_getc(&c))
	    return false;

	if (c != MAGIC[index]) {
	    index = 0;
	    continue;
	}
	index++;
    }

    return true;
}

bool
RS485Driver::_getc(char* c) {
    uint32_t now = millis();
    do {
    	if (!_rs485.available())
    	    continue;
    	*c = _rs485.read();
    	return true;
    } while (abs(millis() - now) < 5);

    return false;
}
