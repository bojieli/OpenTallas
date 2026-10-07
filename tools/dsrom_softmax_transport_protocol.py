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
        self.den_ready = False
        self.state = 'fill_scores'

    def accept(self, port, beat):
        if port not in ('scores', 'pv') or self.state != 'fill_' + port:
            raise ValueError('input outside fill phase')
        if len(beat) != 128:
            raise ValueError('partial transport beat')
        capacity = self.model['ports'][port]['payload_bytes_per_row']
        if len(self.rows[port]) + len(beat) > capacity:
            raise ValueError('unreserved input')
        self.rows[port].extend(beat)

    def dispatch(self, port='scores', mutant=False):
        if port not in ('scores', 'pv') or self.state != 'fill_' + port or len(self.rows[port]) != self.model['ports'][port]['payload_bytes_per_row']:
            raise ValueError('incomplete row')
        if port == 'pv' and not self.den_ready:
            raise ValueError('denominator not ready')
        self.state = 'compute_' + ('exponentials' if port == 'scores' else 'result_bf16')
        result = [bytes(self.rows[port][i:i+1024]) for i in range(0, len(self.rows[port]), 1024)]
        if mutant:
            result[0] = result[0][128:] + result[0][:128]
        return result

    def denominator_ready(self):
        if self.state in ('idle', 'fill_scores'):
            raise ValueError('denominator outside live score transaction')
        self.den_ready = True

    def capture(self, port, vector):
        if port not in ('exponentials', 'result_bf16') or self.state != 'compute_' + port:
            raise ValueError('output outside compute phase')
        spec = self.model['ports'][port]
        if len(vector) != spec['bytes_per_stream_edge'] or len(self.rows[port]) + len(vector) > spec['payload_bytes_per_row']:
            raise ValueError('output reservation exceeded')
        self.rows[port].extend(vector)

    def complete(self, port):
        if self.state != 'compute_' + port or len(self.rows[port]) != self.model['ports'][port]['payload_bytes_per_row']:
            raise ValueError('incomplete outputs')
        self.state = 'drain_' + port

    def drain(self, port, ready):
        if self.state != 'drain_' + port:
            raise ValueError('read port still owned by replay')
        if not ready:
            return b''
        beat = bytes(self.rows[port][:128])
        del self.rows[port][:128]
        if not self.rows[port]:
            self.state = 'fill_pv' if port == 'exponentials' else 'idle'
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
    negatives += rejects(lambda: bank.accept('pv', bytes(128)))
    # The consumer cannot produce PV until it receives this row's exponentials.
    for inp, outp in [('scores', 'exponentials'), ('pv', 'result_bf16')]:
        for i in range(0, len(payloads[inp]), 128):
            before = len(bank.rows[inp])
            for _ in range(rng.randrange(5)):
                assert len(bank.rows[inp]) == before and bank.command == frozen_command
            bank.accept(inp, payloads[inp][i:i+128])
        negatives += rejects(lambda: bank.accept(inp, bytes(128)))
        if inp == 'pv':
            negatives += rejects(lambda: bank.dispatch('pv'))
            bank.denominator_ready()
        replay = bank.dispatch(inp, mutant)
        assert b''.join(replay) == payloads[inp], 'replay beat order changed'
        negatives += rejects(lambda: bank.drain(outp, True))
        width = bank.model['ports'][outp]['bytes_per_stream_edge']
        for i in range(0, len(payloads[outp]), width):
            bank.capture(outp, payloads[outp][i:i+width])
        negatives += rejects(lambda: bank.capture(outp, bytes(width)))
        bank.complete(outp)
        for _ in range(1000):
            assert not bank.drain(outp, False)
            assert bank.command == frozen_command and bank.state == 'drain_' + outp
        negatives += rejects(lambda: bank.reserve(command))
        observed = bytearray()
        while bank.rows[outp]:
            observed.extend(bank.drain(outp, rng.randrange(4) != 0))
        assert observed == payloads[outp]
        if outp == 'exponentials':
            assert bank.state == 'fill_pv'
    assert bank.state == 'idle'
    bank.reserve(frozen_command)
    assert bank.state == 'fill_scores'
    return dict(tokens=tokens, payload_bytes=sum(map(len, payloads.values())),
                rejected_illegal_transactions=negatives, stalled_drain_cycles=2000,
                PV_requires_exp_drain=True)


def join_dependency_check():
    """The source compiler/engine requires E before any corresponding P.V.

    Detect the predecessor policy's cycle independently of the transport class.
    Sources describe E as the tile P.V input and PV as its output operand.
    """
    root = Path(__file__).resolve().parents[1]
    source = root/'rtl/hdc/v41x/ot_hdc_v41x_attn.sv'
    assert 'pv[h, d] = dots(to_bf16(e), kvm.T)[h, d]' in source.read_text()
    edges = [('score_dispatch','exp_available'), ('exp_available','exp_drain'),
             ('exp_drain','PV_available'), ('PV_available','PV_dispatch'),
             ('PV_dispatch','final_output')]
    def acyclic(extra):
        graph = edges + extra
        remaining = {n for edge in graph for n in edge}
        while remaining:
            ready = {n for n in remaining if not any(b==n and a in remaining for a,b in graph)}
            if not ready:
                return False
            remaining -= ready
        return True
    assert acyclic([])
    # Original all-input-prefill and final-output-before-drain policy.
    assert not acyclic([('PV_available','score_dispatch'), ('final_output','exp_drain')])
    return dict(corrected_DAG_acyclic=True, predecessor_deadlock_detected=True,
        dependency_source=str(source.relative_to(root)), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        predecessor_record='results/uarch/dsrom_softmax_transport_20261007/protocol.json',
        predecessor_scope_failure='opaque independent payloads omitted E to P.V dependency; historical PASS does not qualify producer integration')


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
        producer_dependency=join_dependency_check(),
        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        pending=['actual RTL and SRAM read timing', 'CDC and atomic reset', 'ECC and protection negatives',
                 'producer/consumer phase overlap proof', 'physical closure and composed token latency'])
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end='')
