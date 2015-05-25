
Installation for Arduino Development
====================================

First, locate you Arduino `USER_LIB_PATH`. It is expected to be on
`$HOME/Arduino/libraries`. Then, make a directory called `RRP` on that
location:

    $ mkdir -p ~/Arduino/libraries/RRP

Finally, link (or copy) the contents for `src` to that directory.

Round Robin Protocol (RRP)
==========================

The RS-485 network has multiple devices using a master-slave paradigm
(or in the RS-485 nomenclature, driver-reader). Only the driver can
write on the bus, and all readers can read. Every node could became a
driver, but there should be just one driver on the network at a given
time.

RS-485 only describes the most low level layer, giving the network
layer to be part of the application protocol. In this case, we have
designed a protocol called Round Robin Protocol (RRP).

In RRP, there is a node called arbiter, and one or more nodes called
devices. When the network starts, the arbiter is the driver. The first
thing that does is a network discovery, to know how many other devices
are in the network. Then, it gives to each node, using a round robin
algorithm, the oportunity of became driver and use the bus.

Addressing
----------

RRP uses 1 byte as a node address, given that one simple RS-485
network should have no more than 32 nodes (or a maximum of 255 if uses
repeaters). There are two reserved address:

* 0: the arbiter address, used to communicate protocol messages.
* 255: the broadcast address, used to send a non-responding message to
  all nodes

Every other address its free to be used by any device.

The discovery
-------------

The arbiter iters over the 253 possible addresses, and sends a `RRP
SYNC` message to each one. It then releases the driver role becoming a
reader. If the addressed node exists, then it must return a `RRP OK`
message to the arbiter (address 0). If the node does not exists, then
a `TIMEOUT` will expire, and the arbiter will become the driver again,
sending the `SYN` message to the next address.

To launch the discovery process, the arbiter stops sending tokens and
waits until the last message is sent and the `TIMEOUT` has
expired. Then, waits `TIMEOUT * 3` to verify that the input queue of each
device is empty. After that, it sends a `DISCOVER` message to the
broadcast address and again waits `TIMEOUT * 3`. This message forces every
device to enter in `SYNC` mode, waiting and responding only to `SYN`
messages. Once the node receives and answers a `SYN` message, it
continues its previous work.

When a device enters `SYNC` mode, a timeout will start. If the timeout
expires and no `SYN` messages is received, it will exit `SYNC` mode.

Iterating over nodes
--------------------

When the arbiter has a complete list of nodes, it iters over each one
sending a `TOKEN` message. Then, releases the driver role becoming a
reader. If the addressed node needs to use the network, it accepts the
driver role, and sends his message. It needs to use the network before
the arbiter `TIMEOUT` has expired, otherwise a collision will happend.

If the device sends a message, the arbiter's `TIMEOUT` is reset. If the
message is addressed to another device, and this device wants to
answer, it could be done before the `TIMEOUT` has expired again. This
allows that two given nodes could have a request-response dialog
directly. Well-behaved devices does not try to use the network more
than needed.

When the arbiter's `TIMEOUT` has expired, the arbiter gets the driver
role, and sends the `TOKEN` message to the following device in his list.

Protocol Messages
-----------------

Each message has the following structure:

* 'RRP' magic (3 bytes)
* source address (1 byte)
* destination address (1 byte)
* type of message (1 byte)

The 'type' of message could be one of the following:

* 0: `DISCOVER` message, used to alert devices to enter on `SYNC` mode
* 1: `SYN` message, used in discovery process
* 2: `OK` response, the answer of a discovered device
* 3: `TOKEN` message, sent to allow a device to became driver
* 4: `REQUEST` message, sent by a device to another device
* 5: `RESPONSE` message, sent as a response to a `REQUEST` message

If the 'type' is `REQUEST` or `RESPONSE`, the message has the
following body:

* size of payload (1 byte)
* payload ('size' bytes)
