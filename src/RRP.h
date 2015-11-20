// -*- mode: c++; coding: utf-8 -*-

#ifndef _RRP_H_
#define _RRP_H_

#include <SoftwareSerial.h>
#include <stdint.h>

#define RRP_DISCOVER  0
#define RRP_SYN       1
#define RRP_OK        2
#define RRP_TOKEN     3
#define RRP_REQUEST   4
#define RRP_RESPONSE  5

#define RRP_MAX_MESSAGE_SIZE 128
#define RRP_BROADCAST_ADDR 255

typedef struct {
    uint8_t source;
    uint8_t size;
    uint8_t data[RRP_MAX_MESSAGE_SIZE];
} Message;

class RS485Driver {
public:
    RS485Driver(uint8_t rtsPin, uint8_t rxPin, uint8_t txPin);
    RS485Driver(uint8_t rtsPin, uint8_t rxPin, uint8_t txPin, uint8_t myAddress);
    void setMyAddr(uint8_t addr) { _myAddress = addr; }
    void begin(uint16_t speed=19200);

    uint8_t available();
    void receive_from(uint8_t* address, uint8_t** data, uint8_t* size);
    uint8_t send_to(const uint8_t destination, const uint8_t* data, const uint8_t size);

private:
    void _enter_sync_mode();
    void _on_request(uint8_t source);
    void _on_response(uint8_t source);

    void _process();
    bool _wait_magic();
    bool _getc(char* c);

    uint8_t _rtsPin;
    SoftwareSerial _rs485;
    uint8_t _myAddress;
    Message _message;
};

#endif // _RRP_H_
