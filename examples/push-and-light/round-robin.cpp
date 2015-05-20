// -*- mode: c++; coding: utf-8 -*-

#include <Arduino.h>
#include <TinkerKit.h>
#include <rrp.h>

//
// NOTE: define ADDR on compilation time to be 1, 2 or 3
//

RS485Driver rs485(2, 3, 4, ADDR);
TKButton button(I0);
TKLed led(O0);

void
process_message(byte* message, byte size) {
    {
	message[size] = 0;
	Serial.print("message: ");
	Serial.println((const char*)message);
    }

    if (strncmp((const char*)message, "ON", size) == 0)
	led.on();
    else
	led.off();
}

void
setup() {
    Serial.begin(115200);
    rs485.begin(19200);

    Serial.print("\nsetup done --\n");
}

void
loop() {
    static bool state = false;
    bool newState = button.readSwitch();

    if (newState != state) {
	byte dst[4] = {1, 2, 3, 1};
	const char* message = newState ? "ON" : "OFF";
	rs485.send_to(dst[ADDR], (const byte*)message, strlen(message));
	state = newState;
    }

    if (rs485.available()) {
	byte src;
	byte* message;
	byte size;

	rs485.receive_from(&src, &message, &size);
	process_message(message, size);
    }
}
