#!/usr/bin/python
# -*- mode: python; coding: utf-8 -*-

import serial
import traceback
from argparse import ArgumentParser
from hexdump import hexdump
from collections import deque
from threading import Thread
from Queue import Queue, Full


class Message(object):
    def __init__(self, source, destination, type, size=None, payload=None):
        self.source = source
        self.destination = destination
        self.type = type
        self.size = size
        self.payload = payload

        error = "Invalid message size, not enough data"
        if size > 0:
            assert payload is not None, error
            assert size <= len(payload), error

    def marshall(self):
        data = RRP.MAGIC
        data += chr(self.source)       # source
        data += chr(self.destination)  # destination addres
        data += chr(self.type)         # type of message

        if self.type in [RRP.TYPE_RESPONSE, RRP.TYPE_REQUEST]:
            data += chr(self.size)     # size of payload
            data += self.payload       # payload
        return data

    def __repr__(self):
        retval = "Message ({} bytes):\n".format(self.size)
        retval += hexdump(self.marshall(), result="return")
        return retval


class Arbiter(object):
    def __init__(self, rrp, nodes=None):
        self.rrp = rrp
        self.nodes = nodes

        self.finished = False
        self.out_queue = deque(maxlen=50)
        self.in_queue = Queue(maxsize=50)
        self.promiscuous = False

    def run_in_thread(self):
        self.thread = Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def finish(self, wait=True):
        self.finished = True
        self.thread.join()

    def run(self, debug=False):
        if not self.nodes:
            self.nodes = self.rrp.discover()

        try:
            while not self.finished:
                messages = self.rrp.send_token(self.nodes, debug=debug)
                self.append_in_queue(messages)
                self.flush_out_queue()
        except KeyboardInterrupt:
            pass

    def send(self, message, debug=False):
        self.out_queue.appendleft(message)
        if debug:
            print message

    def flush_out_queue(self):
        while self.out_queue:
            msg = self.out_queue.pop()
            self.rrp.send_message(msg)

    def append_in_queue(self, messages):
        while messages:
            try:
                m = messages.pop()
                self.in_queue.put_nowait(m)
            except Full:
                pass

    def receive(self):
        # NOTE: allow Ctr+C to work here, see http://bugs.python.org/issue1360
        oneyear = 365 * 24 * 60 * 60
        while True:
            return self.in_queue.get(True, oneyear)

    def set_promiscuous(self):
        self.promiscuous = True


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

        self.messages = deque(maxlen=50)
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

                message = Message(source, destination, type)
                self.messages.appendleft(message)

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

                message.size = size
                message.payload = payload

                if debug:
                    print " - size:", size
                    print " - payload: '{}'".format(payload)

        return self.messages

    def send(self, dest, payload="", type=TYPE_RESPONSE, debug=False):
        message = Message(0, dest, type, len(payload), payload)
        if debug:
            print message

        self.send_message(message)

    def send_message(self, message):
        self.set_as_driver()
        self.device.write(message.marshall())
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
        self.arbiter = None

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
        assert self.arbiter is None, "Could not discover while arbiter is running"

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

        if self.arbiter is None:
            return self.rrp.send(dst, data, RRP.TYPE_REQUEST, debug=True)

        msg = Message(0, dst, RRP.TYPE_REQUEST, len(data), data)
        self.arbiter.send(msg, debug=True)

    def cmd_start_rr(self, foreground=False, debug=False):
        """Starts the Round Robin arbiter to enable devices to send data
            |- params: [foreground=False [debug=false]]"""

        assert self.arbiter is None, "Round Robin arbiter already running!"

        if isinstance(debug, str):
            debug = debug != "0"

        self.arbiter = Arbiter(self.rrp, self.nodes)
        if foreground:
            print "Round Robin arbiter running (debug={})...".format(debug)
            print "Press Ctrl+C to stop it"
            return self.arbiter.run(debug)

        if debug:
            print "NOTE: debug only could be enabled on foreground mode"

        self.arbiter.run_in_thread()
        print "Round Robin arbiter running in background"

    def cmd_stop_rr(self):
        """Stops the running Round Robin arbiter (if any)"""

        assert self.arbiter is not None, "Round Robin arbiter is not running"

        self.arbiter.finish()
        self.arbiter = None
        print "Round Robin arbiter stopped"

    def cmd_status(self, *args):
        """Show current shell status"""
        print " - {} devices detected:".format(len(self.nodes)), self.nodes

        rr_status = "stopped"
        if self.arbiter is not None:
            rr_status = "running"
        print " - Round Robin arbiter:", rr_status

    def cmd_receive(self, promiscuous=True):
        """Receive and show messages on network
            | params: [promiscuous=False]"""

        assert self.arbiter is not None, \
            "To receive messages, Round Robin arbiter must be running"

        if isinstance(promiscuous, str):
            promiscuous = promiscuous != "0"
        if promiscuous:
            self.arbiter.set_promiscuous()

        try:
            print "Start to show received messages..."
            while True:
                message = self.arbiter.receive()
                print message
        except KeyboardInterrupt:
            pass
        print "\r\r\rStop showing received messages"


class Shell(object):
    def __init__(self, device="/dev/ttyUSB3"):
        self.finished = False
        self.worker = Worker(self, device)
        self.history = deque(maxlen=5)
        self.print_traceback = False

    def prompt_input(self):
        prompt = "> "
        return raw_input(prompt)

    def run_interactive(self):
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

    def run_as_daemon(self):
        self.worker.execute("start_rr", [True])

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
        cmd = fields[0].lower()
        args = fields[1:]

        if cmd in ["?", "h"]:
            cmd = "help"
        elif cmd in ["q"]:
            cmd = "quit"
        elif cmd in ["s"]:
            cmd = "send"
        elif cmd in ["rr", "start"]:
            cmd = "start_rr"
        elif cmd in ["stop"]:
            cmd = "stop_rr"
        elif cmd in ["st"]:
            cmd = "status"
        elif cmd in ["print_traceback", "ptb"]:
            print "Print traceback on error activated"
            self.print_traceback = True
            return

        try:
            self.worker.execute(cmd, args)
        except Exception as e:
            print "ERROR:", e
            if self.print_traceback:
                traceback.print_exc()


if __name__ == '__main__':
    parser = ArgumentParser("Round Robin arbiter shell")
    parser.add_argument("--device", default="/dev/ttyUSB3",
                        help='USB device to use')
    parser.add_argument('--daemon', action='store_true',
                        help='Launch arbiter in daemon mode (no interactive)')

    args = parser.parse_args()
    s = Shell(args.device)

    if not args.daemon:
        s.run_interactive()
    else:
        s.run_as_daemon()
