#!/usr/bin/env python3
"""Executable full-width row reservation protocol, independent of arithmetic.

This exercises the proposed transaction contract. It is not an RTL exactness,
ECC, CDC or timing gate. No softmax arithmetic is replaced by this component.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

from dsrom_softmax_transport import build


class Reservation:
    def __init__(self, tokens):
        self.model = build(tokens)
        self.state = 'idle'

    def reserve(self, command):
        if self.state != 'idle':
            raise ValueError('row still owned')
        self.command = bytes(command)
        self.rows = {k: bytearray() for k in self.model['ports']}
        self.state = 'fill'

    def accept(self, port, beat):
        if self.state != 'fill' or port not in ('scores', 'pv'):
            raise ValueError('input outside fill phase')
        if len(beat) != 128:
            raise ValueError('partial transport beat')
        capacity = self.model['ports'][port]['payload_bytes_per_row']
        if len(self.rows[port]) + len(beat) > capacity:
            raise ValueError('unreserved input')
        self.rows[port].extend(beat)

    def dispatch(self, mutant=False):
        if self.state != 'fill' or any(len(self.rows[p]) != self.model['ports'][p]['payload_bytes_per_row'] for p in ('scores', 'pv')):
            raise ValueError('incomplete row')
        self.state = 'compute'
        result = {}
        for p in ('scores', 'pv'):
            result[p] = [bytes(self.rows[p][i:i+1024]) for i in range(0, len(self.rows[p]), 1024)]
            if mutant:
                result[p][0] = result[p][0][128:] + result[p][0][:128]
        return result

    def capture(self, port, vector):
        if self.state != 'compute' or port not in ('exponentials', 'result_bf16'):
            raise ValueError('output outside compute phase')
        spec = self.model['ports'][port]
        if len(vector) != spec['bytes_per_stream_edge'] or len(self.rows[port]) + len(vector) > spec['payload_bytes_per_row']:
            raise ValueError('output reservation exceeded')
        self.rows[port].extend(vector)

    def complete(self):
        if self.state != 'compute' or any(len(self.rows[p]) != self.model['ports'][p]['payload_bytes_per_row'] for p in ('exponentials', 'result_bf16')):
            raise ValueError('incomplete outputs')
        self.state = 'drain'

    def drain(self, port, ready):
        if self.state != 'drain':
            raise ValueError('read port still owned by replay')
        if not ready:
            return b''
        beat = bytes(self.rows[port][:128])
        del self.rows[port][:128]
        if not self.rows['exponentials'] and not self.rows['result_bf16']:
            self.state = 'idle'
        return beat


def rejects(fn):
    try:
        fn()
    except ValueError:
        return 1
    raise AssertionError('illegal transaction accepted')


def campaign(tokens, mutant=False):
    rng = random.Random(640 + tokens)
    bank = Reservation(tokens)
    payloads = {p: rng.randbytes(s['payload_bytes_per_row']) for p, s in bank.model['ports'].items()}
    command = bytearray(rng.randbytes(326))
    command[-1] &= 3  # exactly 2602 command bits, six padding bits zero
    frozen_command = bytes(command)
    bank.reserve(command)
    command[:] = b'\x00' * len(command)  # producer immediately changes its bus
    negatives = rejects(lambda: bank.reserve(command)) + rejects(bank.dispatch)
    for p in ('scores', 'pv'):
        for i in range(0, len(payloads[p]), 128):
            # Arbitrary idle intervals do not commit bytes or configuration.
            before = len(bank.rows[p])
            for _ in range(rng.randrange(5)):
                assert len(bank.rows[p]) == before and bank.command == frozen_command
            bank.accept(p, payloads[p][i:i+128])
        negatives += rejects(lambda: bank.accept(p, bytes(128)))
    replay = bank.dispatch(mutant)
    for p in replay:
        assert b''.join(replay[p]) == payloads[p], 'replay beat order changed'
    negatives += rejects(lambda: bank.drain('exponentials', True))
    # Arithmetic outputs are opaque tagged payloads: check conservation only.
    for p in ('exponentials', 'result_bf16'):
        width = bank.model['ports'][p]['bytes_per_stream_edge']
        for i in range(0, len(payloads[p]), width):
            bank.capture(p, payloads[p][i:i+width])
        negatives += rejects(lambda: bank.capture(p, bytes(width)))
    bank.complete()
    for _ in range(1000):
        assert not bank.drain('exponentials', False)
        assert bank.command == frozen_command and bank.state == 'drain'
    negatives += rejects(lambda: bank.reserve(command))
    for p in ('exponentials', 'result_bf16'):
        observed = bytearray()
        while bank.rows[p]:
            observed.extend(bank.drain(p, rng.randrange(4) != 0))
        assert observed == payloads[p]
    assert bank.state == 'idle'
    bank.reserve(frozen_command)
    assert bank.state == 'fill'
    return dict(tokens=tokens, payload_bytes=sum(map(len, payloads.values())),
                rejected_illegal_transactions=negatives, stalled_drain_cycles=1000)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    results = [campaign(t) for t in (128, 640)]
    try:
        campaign(640, mutant=True)
    except AssertionError as exc:
        assert str(exc) == 'replay beat order changed'
    else:
        raise AssertionError('beat-order mutant escaped')
    paths = [Path(__file__), Path(__file__).with_name('dsrom_softmax_transport.py')]
    result = dict(scope='analytical full-width protocol simulation; NOT RTL or arithmetic exactness',
        passed=True, campaigns=results, beat_order_mutant_rejected=True,
        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        pending=['actual RTL and SRAM read timing', 'CDC and atomic reset', 'ECC and protection negatives',
                 'producer/consumer phase overlap proof', 'physical closure and composed token latency'])
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end='')
