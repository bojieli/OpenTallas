#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v part 2: plan pin moves for PIN-BOUND cores (DIE-HBM-61/MEM 11-03, no RTL):
  ot_hnx_idxn_keybuf_slice   key_out -> E face (all 2231 pins were on W; H need 223 < 293.76), rest stays;
  ot_hbm_sm_vm_wr_q_t_lanes4 3667 face pins re-balanced over all 4 faces of its 142.56 x 216 slot (no outline change: a
  taller slot breaks 22 q_hub stations) at a 0.168 mean pitch (0.144/0.192 alternating on the 0.048 lattice, 5.95 pins/um).
Pins: M4 on W/E, M5 on N/S (cores pin on M4/M5, M5 ceiling), 0.096 face inset, 0.048 lattice offset 0.024 (as the
tables), 8.64 corner keep-out, pitch 0.192 (5 pins/um, under the 6/um GEOM density limit).  Whole port groups move;
a group is split over two faces only if no face can hold it.  Interior (clock-entry) pins unchanged.
    python3 mk_repin.py PLAN_DIR   (in place: new tables cores/<stem>__p2pin.json, plan pins_file repointed; repin_event.json)"""
import json, re, sys, collections
from pathlib import Path
d = Path(sys.argv[1]); pp = d / 'die_plan.json'; P = json.loads(pp.read_text())
SPEC = {'ot_hnx_idxn_keybuf_slice': {'force': {'key_out': 'E'}, 'balance': False, 'step': 0.192},
        'ot_hbm_sm_vm_wr_q_t_lanes4': {'force': {}, 'balance': True, 'step': 0.168}}
STEP, KO, IN = 0.192, 8.64, 0.096
base = lambda n: re.sub(r'\[\d+\]$', '', n)
bitn = lambda n: int(m.group(1)) if (m := re.search(r'\[(\d+)\]$', n)) else -1
ev, newpf = [], {}
# partner directions per (module, port) from the SAME check.py core_faces model (collect=), so the balance puts each
# moved port group on a core face that faces its partners (no new core_faces FAIL)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools' / 'die_plan'))
import check as C, schema as SC                                       # noqa: E402
_rec = []
C.check_core_faces(SC.Plan(json.loads(pp.read_text()), pp), C.Report(True), str(d), collect=_rec)
_ori = {(tn, h['inst']): h.get('orient', 'R0') for tn, t in P['partition_types'].items() for h in t.get('hard_cores') or []}
_mod = {(tn, h['inst']): h['module'] for tn, t in P['partition_types'].items() for h in t.get('hard_cores') or []}
_OPP = dict(N='S', S='N', E='W', W='E')
def _tf(o, f):
    if o in ('MX', 'R180') and f in 'NS': f = _OPP[f]
    if o in ('MY', 'R180') and f in 'EW': f = _OPP[f]
    return f
SCORE = collections.defaultdict(lambda: collections.defaultdict(list))  # (module, port) -> core face -> [best cos per inst]
for r in _rec:
    m_ = _mod.get((r['type'], r['inst']))
    if m_ in SPEC:
        o = _ori[(r['type'], r['inst'])]
        for f in 'NSEW':
            n_ = C._NORMAL[_tf(o, f)]
            SCORE[(m_, r['port'])][f].append(max(n_[0] * ux + n_[1] * uy for _, ux, uy in r['dirs']))
for t in P['partition_types'].values():
    for h in t.get('hard_cores') or []:
        m = h['module']
        if m not in SPEC:
            continue
        pf = h['pins_file']; W, H = (round(v, 3) for v in h['outline_um'])
        k = (pf, W, H)
        if k not in newpf:
            pins = json.loads((d / pf).read_text())
            def face(p):
                dd = {'W': p['x'], 'E': W - p['x'], 'S': p['y'], 'N': H - p['y']}
                f = min(dd, key=dd.get)
                return f if dd[f] < 2 else 'I'
            groups = collections.OrderedDict()
            for p in pins:
                f = face(p)
                if f == 'I':
                    continue
                groups.setdefault(base(p['name']), dict(face=f, pins=[]))['pins'].append(p)
            STP = SPEC[m]['step']
            cap = {f: int(((H if f in 'WE' else W) - 2 * KO) / STP) + 1 for f in 'NSEW'}
            old = collections.Counter(g['face'] for g in groups.values() for _ in g['pins'])
            for g, f in SPEC[m]['force'].items():
                groups[g]['face'] = f
            assign = collections.defaultdict(list)          # face -> [(group, pins)]
            used = collections.Counter()
            order = sorted(groups.items(), key=lambda kv: -len(kv[1]['pins'])) if SPEC[m]['balance'] else list(groups.items())
            if SPEC[m]['balance']:
                # minimal move, bit level: every group keeps its face; an over-capacity face sheds bits (highest bit
                # indices first) to faces with room, choosing the (group, face) moves that keep every instance's port
                # mean cos >= THR (the SAME check.py core_faces score; FAIL is < FACE_AWAY_COS), largest safe chunk
                # first; groups with no known partner move first (no score).
                THR = C.FACE_AWAY_COS + 0.01
                sc = lambda g, f: SCORE.get((m, g), {}).get(f, [])
                cnt = {g: collections.Counter({gd['face']: len(gd['pins'])}) for g, gd in groups.items()}
                load = collections.Counter({f: 0 for f in 'NSEW'})
                for g, gd in groups.items():
                    load[gd['face']] += len(gd['pins'])

                def safe(g, f, q):
                    n = len(groups[g]['pins']); a_, b_ = sc(g, f), sc(g, q)
                    if not a_:
                        return n
                    k = n
                    for i in range(len(a_)):
                        tot = sum(cnt[g][x] * sc(g, x)[i] for x in cnt[g])
                        if b_[i] < a_[i]:
                            k = min(k, int((tot - THR * n) / (a_[i] - b_[i]) + 1e-9))
                    return max(k, 0)
                for f in sorted('NSEW', key=lambda q: -(load[q] - cap[q])):
                    while load[f] > cap[f]:
                        ex = load[f] - cap[f]; best = None
                        for g in groups:
                            if cnt[g][f] <= 0:
                                continue
                            for q in 'NSEW':
                                if q == f or load[q] >= cap[q]:
                                    continue
                                kk = min(cnt[g][f], cap[q] - load[q], ex, safe(g, f, q))
                                loss = sum(x - y for x, y in zip(sc(g, f), sc(g, q))) if sc(g, f) else -1e9
                                key = (kk > 0, bool(sc(g, f)) is False, kk, -loss)
                                if best is None or key > best[0]:
                                    best = (key, g, q, kk)
                        assert best is not None and best[3] > 0, (m, f, load, 'no safe bit move')
                        _, g, q, kk = best
                        cnt[g][f] -= kk; cnt[g][q] += kk; load[f] -= kk; load[q] += kk
                for g, gd in groups.items():
                    ps = sorted(gd['pins'], key=lambda p: bitn(p['name']))
                    o = gd['face']; keep = cnt[g][o]
                    assign[o].append((g, ps[:keep])); rest = ps[keep:]
                    for q in 'NSEW':
                        if q != o and cnt[g][q] > 0:
                            assign[q].append((g, rest[:cnt[g][q]])); rest = rest[cnt[g][q]:]
                    assert not rest
                order = []                                     # (balance done above)
            for g, gd in order:
                n = len(gd['pins']); f = gd['face']
                if f is None:                                  # split over the faces with room
                    rest = sorted(gd['pins'], key=lambda p: bitn(p['name']))
                    for q in sorted('NSEW', key=lambda q: -(cap[q] - used[q])):
                        take = min(len(rest), cap[q] - used[q])
                        if take > 0:
                            assign[q].append((g, rest[:take])); used[q] += take; rest = rest[take:]
                    assert not rest, (m, g)
                    continue
                assign[f].append((g, sorted(gd['pins'], key=lambda p: bitn(p['name'])))); used[f] += n
            out = [p for p in pins if face(p) == 'I']
            for f, lst in assign.items():
                n = sum(len(x) for _, x in lst); L = H if f in 'WE' else W
                step = STP if n <= cap[f] else (L - 2 * KO) / max(n - 1, 1)
                span = (n - 1) * step; s0 = round(round((L - span) / 2 / 0.048) * 0.048 + 0.024, 3)
                i = 0
                for g, ps in lst:
                    for p in ps:
                        v = round(s0 + round(i * step / 0.048) * 0.048, 3); i += 1
                        q = dict(p)
                        if f == 'W': q.update(x=IN, y=v, layer='M4')
                        elif f == 'E': q.update(x=round(W - IN, 3), y=v, layer='M4')
                        elif f == 'S': q.update(x=v, y=IN, layer='M5')
                        else: q.update(x=v, y=round(H - IN, 3), layer='M5')
                        out.append(q)
            assert len(out) == len(pins)
            stem = re.sub(r'(\.json)?(\.gz)?$', '', pf)
            npf = stem + '__p2pin.json'
            (d / npf).write_text(json.dumps(out) + '\n')
            newpf[k] = npf
            ev.append(dict(module=m, pins_file=pf, new_pins_file=npf, outline=[W, H], pins=len(pins),
                           faces_old=dict(old), faces_new={f: sum(len(x) for _, x in lst) for f, lst in assign.items()},
                           capacity=cap))
        h['pins_file'] = newpf[k]
pp.unlink(); pp.write_text(json.dumps(P, indent=1) + '\n')
(d / 'repin_event.json').write_text(json.dumps(dict(schema='opentallas.hbm_plan_event.v1', event='d44v-p2-repin', tables=ev), indent=1) + '\n')
for e in ev: print(e['module'], e['outline'], e['faces_old'], '->', e['faces_new'])
