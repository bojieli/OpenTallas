#!/usr/bin/env python3
"""Forwarded-clock arc of a tile ETM, as a clock arc.

A tile that forwards its clock (ot_fwd_clk_inv at the face: port = ~ck) is exported by write_timing_model with the
port timed as DATA launched by ck: two register-style groups a port,

    timing_type : rising_edge    cell_fall = ck rise -> port fall (real)   cell_rise = port rise seen from ck RISE (*)
    timing_type : falling_edge   cell_rise = ck fall -> port rise (real)   cell_fall = port fall seen from ck FALL (*)

(*) the other physical edge re-referenced across half a period of the extraction clock (vm_cp_fe0 qSE[581] at TT:
591.0 = 178.6 + 412.4 and -252.6 = 168.0 - 420.6; qSE[580]: 1.6 and -38.8): not a delay of anything.  A die
`create_generated_clock -invert` on the port then takes its edge latencies from whichever table the STA version pairs
with the edge (OpenSTA 2.6.0: rise edge 0.8 ps on fe0 qSE[580], fall edge -251.7 ps on qSE[581]; 3.1.0: fall edge 174.5,
rise edge 0), so the forwarded-clock insertion the die must time is wrong on one edge or both.

This tool rewrites those two groups as ONE clock-network arc

    timing_sense : negative_unate ; timing_type : combinational ;
    cell_fall / fall_transition  <- rising_edge group   (ck rise -> port fall)
    cell_rise / rise_transition  <- falling_edge group  (ck fall -> port rise)

so the generated clock's source latency is the tile's routed insertion on BOTH edges in any STA.  Nothing else in the
library changes; the tile is not re-routed (a closed tile stands: this is a view re-export).

    fclk_arc_fix.py --lib IN.lib --ports 'qSE[580]' 'qSE[581]' --out OUT.lib      one library
    fclk_arc_fix.py --vm8 [--root .] [--out-dir DIR] [--check]                     the eight VM8 face tiles, 3 corners
                                                                                    (ports from each tile's clock.sdc)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _groups(blk: str):
    """[(start, end, text)] of the top-level timing() groups of one pin block"""
    out, i = [], 0
    while True:
        i = blk.find('timing()', i)
        if i < 0:
            return out
        j = blk.find('{', i)
        d, k = 1, j + 1
        while d:
            d += {'{': 1, '}': -1}.get(blk[k], 0)
            k += 1
        out.append((i, k, blk[i:k]))
        i = k


def _table(g: str, name: str):
    m = re.search(name + r'\s*\(([^)]*)\)\s*\{', g)
    if not m:
        return None
    d, k = 1, m.end()
    while d:
        d += {'{': 1, '}': -1}.get(g[k], 0)
        k += 1
    return g[m.start():k]


def arc_state(lib_text: str, port: str, clock: str = 'ck') -> str:
    """'clock_arc' (one negative-unate combinational arc from the clock), 'data_arcs' (the register-style export),
    'missing' (no arc from the clock) or 'other'"""
    i = lib_text.find(f'pin("{port}")')
    if i < 0:
        return 'missing'
    j = lib_text.find('\n    pin(', i + 1)
    gs = [g for _, _, g in _groups(lib_text[i:j if j > 0 else len(lib_text)]) if f'related_pin : "{clock}"' in g]
    if not gs:
        return 'missing'
    tt = sorted(re.search(r'timing_type : (\w+)', g).group(1) if 'timing_type' in g else 'combinational' for g in gs)
    if tt == ['combinational'] and 'negative_unate' in gs[0]:
        return 'clock_arc'
    if tt == ['falling_edge', 'rising_edge']:
        return 'data_arcs'
    return 'other'


def fix(lib_text: str, ports, clock: str = 'ck'):
    """-> (new text, {port: state before})"""
    st = {}
    for port in ports:
        st[port] = arc_state(lib_text, port, clock)
        if st[port] == 'clock_arc':
            continue
        if st[port] != 'data_arcs':
            raise ValueError(f'{port}: arc state {st[port]} (expected the rising_edge + falling_edge export)')
        i = lib_text.find(f'pin("{port}")')
        j = lib_text.find('\n    pin(', i + 1)
        j = j if j > 0 else len(lib_text)
        blk = lib_text[i:j]
        gs = [(a, b, g) for a, b, g in _groups(blk) if f'related_pin : "{clock}"' in g]
        by = {re.search(r'timing_type : (\w+)', g).group(1): g for _, _, g in gs}
        parts = [_table(by['rising_edge'], 'cell_fall'), _table(by['rising_edge'], 'fall_transition'),
                 _table(by['falling_edge'], 'cell_rise'), _table(by['falling_edge'], 'rise_transition')]
        if any(p is None for p in parts):
            raise ValueError(f'{port}: a delay / transition table is missing')
        ind = '        '
        new = ('timing() {\n' + ind + f'related_pin : "{clock}";\n' + ind + 'timing_sense : negative_unate;\n' + ind +
               'timing_type : combinational;\n' + ''.join(ind + p + '\n' for p in parts) + '      }')
        a0, b1 = gs[0][0], gs[-1][1]
        assert all(gs[k][1] <= gs[k + 1][0] for k in range(len(gs) - 1))
        between = ''.join(blk[gs[k][1]:gs[k + 1][0]] for k in range(len(gs) - 1)).strip()
        assert not between, (port, 'unexpected text between the clock arcs', between[:80])
        lib_text = lib_text[:i] + blk[:a0] + new + blk[b1:] + lib_text[j:]
    return lib_text, st


def vm8_ports(root: Path):
    sys.path.insert(0, str(root / 'tools'))
    import hbm_accel_die_fp as F
    return F.vm8_fwd_clock_ports(root)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--lib', type=Path)
    ap.add_argument('--ports', nargs='*', default=[])
    ap.add_argument('--clock', default='ck')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--vm8', action='store_true')
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--out-dir', type=Path, help='--vm8: write <cell>_<corner>.lib here (default: in place)')
    ap.add_argument('--check', action='store_true', help='--vm8: report the arc state of every port, write nothing')
    a = ap.parse_args(argv)
    if a.vm8:
        bad = 0
        for cell, ports in vm8_ports(a.root).items():
            for c in ('tt', 'ff', 'ss'):
                lib = a.root / f'physical/ref_tile/{cell}_cx/views/{cell}/{cell}_{c}.lib'
                txt = lib.read_text()
                if a.check:
                    st = {p: arc_state(txt, p, a.clock) for p in ports}
                else:
                    txt, st = fix(txt, ports, a.clock)
                    out = (a.out_dir / lib.name) if a.out_dir else lib
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(txt)
                n = sum(1 for v in st.values() if v != 'clock_arc')
                bad += n
                print(f'{cell} {c}: {len(ports)} forwarded-clock ports, {n} not a clock arc ' + ('(before the rewrite)' if not a.check else '') + f' {sorted(set(st.values()))}')
        return 1 if (a.check and bad) else 0
    txt, st = fix(a.lib.read_text(), a.ports, a.clock)
    (a.out or a.lib).write_text(txt)
    print(st)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
