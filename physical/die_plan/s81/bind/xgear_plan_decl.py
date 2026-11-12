#!/usr/bin/env python3
"""BUS-GEAR-1/-2 (2026-11-12): declare the geared S81 x lanes' cycles on a gear plan (lanes noted 'BUS-GEAR-1 2:1').

RTL (rtl/dsrom_sys/s81_dv/xgear/ot_s81_xgear_die.sv): the slice TX passes beat 0 combinationally into the partition face
flop (where the ungeared word was captured) and holds beat 1 one edge, so the lane's register stages are unchanged and the
word lands with its second beat: DEC12 beats 2 (word_cycles = cycles + 1), word_bits 1104, beat_index_bits 4 (port
4 x (138 + 1 first-beat flag) = 556 = ceil(1104 / 2) + 4).  fixed_cycles is NOT touched (a fixed cycle would make the bind
add a pad stage the RTL does not have).  Word latency vs the ungeared lane: +1 (EQ: tb_s81_xgear_eq.sv, MUT 1 shows the
+1 is needed).
Fail-closed: every noted lane has width-556 ports and no other DEC12 declaration; exactly 72 lanes; nothing else changes.
Regenerate the latency table afterwards (tools/die_plan/gen.py latency PLAN --inplace).
usage: xgear_plan_decl.py PLAN_IN PLAN_OUT
"""
import json, sys

DECL = dict(beats=2, word_bits=1104, beat_index_bits=4)
NOTE = ' | BUS-GEAR-2 RTL: beat 0 combinational into the face flop, beat 1 held (beats 2: word +1, cycles unchanged)'


def main():
    pin, pout = sys.argv[1:3]
    d = json.load(open(pin))
    P = {p['id']: p for p in d['ports']}
    n = 0
    for l in d['lanes']:
        if 'BUS-GEAR-1 2:1' not in (l.get('note') or ''):
            continue
        ws = {int(P[i]['width']) for i in l['ports']}
        if ws != {556}:
            raise SystemExit('lane %s: widths %s, want {556}' % (l['id'], ws))
        have = {k: l[k] for k in DECL if k in l}
        if have and have != DECL:
            raise SystemExit('lane %s: other DEC12 declaration %s' % (l['id'], have))
        l.update(DECL)
        if NOTE not in l['note']:
            l['note'] = l['note'] + NOTE
        n += 1
    if n != 72:
        raise SystemExit('expected 72 geared lanes, got %d' % n)
    json.dump(d, open(pout, 'w'), indent=1)
    print('declared', n)


if __name__ == '__main__':
    main()
