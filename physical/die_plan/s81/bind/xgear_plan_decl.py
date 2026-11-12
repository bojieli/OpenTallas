#!/usr/bin/env python3
"""BUS-GEAR-1 (2026-11-12): declare the geared S81 x lanes' cycles on a gear plan (lanes noted 'BUS-GEAR-1 2:1').

RTL (rtl/dsrom_sys/s81_dv/xgear/ot_s81_xgear_die.sv): the slice TX beat register is one extra station cycle on every
beat (fixed_cycles 1) and the word lands with its second beat (DEC12 beats 2: word_cycles = cycles + 1); the beat lane is
4 x (138 + 1 first-beat flag) = 556 = ceil(1104 / 2) + beat_index_bits 4.  Total word latency vs the ungeared lane: +2.
Fail-closed: every noted lane has width-556 ports and fixed_cycles 0 or 1; nothing else changes.  Regenerate the latency
table afterwards (tools/die_plan/gen.py latency PLAN --inplace).
usage: xgear_plan_decl.py PLAN_IN PLAN_OUT
"""
import json, sys

def main():
    pin, pout = sys.argv[1:3]
    d = json.load(open(pin))
    P = {p['id']: p for p in d['ports']}
    n = 0
    for l in d['lanes']:
        if 'BUS-GEAR-1 2:1' not in (l.get('note') or ''):
            continue
        ws = {int(P[i]['width']) for i in l['ports']}
        if ws != {556} or int(l.get('fixed_cycles', 0)) not in (0, 1):
            raise SystemExit('lane %s: widths %s fixed %s' % (l['id'], ws, l.get('fixed_cycles')))
        l['fixed_cycles'] = 1
        l['beats'] = 2
        l['word_bits'] = 1104
        l['beat_index_bits'] = 4
        l['note'] = l['note'] + ' | BUS-GEAR-1 RTL: TX face flop (fixed 1) + 2nd beat (beats 2), word +2'
        n += 1
    if n != 72:
        raise SystemExit('expected 72 geared lanes, got %d' % n)
    json.dump(d, open(pout, 'w'), indent=1)
    print('declared', n)

if __name__ == '__main__':
    main()
