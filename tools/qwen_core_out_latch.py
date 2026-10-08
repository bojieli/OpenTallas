#!/usr/bin/env python3
"""Output lockup-latch stage for the Qwen ROM decode core (drive-0602, 2026-10-08).

Every data output bit of the top module gets a negative-level latch (yosys $_DLATCH_N_, enable = the core clock port:
transparent while clk is low, opaque while it is high).  The port is re-pointed to the latch Q; the old net becomes the
latch D.  Nothing else in the cell graph changes.

Why: under rule H1 the die-link hold term (50 ps skew + 25 ps uncertainty) is carried by the sender's output min delay,
so a pin flop must hold its output for >= 75 ps after its own clock edge; DFFHQNx1 clk->q + the output buffer is ~62 ps at
FF (core_kv_banked 77d93ac50: 647 reg->out ports at -12.9, 49 gated feedthroughs at -18.0 after the H1 SDC fix).  The latch
only changes the port at the FALLING edge, so the next rising edge cannot disturb the receiver's hold (hold slack ~ +T/2).
Cycle behaviour seen by a rising-edge receiver is unchanged (0 added cycles); the cost is setup: the port becomes valid at
T/2 + latch delay instead of clk->q, which the 0.2 T outside budget still covers at TT (see drive-0602.log).

Constant bits and the excluded clock outputs (default: u_me.clk, the gated engine clock) are left as they were.
--mutant-dff replaces the latch by a rising-edge flop (+1 cycle): the exactness bench must FAIL on it (negative control).
"""
import argparse
import json
from pathlib import Path


def apply(design, top='ot_qwen_rom_core', clock='clk', exclude=('u_me.clk',), mutant_dff=False):
    m = design['modules'][top]
    clk_bits = m['ports'][clock]['bits']
    assert len(clk_bits) == 1 and isinstance(clk_bits[0], int), 'clock port must be one net bit'
    ck = clk_bits[0]
    nxt = 1 + max([b for n in m['netnames'].values() for b in n['bits'] if isinstance(b, int)] +
                  [b for p in m['ports'].values() for b in p['bits'] if isinstance(b, int)])
    latched = 0
    for name, port in m['ports'].items():
        if port['direction'] != 'output' or name in exclude:
            continue
        newbits = []
        for i, b in enumerate(port['bits']):
            if not isinstance(b, int):          # constant output bit: nothing launches it
                newbits.append(b)
                continue
            q = nxt; nxt += 1
            cell = ({'type': '$_DFF_P_', 'parameters': {}, 'attributes': {},
                     'port_directions': {'C': 'input', 'D': 'input', 'Q': 'output'},
                     'connections': {'C': [ck], 'D': [b], 'Q': [q]}} if mutant_dff else
                    {'type': '$_DLATCH_N_', 'parameters': {}, 'attributes': {},
                     'port_directions': {'E': 'input', 'D': 'input', 'Q': 'output'},
                     'connections': {'E': [ck], 'D': [b], 'Q': [q]}})
            cname = f'ol_lat${name}[{i}]'
            assert cname not in m['cells']
            m['cells'][cname] = cell
            newbits.append(q)
            latched += 1
        if newbits != port['bits']:
            old = m['netnames'].get(name)
            if old is not None:
                m['netnames'][f'{name}__ol_d'] = old
            m['netnames'][name] = {'hide_name': 0, 'bits': newbits, 'attributes': {}}
            port['bits'] = newbits
    return latched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--top', default='ot_qwen_rom_core')
    ap.add_argument('--exclude', default='u_me.clk')
    ap.add_argument('--mutant-dff', action='store_true')
    a = ap.parse_args()
    d = json.loads(a.input.read_text())
    n = apply(d, a.top, exclude=tuple(x for x in a.exclude.split(',') if x), mutant_dff=a.mutant_dff)
    a.output.write_text(json.dumps(d, separators=(',', ':')) + '\n')
    print(json.dumps({'schema': 'qwen.core_out_latch.v1', 'latched_bits': n, 'mutant_dff': a.mutant_dff,
                      'exclude': a.exclude}))


if __name__ == '__main__':
    main()
