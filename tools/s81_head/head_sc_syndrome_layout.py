#!/usr/bin/env python3
"""Prepare an opt-in SC syndrome placement fallback; never modify RTL or plans.

Run against a private SC kit's face_flops.tcl. The output is a candidate only:
existing GRT must be read, and PLACE/clock/hold review precedes any release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

PREFIX = 'u_phy.u_link.u_dec.u_syn.'
COUNTS = {'sc_q': 550, 'sp0': 300, 'sp1': 300, 'S_q': 300}
ANCHOR = 'set hf1_n 0; set hf1_miss {}'
MARKER = '# CODEX_SC_SYNDROME_BEGIN'


def sites(style: str) -> dict[str, tuple[float, float]]:
    if style not in ('pitch65', 'two-bank'):
        raise ValueError(style)
    out = {}
    for family, count in COUNTS.items():
        for bit in range(count):
            if family == 'S_q':
                # Consumers are BM0/1/2 to the WEST. Preserve vJ's clock lane
                # x1240..1269; do not move S_q east to the syndrome producer.
                x, y = 1269 + (bit % 7) * 6.48, 8.64 + (bit // 7) * 1.08
            elif style == 'pitch65':
                x = 1438.56 + (bit % 18) * 6.48
                origin = {'sp1': 8.64, 'sc_q': 69.12, 'sp0': 70.74}[family]
                y = origin + (bit // 18) * 3.24
            else:
                col, row = bit % 12, bit // 12
                x = (1438.56 if col < 6 else 1514.16) + (col % 6) * 6.48
                origin = {'sp1': 8.64, 'sc_q': 95.04, 'sp0': 96.66}[family]
                y = origin + row * 3.24
            out[f'{PREFIX}{family}[{bit}]'] = (round(x, 6), round(y, 6))
    return out


def rewrite(source: str, style: str) -> tuple[str, dict]:
    if MARKER in source or source.count(ANCHOR) != 1:
        raise ValueError('expected one fresh HF1 placement loop')
    existing = re.findall(r'\{u_phy\.u_link\.u_dec\.u_syn\.(sc_q|sp0|sp1|S_q)\[(\d+)\]\}\s+\{[\d.]+\s+[\d.]+\}', source)
    have = {f: set() for f in COUNTS}
    for family, bit in existing:
        have[family].add(int(bit))
    for family in ('sc_q', 'sp1', 'S_q'):
        if have[family] != set(range(COUNTS[family])):
            raise ValueError(f'incomplete {family} placement table')
    # sp0 exists in the measured gate netlist but was left to GPL. Explicit
    # interleaved sites reserve room for it instead of packing it at the west edge.
    target = sites(style)
    lines = [MARKER + ' style=' + style,
             '# Placement only: PIN CYCLES 0; macro/clock/child adoption HOLD stays.',
             '# Source proof and timing are separate; no RTL or SDC change.']
    for name, (x, y) in target.items():
        lines.append(f'dict set hf1_sites {{{name}}} {{{x:.6f} {y:.6f}}}')
    lines.append('# CODEX_SC_SYNDROME_END')
    output = source.replace(ANCHOR, '\n'.join(lines) + '\n' + ANCHOR, 1)
    bounds = {}
    for family in COUNTS:
        p = [p for n, p in target.items() if n.startswith(PREFIX + family + '[')]
        bounds[family] = [min(x for x,y in p), min(y for x,y in p), max(x for x,y in p), max(y for x,y in p)]
    receipt = {
        'schema': 'opentallas.head.sc_syndrome_candidate.v1',
        'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'style': style, 'counts': COUNTS, 'sites': len(target),
        'bounds_um': bounds, 'pin_cycles': 0, 'rtl_changed': False,
        'sdc_changed': False, 'macros_changed': False,
        'die_outline_um': [2885.76, 1226.88],
        'measured_rows_y_um': [4.32, 1222.56],
        'macro_gap_x_um': [1430.676, 1560.006],
        'central_corridor_um': 42.12 if style == 'two-bank' else None,
        'held': ['READ_CURRENT_GRT', 'PLACE_REVIEW', 'CLOCK_HOLD', 'CHILD_ADOPTION', 'DO_NOT_COUNT', 'HOLD_ROUTE'],
        'note': 'Candidate geometry only. All 300 S_q bits broadcast to all three western BM children; their existing long consumer reach is not qualified by this change.'}
    return output, receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--face-flops', type=Path, required=True)
    ap.add_argument('--style', choices=('pitch65','two-bank'), required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--receipt', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists() or a.receipt.exists():
        ap.error('candidate output/receipt already exists; keep previous evidence')
    text, rec = rewrite(a.face_flops.read_text(), a.style)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(text)
    a.receipt.write_text(json.dumps(rec, indent=2) + '\n')
    print(f'SC_CANDIDATE {a.style} sites={rec["sites"]} PIN_CYCLES=0 HELD')

if __name__ == '__main__':
    main()
