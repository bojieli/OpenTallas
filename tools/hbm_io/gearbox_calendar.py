#!/usr/bin/env python3
"""Exact periodic calendar for a static 612-bit frame / 487-bit word bridge.

There is no runtime ready input. TX reservations and RX output ages follow the
calendar phase; an unexpected valid is a fault, never an issue decision.
"""
from math import gcd


def calendar(frame=612, word=487):
    if not 0 < word < frame:
        raise ValueError('requires 0 < word < frame')
    period = frame // gcd(frame, word)
    tx_bits = rx_bits = 0
    rows = []
    sent = received = 0
    for cycle in range(period):
        tx_due = tx_bits < word
        if tx_due:
            tx_bits += frame
            sent += 1
        tx_bits -= word
        rx_bits += word
        rx_due = rx_bits >= frame
        if rx_due:
            rx_bits -= frame
            received += 1
        rows.append({'cycle': cycle, 'tx_frame_due': tx_due,
                     'rx_frame_due': rx_due, 'tx_remaining_bits': tx_bits,
                     'rx_remaining_bits': rx_bits})
    assert tx_bits == rx_bits == 0
    assert sent == received == word // gcd(frame, word)
    return {'frame_bits': frame, 'word_bits': word, 'period': period,
            'frames_per_period': sent, 'rows': rows,
            'scope': 'digital gearbox component only; external transport epoch and latency must be compiled',
            'physical_qualified': False}


if __name__ == '__main__':
    import json
    print(json.dumps(calendar(), indent=2))
