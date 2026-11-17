"""FABLE-FIX-HEAD-CORRIDOR: bit-slice COLUMN form for the NF15f relay ranks of hd_lep0N.
Each relay rank (tags *_r<k>, rxh_l<k>) becomes one narrow, tall stage rect (W um wide) in a keepout-free site column; every FF
then sits on its own bit's horizontal trunk (alloc_r5 --columns checks exactly that).  For every candidate x the free y runs
are taken (hard cores / SRAMs + 2 um, clock reserved sites, landing pins, every other stage group + 1 um, columns already
placed + 1 um); a bit can use the run where its reach window (405 um to the FF on the trunk, from each source rect and to each
dest rect, the Q side less the jog) overlaps it.  Chosen: all bits feasible, then the widest worst-bit overlap, then the
centre of the hop.  The rect is the run cut to the union of the bit windows.  Base (non-relay) groups are NOT moved: run it on
a plan whose base groups are already legal (place_anchors2 step 2).
usage: place_cols.py PLAN EDGES OUT_PLAN COLS.json REPORT.json [W_um=10.8] [JOG=8.64] [KEEP_COMPACT tag,tag]"""
import json, sys, collections, hashlib
import numpy as np
from pathlib import Path
pp, ep, op, cp, rp = map(Path, sys.argv[1:6]); CW = float(sys.argv[6]) if len(sys.argv) > 6 else 10.8; J = float(sys.argv[7]) if len(sys.argv) > 7 else 8.64
P = json.loads(pp.read_text()); E = json.loads(ep.read_text())['edges']
t = P['partition_types']['hd_lep0N']; gs = t['clock']['landing_contract']['native_stage_groups']['groups']
W, H = t['outline_um']; R = 405.0; PITCH = 2.16; MINW = 6.0
SWAP = {'R90', 'R270', 'MXR90', 'MYR90', 'W', 'E', 'FW', 'FE'}
def macro_rect(h):
    (x, y), (w, hh) = h['origin_um'], h['outline_um']
    if h.get('orient') in SWAP: w, hh = hh, w
    return [x, y, x + w, y + hh]
MAC = [(h['inst'], macro_rect(h)) for h in t['hard_cores']]
RSV = [r['rect_um'] for r in t['clock'].get('reserved_sites_um', [])]
PIN = [[p['xy_um'][0] - 0.5, p['xy_um'][1] - 0.5, p['xy_um'][0] + 0.5, p['xy_um'][1] + 0.5]
       for p in t['clock']['landing_contract'].get('pins', []) if p.get('xy_um')]
KEEP = set(x for x in (sys.argv[8] if len(sys.argv) > 8 else '').split(',') if x)   # relay tags that stay compact anchors (as in PLAN)
def is_col(tag):
    n = tag.split(':')[-1]; return n not in KEEP and (('_r' in n and n.split('_r')[-1].isdigit()) or n.startswith('rxh_l'))
def ov(a, b): return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6
base = {}
for g in gs:
    if not is_col(g['tag']): base[(g['tag'], tuple(g['rect_um']))] = g['rect_um']
OBS = [[m[0] - 2, m[1] - 2, m[2] + 2, m[3] + 2] for _, m in MAC] + RSV + PIN + [[r[0] - 1, r[1] - 1, r[2] + 1, r[3] + 1] for r in base.values()]
YLO = max([m[3] for _, m in MAC if m[3] < H / 2 and m[2] - m[0] > 500]) + 2.0; YHI = min([m[1] for _, m in MAC if m[1] > H / 2 and m[2] - m[0] > 500]) - 2.0
# per relay FF: its source rects and its dest rects
Sb = collections.defaultdict(dict); Db = collections.defaultdict(lambda: collections.defaultdict(set))
for e in E:
    k = e.get('kind', '')
    if k.endswith('(to relay)'):
        tag = ':'.join(e['dest_id'].split(':')[1:3]); Sb[tag][(e['dest_id'], str(e['dest_bit']))] = tuple(tuple(r) for r in e.get('source_rects_um', [e['source_rect_um']]))
    elif k.endswith('(from relay)'):
        tag = ':'.join(e['source_id'].split(':')[1:3]); Db[tag][(e['source_id'], str(e['source_bit']))].add(tuple(e['dest_rect_um']))
tags = sorted([tg for tg in Sb if is_col(tg)], key=lambda x: -len(Sb[x]))
placed = []; cols = {}; rep = []
xs = np.arange(4.32, W - CW - 4.32, PITCH)
def runs(x0, x1, obs):
    iv = sorted((max(YLO, o[1]), min(YHI, o[3])) for o in obs if o[0] < x1 - 1e-6 and x0 < o[2] - 1e-6 and o[1] < YHI and o[3] > YLO)
    out = []; cur = YLO
    for lo, hi in iv:
        if lo > cur + 1e-6: out.append((cur, lo))
        cur = max(cur, hi)
    if cur < YHI - 1e-6: out.append((cur, YHI))
    return out
