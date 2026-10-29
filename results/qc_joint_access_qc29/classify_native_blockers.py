#!/usr/bin/env python3
"""DIE-QC-29 diagnostic: why local 89,180 access PASS0 and the global 0.32-um native
landing census (2,469 FAIL) disagree. For every failed native M7 clock pin, test each
legal in-pin M8 row against (a) canonical PG only, (b) + reserved clock-cell power access,
(c) + clock M8 witnesses, at the census spacing and at plain M8 spacing 0.04.
Read-only diagnostic; no plan, tool or geometry edit."""
import argparse, json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/die_plan'))
import die_clock_128 as C
p = argparse.ArgumentParser()
for n in ['landing-plan', 'pg', 'reserved-power', 'clock-plan', 'out']: p.add_argument('--' + n, required=True)
a = p.parse_args()
L = json.load(open(a.landing_plan)); sp0 = L['spacing_um']
pg = C.pg_shapes(json.load(open(a.pg))); res = C.pg_shapes(json.load(open(a.reserved_power)))
cp = json.load(open(a.clock_plan))
wit = [('M8', r['net'], 'clock_access', r['m8_witness_y_um'] - .04, r['m8_witness_y_um'] + .04,
        r['backbone_xy_um'][0] - .096, r['backbone_xy_um'][0] + .096) for r in cp['records']]
def idx(sp, sets):
    ix = C.MetalIndex(sp)
    for tag, ss in sets:
        for s in ss: ix.add((s[0], s[1], tag, *s[3:]))
    return ix
out = {}
for sp in sorted({sp0, .16, .08, .04}, reverse=True):
    I = {'pg': idx(sp, [('pg', pg)]), 'pg+res': idx(sp, [('pg', pg), ('res', res)]),
         'pg+res+wit': idx(sp, [('pg', pg), ('res', res), ('wit', wit)])}
    cnt = collections.Counter(); first = collections.Counter(); bytype = collections.Counter()
    for f in L['failures']:
        x = f['reference_xy_um'][0]
        ok = {}
        for k, ix in I.items():
            ok[k] = any(not ix.hits(('M8', f['net'], 'access', y - .04, y + .04, x - .096, x + .096), first=True)
                        for y in f['legal_in_pin_rows_um'])
        cls = 'pass_all' if ok['pg+res+wit'] else 'blocked_by_witness' if ok['pg+res'] else \
              'blocked_by_reserved_power_access' if ok['pg'] else 'blocked_by_canonical_PG'
        cnt[cls] += 1
        if cls == 'blocked_by_canonical_PG':
            # which canonical net/layer kind is nearest
            y = f['legal_in_pin_rows_um'][0]
            h = I['pg'].hits(('M8', f['net'], 'access', y - .04, y + .04, x - .096, x + .096), first=True)
            t = I['pg'].shapes[h[0][0]]; first[(t[1], round(t[4] - t[3], 3))] += 1
        bytype[(f['inst'].split('_')[0] if f['inst'].startswith('c_') else f['inst'], cls)] += 1
    out[str(sp)] = dict(failures_rechecked=len(L['failures']), classes=dict(cnt),
                        canonical_blocker_net_width=[[list(k), v] for k, v in first.most_common(8)])
    print(sp, dict(cnt), first.most_common(4), flush=True)
Path(a.out).write_text(json.dumps(dict(source_spacing=sp0, note='rechecks only the census failures; rows = legal in-pin rows', by_spacing=out), indent=1))
