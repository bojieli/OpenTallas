#!/usr/bin/env python3
"""Build the tp8b Qwen die once, record the registered reset tree (_reset_tree: m['tp8_reset_tree']) and write the die
case (elements.lef, die.v, place.tcl) for tools/hier_contract/pinreg_audit.py (reset-tree 2026-10-13).

usage (repo root): python3 tools/qwen_tp8/reset_tree_run.py OUTDIR [--case]   -> OUTDIR/reset_tree.json (+ OUTDIR/case)
OT_RELAY_GATE=warn records the data-relay misses instead of raising (they are the data stream's); OT_RESET_GATE=warn
records reset nets over the reach; an unreachable reset sink/driver always FAILS (die standard) unless OT_RESET_GATE=diag
(diagnosis only, record reach_gate FAIL_DIAG)."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, 'tools')
import die_top_lint as D
import qwen_rom_fulldie_b3r2 as G

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); t = time.time()
D.QWEN_RECIPE = 'tp8b'; D._QW.clear(); D.QSRC = None
v, m = D.load_qwen()[:2]
rec = dict(m.get('tp8_reset_tree') or {})
pos = G._pin_pos(v, m)
rst = []
for bid, cl, bits, eps in m['buses']:
    if len(eps) < 2 or not (cl == 'reset' or bid.startswith(('rst', 'arst')) or '_rst_' in bid):
        continue
    pts = [pos(*e) for e in eps]
    rst.append((round(G._hp(pts), 1), bid, cl, len(eps)))
rst.sort(reverse=True)
r = m.get('r21_relays') or {}
res = dict(schema='opentallas.qwen-tp8.reset-tree-run.v1', recipe='tp8b', die=m['die'], build_s=round(time.time() - t),
           instances=len(m['insts']), reset_tree=rec, reset_named_nets=len(rst),
           reset_named_over_500=[q for q in rst if q[0] > 500.0], reset_named_worst=rst[:12],
           data_over_reach=len(r.get('over_reach') or []), data_max_pin_to_pin_um=r.get('max_pin_to_pin_um'))
(out / 'reset_tree.json').write_text(json.dumps(res, indent=1) + '\n')
if '--case' in sys.argv:
    v.case_real(m, out / 'case')
print(json.dumps({k: res[k] for k in ('build_s', 'instances', 'reset_named_nets', 'reset_named_over_500', 'data_over_reach')}))
print(json.dumps({k: rec.get(k) for k in ('long_reset_nets', 'repeaters', 'pad_rep', 'pad_p8', 'cells', 'nets', 'max_net_um',
                                         'depth_cycles', 'max_depth_cycles', 'over', 'errors')})[:3000])
