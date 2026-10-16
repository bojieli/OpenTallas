#!/usr/bin/env python3
"""Additive writer pin grant: move ONLY the 1-bit sticky `fault` output from the NE corner (E 384.444) to the
W face beside the address/valid capture strip it checks (W 14.844, an existing 0.288 um gap in rgx_addr).

Measured reason (mid-W gate bb557ca99, read-only TT post-CTS STA): the single failing endpoint of the tile is the
fault pin-register clone ot_prs_00000_ff at (95.9, 384.5).  Every check source sits on the opposite corner
(a0/v0 capture W y5..33, tkw lane-4 address S face) or on the N face (sid/ingress_slot/slot_* meta capture), so the
check cone was placed in the SW and its result travelled ~380 um back up: sid_q -48.60, islot_q -46.33,
rgx_ctrl -39.24, tkw -11.84 ps (all into this one endpoint, 150 ps related-root uncertainty retained).  SID is not
the cause by itself (islot fails equally), so a SID-specialised master set cannot close it; one master + this pin.
Same RTL, same 16 roots, same cycles; every other of the 5,099 bits keeps its exact grant."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'results/arch/hbm_die_v15/writer_roots_v6_wmid_1016'
OUT = ROOT / 'results/arch/hbm_die_v15/writer_roots_v6_fsw_1016'
NEW = ('M4', 'W', 14.844)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lines = (SRC / 'assigned_pins.tcl').read_text().splitlines()
    rec = re.compile(r'ot_assigned_pin_exact \{([^}]+)\} (M\d) ([NSEW]) ([\d.]+)')
    pins = {m[1]: (m[2], m[3], float(m[4])) for m in map(rec.match, lines) if m}
    old = pins['fault']
    # legality: W/E faces have no strap exclusions; keep >=0.096 to signal pins and >=0.192 to clock pins
    for n, (l, f, v) in pins.items():
        if n != 'fault' and f == NEW[1]:
            need = 0.192 if n.startswith('clk_') else 0.096
            assert abs(v - NEW[2]) >= need - 1e-9, (n, v)
    out = [re.sub(r'\{fault\} M\d [NSEW] [\d.]+', f'{{fault}} {NEW[0]} {NEW[1]} {NEW[2]:.6f}', s) for s in lines]
    assert sum(a != b for a, b in zip(lines, out)) == 1
    (OUT / 'assigned_pins.tcl').write_text('\n'.join(out) + '\n')
    g = json.loads((SRC / 'grant.json').read_text())
    s = g['slots'][0]
    for p in s['pins']:
        if p['name'] == 'fault':
            p.update(face=NEW[1], layer=NEW[0], bit_centres_um=[NEW[2]], offset=NEW[2],
                     span_um=[round(NEW[2] - .048, 6), round(NEW[2] + .048, 6)])
    fc = s['face_capacity']
    fc['E']['bits'] -= 1
    fc['W']['bits'] += 1
    for f in 'EW':
        fc[f]['utilization'] = round(fc[f]['bits'] * .096 / fc[f]['length_um'], 6)
        assert fc[f]['utilization'] <= .60
    g['structural_successor'] = ('fault output moved E384.444 -> W14.844 beside the checked capture strip; '
                                 'clk_body mid-W grant and all other 5,099 bits unchanged; source/cycles unchanged')
    (OUT / 'grant.json').write_text(json.dumps(g, indent=1) + '\n')
    (OUT / 'changes.json').write_text(json.dumps({'base_grant': 'writer_roots_v6_wmid_1016 (863313e0a)',
                                                  'fault': {'before': list(old), 'after': list(NEW)}}, indent=1) + '\n')
    print('fault', old, '->', NEW)


if __name__ == '__main__':
    main()
