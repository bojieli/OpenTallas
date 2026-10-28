#!/usr/bin/env python3
"""DIE-HBM-5: r4_tok.py (MESO-RECONCILE-2 planner, 12.15b spice x1.0485/x1.0552) + START-FORWARD WIRES.
A region with outgoing crossings but no incoming one is never reached by the DIRECTED start tree (kind 'unreached':
the 4 HBM status links L117/L117m/L138/L138m out of NW/NE spb0+spb1).  Fix (COORD 10-28 01:42 cond. 2: start-forward
wire, never a wider window): for each such region add one 1-bit registered start-forward crossing FROM the region its
widest outgoing crossing lands in, at that crossing's boundary point (same xing_point), so the start tree reaches it
through a real fixed-latency crossing.  The data crossings are then ordinary nontree rows.
usage: r5_sf.py SRC PLAN V FEED MAP OUT.tsv"""
import importlib.util, json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent))
import region3_tok as R3
SRC = sys.argv[1]
sys.path[:0] = [SRC + '/tools', SRC + '/tools/die_plan', SRC + '/tools/throughput', SRC + '/src',
                SRC + '/tools/hbm_b2', SRC + '/tools/s81_head']
spec = importlib.util.spec_from_file_location('count_align_plan', here / 'src_mr' / 'count_align_plan.py')
cap = importlib.util.module_from_spec(spec); spec.loader.exec_module(cap); sys.modules['count_align_plan'] = cap
if not hasattr(cap, 'DSU'):
    old = here.parent / 'src' / 'count_align_plan.py'
    s2 = importlib.util.spec_from_file_location('cap_old', old); o = importlib.util.module_from_spec(s2); s2.loader.exec_module(o)
    cap.DSU = o.DSU
import locality as Lc
FFX = 1.0552 / 1.0485
_m = Lc.margins
def margins(br_rows, Ttab, period, budget=None, ff_scale=None):
    if ff_scale is None:
        ff_scale = Ttab["classes"]["A"]["FF"]["mu_stage_ps"] / Ttab["classes"]["A"]["TT"]["mu_stage_ps"]
    return _m(br_rows, Ttab, period, budget, ff_scale * FFX)
Lc.margins = margins
_x = Lc.crossings
SF = []
def crossings(D, reg, G, padj):
    out = _x(D, reg, G, padj)
    ins = {x["rb"] for x in out}
    for r in sorted({x["ra"] for x in out} - ins):
        w = max((x for x in out if x["ra"] == r), key=lambda x: (x["width"], x["id"]))
        sf = dict(id=f"SF:{w['rb']}>{r}", src=w["dst"], dst=w["src"], ra=w["rb"], rb=r, width=1, xy=w["xy"],
                  far=w["far"], start_forward=True, for_ports=sorted(x["id"] for x in out if x["ra"] == r))
        out.append(sf); SF.append(sf)
    return out
Lc.crossings = crossings
R3.cmd_tsv(SRC, *sys.argv[2:7])
print("START_FORWARD", json.dumps([{k: s[k] for k in ("id", "ra", "rb", "xy", "for_ports")} for s in SF]))
