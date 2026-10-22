#!/usr/bin/env python3
"""HBM-DIE17 10-21: exact per-bus capacity-booking attribution for relay_lanes_d4f (N->O NW window question).
Runs the UNCHANGED planner (same argv as s4 remote) with Capacity._dec wrapped: every booked um2 is credited to the
row (bus driver) whose main() loop iteration booked it, and to the kind (kept / station / forced / pad).  Self-check:
the attributed window sums must equal the planner's own window_report (exact reproduction, else exit 3).
usage: booking_attrib.py ATTRIB_OUT.json -- <relay_lanes_d4f.py args>"""
import sys, json, collections
from pathlib import Path
out = Path(sys.argv[1]); assert sys.argv[2] == '--'; argv = sys.argv[3:]
import os; sys.path.insert(0, os.environ.get('OT_LANES_TOOLS') or str(Path(__file__).resolve().parents[3] / 'tools/hbm_die_v16'))
import relay_lanes_d4f as L
book = collections.defaultdict(float); caps = {}
orig_dec = L.Capacity._dec; orig_consume = L.Capacity.consume
def consume(self, cx, cy, fp, forced=False, spread=1):
    c = sys._getframe(1); f = c
    while f is not None and f.f_code.co_name != 'main':
        f = f.f_back
    bi = f.f_locals.get('bi') if f is not None else None
    if c.f_code.co_name == 'plan_bus_cap':
        kind = 'forced' if forced else 'station'
    else:
        kind = 'kept' if f is not None and 'res' not in f.f_locals else ('pad_forced' if forced else 'pad')
    self._ctx = (bi, kind)
    return orig_consume(self, cx, cy, fp, forced=forced, spread=spread)
def dec(self, x, y, d):
    bi, kind = getattr(self, '_ctx', (None, '?')); book[(bi, kind, int(x), int(y))] += d; caps['cap'] = self
    return orig_dec(self, x, y, d)
L.Capacity.consume = consume; L.Capacity._dec = dec
rows_holder = {}
orig_wr = L.window_report
def window_report(router, cap, win_um=572.0):
    r = orig_wr(router, cap, win_um); k = max(1, int(round(win_um / (router.G * cap.k))))
    rows_holder['k'] = k; rows_holder['G'] = router.G; rows_holder['ck'] = cap.k; rows_holder['report'] = r
    return r
L.window_report = window_report
sys.argv = ['relay_lanes_d4f.py'] + argv
L.main()
st = json.loads(Path(argv[argv.index('--out') + 1]).read_text())
drivers = {bi: r['driver'] for bi, r in enumerate(st['rows'])}
k, G, ck = rows_holder['k'], rows_holder['G'], rows_holder['ck']
res = []; bad = 0
cap_ = caps['cap']; W_ = [tuple(t[1]) for t in rows_holder['report']['worst']]
for w_ in os.environ.get('OT_ATTRIB_WINDOWS', '10450,30800;9900,30800;8250,30800;12100,30800').split(';'):
    w_ = tuple(int(v) for v in w_.split(','))
    if w_ not in W_: W_.append(w_)
def _win(wx, wy):
    bx, by = int(round(wx / (ck * G))), int(round(wy / (ck * G)))
    c0 = cap_.cap0[bx:bx + k, by:by + k].sum(); u = cap_.used[bx:bx + k, by:by + k].sum()
    return (round(u / c0, 3) if c0 > 0 else None), [wx, wy], round(u), round(c0)
for ratio, (wx, wy), used, c0 in [_win(*w_) for w_ in W_]:
    bx0, by0 = int(round(wx / (ck * G))), int(round(wy / (ck * G)))
    per = collections.defaultdict(float); kinds = collections.defaultdict(float)
    for (bi, kind, x, y), d in book.items():
        if bx0 <= x < bx0 + k and by0 <= y < by0 + k:
            per[drivers.get(bi, str(bi))] += d; kinds[kind] += d
    tot = sum(per.values()); ok = abs(tot - used) <= 1.0; bad += not ok
    res.append(dict(window=[wx, wy], ratio=ratio, used=used, cap=c0, attributed=round(tot, 1), exact=ok,
                    kinds={a: round(b, 1) for a, b in kinds.items()},
                    buses=sorted(([n, round(v, 1)] for n, v in per.items()), key=lambda t: -t[1])))
out.write_text(json.dumps(dict(tool='booking_attrib.py (HBM-DIE17)', argv=argv, windows=res), indent=1, default=float) + '\n')
print('BOOKING_ATTRIB', 'EXACT' if not bad else f'MISMATCH {bad}', 'windows', len(res)); sys.exit(3 if bad else 0)
