
This example uses three nodes (Arduino), each one with a push button
(Tinkerkit Button, I0) and a LED (Tinkerkit Led, O0). Those nodes are
connected to a RS-485 bus, connected on pins 2 (RTS), 3 (Rx) and 4
(Tx).

Each node is connected to an USB port (/dev/ttyUSB0 to /dev/ttyUSB2)
using a FTDI interface attached to Hardware UART (the builtin FTDI or
an external one). To the same bus, there is a RS-485 to USB adapter
(connected to /dev/ttyUSB3).
