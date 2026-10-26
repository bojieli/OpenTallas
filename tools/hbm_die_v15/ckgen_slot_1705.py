#!/usr/bin/env python3
"""Grant the die clock root hb_ckgen (hfd_ckgen: PLL hard core ot_hbm_pll_bb + four real reset-release synchronisers) a
v5 die slot (H-DIE 2026-10-15 17:05; it had none since v5 -- HBM-V15-HARDEN 13:11 'ckgen/pll_bb have no v5 slot').
Home: the free east end of the centre glue row (east of idx_link, between scorers idx_s1 and idx_s3), the geometric
centre of the four quadrant clock roots, so the four first-level die tree branches are near equal length.
Outline 216 x 216 um = the 172.8 um PLL abstract (physical/s81_ph_views/macros/ot_s81_pll_bb, same vendor class) plus a
21.6 um ring for the reset synchronisers and the four root buffers.  Refuses on any overlap with an existing slot."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
G = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
d = json.loads(G.read_text())
slot = {"name": "hb_ckgen", "cell": "hfd_ckgen", "instance": "hb_ckgen", "source": "rtl/hbm_accel/control/hfd_ckgen.sv",
        "params": {}, "kind": "hard_macro_group", "parent": "die", "outline": {"w": 216.0, "h": 216.0},
        "origin": {"x": 16416.0, "y": 10216.8, "orient": "R0"}, "version": 5, "grant": "slot",
        "clock_entry": None, "pg_layer": "M5", "strap_layer": "M6", "signal_max_layer": "M9", "layer_cap": "M9",
        "pins": [{"name": "refclk", "face": "N", "layer": "M9", "note": "bump at the ckgen site"},
                 {"name": "por_n", "face": "N", "layer": "M9", "note": "bump at the ckgen site"},
                 {"name": "pll_hbm", "face": "centre", "layer": "M9", "note": "die clock tree root (die CTS, M8/M9)"},
                 {"name": "pll_stream", "face": "centre", "layer": "M9"}, {"name": "pll_serial", "face": "centre", "layer": "M9"},
                 {"name": "pll_link", "face": "centre", "layer": "M9"}],
        "notes": "die clock root: PLL analog core = allowed modelled hard core (owner rule 10-14 08:05); reset release = "
                 "real RTL; first tree level = four quadrant roots (die CTS, tools/hbm_die_v15/view_case.py --die-clock)",
        "granted": "H-DIE 2026-10-15T17:30-07:00"}
o, w = slot['origin'], slot['outline']
for s in d['slots']:
    if s['name'] == slot['name'] or s.get('parent') != 'die' or not s.get('origin') or not s.get('outline'):
        continue
    so, sw = s['origin'], s['outline']
    rot = so.get('orient') in ('R90', 'R270', 'MXR90', 'MYR90')
    W_, H_ = (sw['h'], sw['w']) if rot and False else (sw['w'], sw['h'])
    if o['x'] < so['x'] + W_ and so['x'] < o['x'] + w['w'] and o['y'] < so['y'] + H_ and so['y'] < o['y'] + w['h']:
        raise SystemExit(f'overlap with {s["name"]} {so} {sw}')
P = json.loads((ROOT / d['floorplan']['file']).read_text())
for n, b in P.items():
    if isinstance(b, dict) and 'x' in b and o['x'] < b['x'] + b['w'] and b['x'] < o['x'] + w['w'] and \
            o['y'] < b['y'] + b['h'] and b['y'] < o['y'] + w['h']:
        raise SystemExit(f'overlap with plan block {n} {b}')
d['slots'] = [s for s in d['slots'] if s['name'] != slot['name']] + [slot]
G.write_text(json.dumps(d, indent=1) + '\n')
print('granted hb_ckgen', o, w)
