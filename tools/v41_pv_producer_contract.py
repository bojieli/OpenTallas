#!/usr/bin/env python3
"""Source-pinned executable contract model; not an RTL timing measurement."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['rtl/hdc/v41x/ot_hdc_v41x_att_adapt.sv',
           'rtl/hdc/v41x/ot_hdc_core_v41x.sv', 'tools/hdc_replay_v41.py']

def replay(rows=640, heads=16, groups=4, pwords=1, row_banks=4, stall_period=0):
    if min(rows, heads, groups, row_banks) <= 0 or pwords not in (1, 2):
        raise ValueError('invalid geometry')
    # Nonzero distinguishable finite BF16 payload. No arithmetic approximation.
    values = [[0x3c00 + ((h * rows + r) % 768) for r in range(rows)] for h in range(heads)]
    memory = {}
    preload_conflicts = 0
    for start in range(0, heads * rows, groups):
        used = set()
        for linear in range(start, min(start + groups, heads * rows)):
            h, r = divmod(linear, rows)
            bank = (h, r % row_banks)
            preload_conflicts += bank in used
            used.add(bank)
            memory[h, r] = values[h][r]
    # A_LDX completion fence: no load/stream overlap is allowed in existing RTL.
    beats = []
    conflicts = 0
    for block in range(0, rows, 32):
        for row in range(block, min(block + 32, rows), 2 * pwords):
            used = set()
            beat = []
            for r in range(row, min(row + 2 * pwords, block + 32, rows)):
                for h in range(heads):
                    bank = (h, r % row_banks)
                    conflicts += bank in used
                    used.add(bank)
                    beat.append((h, r, memory[h, r]))
            beats.append(beat)
    accepted = []
    cycle = 0
    pos = 0
    while pos < len(beats):
        ready = not stall_period or cycle % stall_period != 0
        if ready:
            accepted.extend(beats[pos]); pos += 1
        cycle += 1
    expected = sorted((h, r, values[h][r]) for h in range(heads) for r in range(rows))
    assert sorted(accepted) == expected
    return dict(rows=rows, heads=heads, groups=groups, pwords=pwords,
                row_banks=row_banks, preload_issue_cycles=(heads*rows+groups-1)//groups,
                preload_bank_conflicts=preload_conflicts, stream_bank_conflicts=conflicts,
                accepted_beats=len(beats), stream_elapsed_cycles=cycle,
                exact_nonzero_elements=len(accepted),
                lower_bound_preload_plus_stream=(heads*rows+groups-1)//groups+len(beats))

def report():
    old = replay(pwords=1)
    proposed = replay(pwords=2)
    return dict(status='executable_contract_model_not_rtl_measurement',
        source_pins={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
        current=old, proposed_banked_xbuf=proposed,
        insufficient_two_row_banks=replay(pwords=2,row_banks=2),
        backpressure=replay(pwords=2,stall_period=3),
        assumptions=['all SU probability writes complete before A_LDX',
          'G scalar FP32 VM operands accepted every cycle: optimistic VM service bound',
          'proposed xbuf uses head x (row modulo 4) banks, one port per bank',
          'preload and stream do not overlap; no refill or overwrite until operation completes',
          'stream always ready except separately reported backpressure case'],
        unresolved=['actual SU latency and shared VM arbitration',
          'physical xbuf banking/register mux implementation',
          'stationary engine four-bank lifetime guard and numerical verification'],
        architectural_conclusion='PWORDS2 widens local preloaded xbuf gather, not sustained SU/VM bandwidth; G4 preload is 2560 issue cycles before streaming. No full-layer rate claimed.')

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path); args=ap.parse_args()
    data=json.dumps(report(),indent=2)+'\n'
    if args.output: args.output.write_text(data)
    else: print(data,end='')
