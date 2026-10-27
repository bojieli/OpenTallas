#!/usr/bin/env python3
"""PATH-S81-PD4: apply Codex bk_tx64_delta (u_bk_sel.u_tx origin y 25.92 -> 64.8, x unchanged, no outline change).
Translates every coordinate owned by the TX core consistently: hard-core origin, its plan-defined clock entry
(clock.taps kind=core name=u_bk_sel.u_tx), any reset entry naming it, and internal-station endpoints that sit on the
old TX rectangle (regs between are left to the G0C reach gate, which must still pass)."""
import json, sys
src, dst, rep = sys.argv[1:4]
TYPE = 'bk_sel__t2_phy1026_bk_sel'; INST = 'u_bk_sel.u_tx'; DY = 64.8-25.92
raw = json.load(open(src)); t = raw['partition_types'][TYPE]
hc = next(c for c in t['hard_cores'] if c['inst'] == INST)
assert abs(hc['origin_um'][1]-25.92) < 1e-6 and abs(hc['origin_um'][0]-8.64) < 1e-6, hc['origin_um']
x0, y0 = hc['origin_um']; w, h = hc['outline_um']; old = (x0, y0, x0+w, y0+h)
others = [c for c in t['hard_cores'] if c is not hc]
new = (x0, y0+DY, x0+w, y0+h+DY)
ov = [c['inst'] for c in others if not (c['origin_um'][0] >= new[2] or c['origin_um'][0]+c['outline_um'][0] <= new[0]
      or c['origin_um'][1] >= new[3] or c['origin_um'][1]+c['outline_um'][1] <= new[1])]
assert not ov, ov
assert new[3] <= t['outline_um'][1]
hc['origin_um'] = [x0, round(y0+DY, 6)]
log = dict(type=TYPE, inst=INST, origin_from=[x0, y0], origin_to=hc['origin_um'], dy=round(DY, 6), clock=[], stations=[])
for tp in t['clock'].get('taps', []):
    if tp.get('name') == INST:
        a = list(tp['xy']); tp['xy'] = [tp['xy'][0], round(tp['xy'][1]+DY, 6)]; log['clock'].append([a, tp['xy']])
inside = lambda p: old[0]-1 <= p[0] <= old[2]+1 and old[1]-1 <= p[1] <= old[3]+1
for st in t.get('internal_stations', []):
    for k in ('from_um', 'to_um'):
        if k in st and inside(st[k]):
            a = list(st[k]); st[k] = [st[k][0], round(st[k][1]+DY, 6)]; log['stations'].append(dict(conn=st.get('conn'), end=k, frm=a, to=st[k]))
t['note'] = t.get('note', '')+'; PATH-S81-PD4 10-26: bk_tx64 (u_tx y 25.92->64.8, Codex bk_tx64_delta, 0/6 storage-band FAIL probe)'
json.dump(raw, open(dst, 'w'), separators=(',', ':')); json.dump(log, open(rep, 'w'), indent=1)
print(json.dumps(dict(clock=log['clock'], stations=len(log['stations']))))
