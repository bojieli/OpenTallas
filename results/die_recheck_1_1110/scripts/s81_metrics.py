#!/usr/bin/env python3
"""DIE-RECHECK-1 (DO_NOT_COUNT): die-level numbers of one S81 clock-only die route variant.

  s81_metrics.py PLAN ROUTE_DIR OUT_DIR TREE_JSON [--label L]   -> OUT_DIR/metrics.json (+ prints it)

(a) die tap arrival spread per corner (arr_<C>.txt T lines x spice cal, as ds85_arrivals);
(b) per-partition arrival-contract check (METHODOLOGY 12.25 cond 3): within each partition, max-min of its die tap
    arrivals vs the plan clock.tap_window (per_type_ps[type] else window_ps), per corner;
(c) landings (arrivals_detail.json rows): unshared die stages, window need W = p_up + p_dn (OCV/droop range of the
    phase), STRUCTURAL count W > P - 2*margin (no K/phase choice can give a 1-cycle window with the 100 ps margin on
    both sides), and the wrapped clearance s = max(-hi, lo) of d folded into (-P/2, P/2] (s < 0 = NEAR/EDGE);
(d) LPS classes from report.json (TOK-VERIFY-1's table, raw and wrapped).
"""
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

P, M = 833.0, 100.0
plan = json.loads(Path(sys.argv[1]).read_text())
R, O, tree = Path(sys.argv[2]), Path(sys.argv[3]), json.loads(Path(sys.argv[4]).read_text())
label = sys.argv[sys.argv.index('--label') + 1] if '--label' in sys.argv else O.name
det = json.loads((O / 'arrivals_detail.json').read_text())
parts = {p['name']: p for p in plan['partitions']}
tw = plan['clock'].get('tap_window') or {}
W0, per_type = float(tw.get('window_ps') or 180.0), tw.get('per_type_ps') or {}
out = dict(label=label, corners={})
for C in ('TT', 'FF'):
    k = det['corners'][C]['spice_factor']
    T = {}
    for ln in (R / f'arr_{C}.txt').read_text().splitlines():
        x = ln.split()
        if x and x[0] == 'T':
            T[x[1]] = float(x[2]) * k
    tp = defaultdict(list)
    for t in tree['taps']:
        if t['port'] in T:
            tp[t['part']].append(T[t['port']])
    viol = []
    for part, v in tp.items():
        typ = parts[part]['type']
        lim = float(per_type.get(typ, W0)) if not isinstance(per_type.get(typ), dict) else W0
        if len(v) > 1 and max(v) - min(v) > lim:
            viol.append((part, typ, round(max(v) - min(v), 1), lim))
    viol.sort(key=lambda x: x[3] - x[2])
    rows = [r for r in det['corners'][C]['rows'] if 'd_ps' in r]
    need = sorted(r['p_up_ps'] + r['p_dn_ps'] for r in rows)
    unsh = sorted(r['die_stages_fwd'] + r['die_stages_local'] for r in rows)

    def wrap(x):
        return x - P * round(x / P)
    clr = []
    for r in rows:
        d = wrap(r['d_ps'])
        hi, lo = d + r['p_up_ps'], d - r['p_dn_ps']
        clr.append((max(-hi, lo) - M, r['port'], r['src'], r['dst'], round(r['p_up_ps'] + r['p_dn_ps'], 1),
                    r['die_stages_fwd'] + r['die_stages_local'], r['src_view'], r['dst_view']))
    clr.sort()
    allv = sorted(T.values())
    out['corners'][C] = dict(
        taps=len(allv), tap_arr_min=round(allv[0], 1), tap_arr_max=round(allv[-1], 1),
        contract_parts=len(tp), contract_viol=len(viol), contract_worst=viol[:8],
        landings=len(rows), unshared_stages_p50=unsh[len(unsh) // 2], unshared_stages_p90=unsh[int(.9 * len(unsh))],
        unshared_stages_max=unsh[-1], window_need_p50=round(need[len(need) // 2], 1),
        window_need_p90=round(need[int(.9 * len(need))], 1), window_need_max=round(need[-1], 1),
        structural_over=sum(w > P - 2 * M for w in need),
        wrapped_clear_below0=sum(c[0] < 0 for c in clr), wrapped_worst=[c for c in clr[:8]])
rep = O / 'report.json'
if rep.exists():
    r = json.loads(rep.read_text())
    out['lps_raw'], out['lps_wrapped'] = r['raw']['all'], r['wrapped']['all']
(O / 'metrics.json').write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
