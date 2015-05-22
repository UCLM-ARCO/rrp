// -*- mode: c++; coding: utf-8 -*-

module RemoteIO {

    sequence<byte> ByteSeq;

    interface Output {
	void send(ByteSeq data);
    };

    interface Input {
	void register(Output* observer);
    };

    interface IO extends Input, Output {};
};
