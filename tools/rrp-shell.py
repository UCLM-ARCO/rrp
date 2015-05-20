#!/usr/bin/python
# -*- mode: python; coding: utf-8 -*-

import serial
from hexdump import hexdump
from collections import deque


class Message(object):
    def __init__(self, source, destination, type, size=None, payload=None):
        self.source = source
        self.destination = destination
        self.type = type
        self.size = size
        self.payload = payload


class RRP(object):

    MAGIC = "RRP"
    BROADCAST = 255

    TYPE_DISCOVER = 0
    TYPE_SYN = 1
    TYPE_OK = 2
    TYPE_TOKEN = 3
    TYPE_REQUEST = 4
    TYPE_RESPONSE = 5

    def __init__(self, device, timeout=5):
        self.device = serial.Serial(device, baudrate=19200, timeout=timeout / 1000.0)
        self.set_as_driver()

    def set_as_driver(self):
        self.device.setRTS(False)

    def set_as_receiver(self):
        self.device.setRTS(True)

    def wait_idle(self, count):
        i = count
        self.set_as_receiver()
        while i:
            if not self.device.read(1):
                i -= 1
            else:
                i = count

    def discover(self):
        self.wait_idle(4)
        self.send(RRP.BROADCAST, type=RRP.TYPE_DISCOVER)
        self.wait_idle(4)

        nodes = []
        for i in range(1, 255):
            if self.sync_with(i):
                nodes.append(i)
        return nodes

    def sync_with(self, addr):
        self.send(addr, type=RRP.TYPE_SYN)
        message = self.receive()
        if message is not None and message.type == RRP.TYPE_OK:
            return True
        return False

    def send_token(self, nodes, debug=False):
        for addr in nodes:
            self.send(addr, type=RRP.TYPE_TOKEN)

            while True:
                if not self.wait_magic():
                    break

                source = ord(self.device.read(1))
                destination = ord(self.device.read(1))
                type = ord(self.device.read(1))

                if debug:
                    print "received message:"
                    print " - token in device:", addr
                    print " - message from:", source
                    print " - destination:", destination
                    print " - type:", type

                if type not in [RRP.TYPE_REQUEST, RRP.TYPE_RESPONSE]:
                    continue

                size = ord(self.device.read(1))
                if size:
                    payload = self.device.read(size)

                if debug:
                    print " - size:", size
                    print " - payload: '{}'".format(payload)

    def send(self, dest, payload="", type=TYPE_RESPONSE, debug=False):
        data = RRP.MAGIC
        data += chr(0)                 # source (0 is arbiter)
        data += chr(dest)              # destination addres
        data += chr(type)              # type of message

        if type in [RRP.TYPE_RESPONSE, RRP.TYPE_REQUEST]:
            data += chr(len(payload))  # size of payload
            data += payload            # payload

        if debug:
            print "Send message  ({} bytes):".format(len(data))
            hexdump(data)

        self.set_as_driver()
        self.device.write(data)
        self.device.flush()

    def receive(self):
        self.set_as_receiver()
        if not self.wait_magic():
            return None

        source = ord(self.device.read(1))
        destination = ord(self.device.read(1))
        type = ord(self.device.read(1))

        size = None
        payload = None
        if type == RRP.TYPE_REQUEST or type == RRP.TYPE_RESPONSE:
            size = ord(self.device.read(1))
            payload = self.device.read(size)

        if destination != 0:
            print "WARNING: received a message not addressed to arbiter!"

        message = Message(source, destination, type, size, payload)
        return message

    def wait_magic(self):
        self.set_as_receiver()

        i = 0
        while i < 3:
            c = self.device.read(1)
            if not c:
                return False

            if RRP.MAGIC[i] != c:
                i = 0
                continue
            i += 1
        return True


class Worker(object):
    def __init__(self, app, device):
        self.app = app
        self.rrp = RRP(device)
        self.nodes = []

        # FIXME: remove this, added only to speed up devel
        self.nodes = [1, 2, 3]

    def execute(self, cmd, args):
        fn = getattr(self, "cmd_" + cmd, None)
        if fn is not None:
            return fn(*args)
        self.unknown_cmd(cmd)

    def unknown_cmd(self, cmd):
        raise RuntimeError("'{}': Unknown command!".format(cmd))

    def cmd_help(self, *args):
        """Shows the list of commands"""
        cmds = [x for x in dir(self) if x.startswith("cmd_")]
        docs = [getattr(self, x).__doc__ for x in cmds]

        padding = max([len(x) - 4 for x in cmds])

        print "Available commands and its descriptions:\n"
        for i in range(len(cmds)):
            name = cmds[i][4:]
            padd = padding - len(name)
            print "", name, padd * " ", docs[i]

    def cmd_quit(self, *args):
        """Exits this program"""
        self.app.finished = True

    def cmd_discover(self, *args):
        """Performs a full device discovery"""
        print "Discovering devices..."
        self.nodes = self.rrp.discover()
        print " - nodes:", self.nodes

    def cmd_send(self, dst, *data):
        r"""Send data to destination.
            |- params: <address> <data>
            |- examples:
               > send 1 data up to 255 bytes
               > send 1 \x00\x01\x02"""

        dst = int(dst)
        assert dst >= 0 and dst <= 255, "Invalid address"

        data = " ".join(data)
        data = data.decode("string_escape")
        self.rrp.send(dst, data, RRP.TYPE_REQUEST, debug=True)

    def cmd_start_rr(self, debug=False):
        """Starts the Round Robin algorithm to enable devices to send data
            |- params: [debug=false]
           NOTE: you need to discover nodes first."""
        if not self.nodes:
            raise RuntimeError("No nodes available, please use discover first")

        try:
            while True:
                self.rrp.send_token(self.nodes, debug=bool(debug))
        except KeyboardInterrupt:
            print "\r\r\rRound Robin algorithm stopped"
            return

    def cmd_status(self, *args):
        """Show current shell status"""
        print " - {} devices detected:".format(len(self.nodes)), self.nodes

        rr_status = "stopped"
        print " - Round Robin arbiter:", rr_status


class Shell(object):
    def __init__(self, device="/dev/ttyUSB3"):
        self.finished = False
        self.worker = Worker(self, device)
        self.history = deque(maxlen=5)

    def prompt_input(self):
        prompt = "> "
        return raw_input(prompt)

    def run(self):
        print "Welcome to RRP shell!"
        print "Enter 'h', '?' or 'help' to see your options\n"

        while not self.finished:
            try:
                cmd = self.prompt_input()
                if cmd:
                    self.run_command(cmd)
                    print ""
            except (KeyboardInterrupt, EOFError):
                self.finished = True

        print "\r\r\rBye!"

    def run_command(self, userinput):
        if userinput == "\x1b\x5b\x41":  # UP_ARROW
            if not self.history:
                print "ERROR: cmd history is empty"
                return

            userinput = self.history[-1]
            print "Executing last command: '{}'".format(userinput)
        else:
            self.history.append(userinput)

        fields = userinput.split()
        cmd = fields[0]
        args = fields[1:]

        if cmd in ["?", "h"]:
            cmd = "help"
        elif cmd in ["q"]:
            cmd = "quit"
        elif cmd in ["s"]:
            cmd = "send"
        elif cmd in ["rr"]:
            cmd = "start_rr"
        elif cmd in ["st"]:
            cmd = "status"

        try:
            self.worker.execute(cmd, args)
        except Exception as e:
            print "ERROR:", e


if __name__ == '__main__':
    Shell().run()
