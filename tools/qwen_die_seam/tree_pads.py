#!/usr/bin/env python3
"""qwen-tp8 2026-10-12: tree-leg relay pads for a die netlist (gen_bench.tree_pads: the array bench's arrival model).

    tree_pads.py --die-v die.v --out pads.json      ({bus (no n_ prefix): pads}, misaligned nodes before padding)
The die generator's tp8a recipe reads pads.json (tp8 cfg 'tree_pads') and adds that many relays at the sink end of
each tree word, so every node's legs arrive on the same cycle (array bench PASS with 0 deskew).
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract, gen_bench  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--die-v', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()
inst, buses = extract.parse(a.die_v)
S = dict(buses=buses, slots={n: dict(master=m, pins=p) for n, (m, p) in inst.items() if not m.startswith('qfd_rly')})
pads, mis, nodes = gen_bench.tree_pads(S)
rec = dict(source=a.die_v, nodes=nodes, misaligned_nodes=mis, pad_relays=sum(pads.values()),
           pads={b[2:] if b.startswith('n_') else b: k for b, k in sorted(pads.items())})
Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps({k: rec[k] for k in ('nodes', 'misaligned_nodes', 'pad_relays')}))