for tg in tags:
    bits = list(Sb[tg]); cls = collections.Counter((Sb[tg][b], frozenset(Db[tg].get(b, ()))) for b in bits); C = list(cls)
    best = None; HNEED = max(40.0, len(bits) / 18.0)      # tracks for the rank: every bit needs a trunk row inside the column span
    for x in xs:
        x0, x1 = float(x), float(x) + CW
        lo = np.full(len(C), -1e9); hi = np.full(len(C), 1e9)
        for i, (S, D) in enumerate(C):
            for s in S:
                b = R - max(abs(x0 - s[2]), abs(x1 - s[0])) - (s[3] - s[1]) / 2; c = (s[1] + s[3]) / 2; lo[i] = max(lo[i], c - b); hi[i] = min(hi[i], c + b)
            for d in D:
                b = R - J - max(abs(x0 - d[2]), abs(x1 - d[0])) - (d[3] - d[1]) / 2; c = (d[1] + d[3]) / 2; lo[i] = max(lo[i], c - b); hi[i] = min(hi[i], c + b)
        if (hi - lo).max() < MINW: continue
        xc = (x0 + x1) / 2      # bits whose source and dests lie on opposite sides of the column share ONE track (D | FF | Q)
        opp = int(sum(n for (S, D), n in cls.items() if D and ((max(s[2] for s in S) <= xc and min(d[0] for d in D) >= xc) or (min(s[0] for s in S) >= xc and max(d[2] for d in D) <= xc))))
        for r0, r1 in runs(x0, x1, OBS + placed):
            o = np.minimum(hi, r1) - np.maximum(lo, r0); nok = int(sum(n for (c, n), v in zip(cls.items(), o) if v >= MINW))
            sc = (nok, int(min(float(o.min()), r1 - r0) >= HNEED), opp, round(min(float(o.min()), 80.0), 1), round(min(float(np.median(o)), 120.0), 1))
            if best is None or sc > best[0]: best = (sc, x0, x1, max(r0, float(lo.min())), min(r1, float(hi.max())), float(o.min()))
    assert best, ('NO COLUMN', tg)
    sc, x0, x1, y0, y1, omin = best; rect = [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]
    cols[tg] = rect; placed.append([rect[0] - 1, rect[1] - 1, rect[2] + 1, rect[3] + 1])
    rep.append(dict(tag=tg, ff=len(bits), rect_um=rect, h_um=round(y1 - y0, 2), bits_feasible=sc[0], height_ok=sc[1], bits_one_track=sc[2], worst_bit_window_um=round(omin, 1)))
    print('COLUMN %-16s ff %5d x %.2f y %.2f..%.2f h %.1f feasible %d/%d one-track %d worst window %.1f' % (tg, len(bits), x0, y0, y1, y1 - y0, sc[0], len(bits), sc[2], omin), flush=True)
old = {}
for g in gs:
    if g['tag'] in cols: old.setdefault(g['tag'], list(g['rect_um'])); g['rect_um'] = list(cols[g['tag']])
bad = []
for g in gs:
    r = g['rect_um']; m = [i for i, q in MAC if ov(r, q)]; s = sum(1 for q in RSV if ov(r, q)); p = sum(1 for q in PIN if ov(r, q))
    if m or s or p: bad.append(dict(tag=g['tag'], rect_um=r, macros=m, reserved_sites=s, pins=p))
uniq = {}
for g in gs: uniq[(g['tag'], tuple(g['rect_um']))] = g['rect_um']
ul = list(uniq.items()); gov = [(a[0][0], b[0][0]) for i, a in enumerate(ul) for b in ul[i + 1:] if ov(a[1], b[1]) and (a[0][0] in cols or b[0][0] in cols)]
op.write_text(json.dumps(P, indent=1) + '\n'); cp.write_text(json.dumps(cols, indent=1) + '\n')
rp.write_text(json.dumps(dict(schema='opentallas.head_nf15f_relay_columns.v1', plan_in=hashlib.sha256(pp.read_bytes()).hexdigest(),
    plan_out=hashlib.sha256(op.read_bytes()).hexdigest(), width_um=CW, jog_um=J, columns=rep, old_rect_um=old, keepout_overlaps=bad,
    column_group_overlaps=gov, infeasible=[r['tag'] for r in rep if r['bits_feasible'] < r['ff']]), indent=1) + '\n')
print('COLS_PLACE columns', len(cols), 'infeasible', [r['tag'] for r in rep if r['bits_feasible'] < r['ff']], 'keepout_overlaps', len(bad), 'group_overlaps', len(gov), 'plan', hashlib.sha256(op.read_bytes()).hexdigest()[:16], flush=True)
sys.exit(3 if bad or gov else 0)
