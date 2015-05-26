// -*- mode: c++; coding: utf-8 -*-

#include <SoftwareSerial.h>

#define RRP_DISCOVER  0
#define RRP_SYN       1
#define RRP_OK        2
#define RRP_TOKEN     3
#define RRP_REQUEST   4
#define RRP_RESPONSE  5

#define RRP_MAX_MESSAGE_SIZE 128
#define RRP_BROADCAST_ADDR 255

typedef struct {
    byte source;
    byte size;
    byte data[RRP_MAX_MESSAGE_SIZE];
} Message;

class RS485Driver {
public:
    RS485Driver(byte rtsPin, byte rxPin, byte txPin);
    RS485Driver(byte rtsPin, byte rxPin, byte txPin, byte myAddress);
    void setMyAddr(byte addr) { _myAddress = addr; }
    void begin(uint16_t speed=19200);

    byte available();
    void receive_from(byte* address, byte** data, byte* size);
    byte send_to(const byte destination, const byte* data, const byte size);

private:
    void _enter_sync_mode();
    void _on_request(byte source);
    void _on_response(byte source);

    void _process();
    bool _wait_magic();
    bool _getc(char* c);

    byte _rtsPin;
    SoftwareSerial _rs485;
    byte _myAddress;
    Message _message;
};
