#!/usr/bin/env python3
"""Static opt2 PAIR compilation; no arithmetic/golden generation or latency credit.

Addresses are bulk-copy line addresses (one increment per 1088-bit response).
The caller supplies installed weight spans and already allocated PQ x contexts.
This module never allocates storage or changes Euclid's issue implementation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Op:
    identity: int
    rows: int
    groups: int
    fmt: str
    base: int
    lines: int
    xb: int
    dep: bool
    x_bound: bool
    c: int = 8

    @property
    def items(self):
        return self.rows * self.groups

    @property
    def delay(self):
        return (14 if self.fmt == 'bf16' else 0) + 7 * (self.groups - 1).bit_length()

    def validate(self):
        if self.fmt not in ('bf16', 'fp4', 'fp8'):
            raise ValueError('unbound format')
        if not (0 < self.rows <= 4096 and 0 < self.groups <= 16 and self.c == 8):
            raise ValueError('unsupported shape')
        if self.lines != self.items * self.c:
            raise ValueError('weight span does not match literal shape')
        if not (0 <= self.base and self.base + self.lines <= 2**32):
            raise ValueError('weight span out of bounds')
        if not self.x_bound or not 0 <= self.xb < 128 or self.groups * self.c > 128:
            raise ValueError('missing/bad installed PQ x context')


def pair_refusal(a: Op, b: Op):
    """P1--P5. Dependency is on B; A may start a new independent run."""
    a.validate()
    b.validate()
    if b.dep:
        return 'P1 dependency boundary'
    if a.c != b.c:
        return 'P2 chunk steps differ'
    if (a.fmt == 'bf16') != (b.fmt == 'bf16'):
        return 'P3 column types differ'
    if b.delay < a.delay:
        return 'P4 retirement delay falls'
    tail = a.items % 8
    if tail == 0 or b.items > 8 - tail:
        return 'P5 whole B does not fit tail'
    # Both contexts must be resident before packed launch; do not guess lifetime.
    aa = {(a.xb + i) % 128 for i in range(a.groups * a.c)}
    bb = {(b.xb + i) % 128 for i in range(b.groups * b.c)}
    if aa & bb:
        return 'P1 overlapping installed x spans'
    if b.rows > 8 - len({r % 8 for r in range(a.rows)}):
        return 'reducer keys remain owned by A'
    return None


def pair_descriptor(a: Op, b: Op):
    refusal = pair_refusal(a, b)
    if refusal:
        raise ValueError(refusal)
    k = a.items % 8
    head_lines = (a.items - k) * a.c
    # Reserve all A keys, including rows draining from earlier waves; never
    # infer that a row is released merely because its last line was issued.
    used = {r % 8 for r in range(a.rows)}
    free = [i for i in range(8) if i not in used]
    if b.rows > len(free):
        raise ValueError('no disjoint reducer keys')
    return dict(kind='PAIR', head=dict(base=a.base, lines=head_lines),
                tail_base=a.base + head_lines, tail_items=k,
                b_base=b.base, b_items=b.items, steps=a.c,
                segments=[asdict(a), asdict(b)],
                b_reducer_keys=free[:b.rows],
                result_contract='segment identity plus op-local row; never timing attribution',
                head_lines=head_lines, packed_lines=(k + b.items) * a.c)


def request_addresses(desc):
    """Literal address order for hardware/compiler consumers, not host sums."""
    h = desc['head']
    for i in range(h['lines']):
        yield h['base'] + i
    for t in range(desc['steps']):
        for i in range(desc['tail_items']):
            yield desc['tail_base'] + t * desc['tail_items'] + i
        for i in range(desc['b_items']):
            yield desc['b_base'] + t * desc['b_items'] + i


def tag16_mapping(desc):
    """Finite W2 mapping contract; no claim for unequal-G or mixed-format pairs."""
    a, b = [Op(**o) for o in desc['segments']]
    if not (a.rows == b.rows == 2 and a.groups == b.groups == 2
            and a.fmt == b.fmt == 'fp4' and a.c == b.c == 8):
        raise ValueError('TAGW16 mapper supports actual W2 pairs only')
    return dict(rows_a=2, rows_total=4, groups=2, c=8,
                xb_a=a.xb, xb_b=b.xb, delta_x=(b.xb-a.xb)%128,
                op_a=a.identity, op_b=b.identity,
                virtual_rows=[dict(key=i, operation=a.identity if i<2 else b.identity,
                                   local_row=i if i<2 else i-2) for i in range(4)],
                tag_bits=16, reducer_keys=[0,1,2,3],
                completion_rows=4, format='fp4', source_arithmetic_changed=False)


def compile_run(ops, enabled=False):
    """Default-off compiler. Conservative pairs; no speculative shift packing."""
    for op in ops:
        op.validate()
    if len({o.identity for o in ops}) != len(ops):
        raise ValueError('duplicate operation identity')
    out, i = [], 0
    while i < len(ops):
        a = ops[i]
        if enabled and i + 1 < len(ops) and pair_refusal(a, ops[i + 1]) is None:
            out.append(pair_descriptor(a, ops[i + 1]))
            i += 2
        else:
            out.append(dict(kind='LINEAR', base=a.base, lines=a.lines, op=asdict(a)))
            i += 1
    return dict(schema='opentallas.dshbm.wavepack.static.v1', enabled=enabled,
                descriptors=out, arithmetic_changed=False, measured_gain=None,
                adoption=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ops', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--enable', action='store_true')
    a = ap.parse_args()
    rec = compile_run([Op(**o) for o in json.loads(a.ops.read_text())], a.enable)
    a.output.write_text(json.dumps(rec, indent=2) + '\n')


if __name__ == '__main__':
    main()
