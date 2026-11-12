"""S81-LEAF-CYC quad2 composer stage (DIE-S81-87 ready8; RTL claude/s81-leaf-cyc2-1111@63676d718d59, CS_HI/HO D2 GS2 G4).

usage: python3 stage_leaf_cyc2.py IN OUT REPORT        (cwd = a repo root; type_keys: hard_cores, internal_stations)

Applies on top of the CURRENT layout of each type (whatever earlier stages / clean-slate sidecars left in IN):
  every ot_s81sl_leaf__* type EXCEPT the KV slice types (partitions s_0S_L*: ot_s81sl_slice_w3 sets their depths through
  LF_CS_*, the quad2 wrappers do not touch them) =>
  (1) lane permutation: the 16 identical hcpost lane cores (module + outline asserted equal) are re-assigned among their
      OWN current slots (origin + orient as found in IN), so a quad of 4 lanes is compact (local swap search, seed 1).
      Precedence: no coordinate from any earlier plan is written; a lane moved by a clean-slate sidecar keeps the
      sidecar's slot set, only the lane-index -> slot map changes (positions-only, EQ by construction).
  (2) internal_stations: every vn hq_/hr_/hw_ <-> vp lane entry becomes regs_um [m, q] (q = quad stage, m = Manhattan
      minimax point of the group's vn pins and q; one site pair per quad and direction = the two shared stages
      kit_istations sites); entries added for every vn h-port x lane so the permuted lanes are covered; the lane end
      (to_um) follows its lane: the point of the lane box nearest the vn pin (+ track offset), the convention the
      stored entries already use.  Chains whose stored endpoints are swapped (lane end
      in from_um) are detected by geometry and kept in their stored direction.  Other entries are untouched.
  clock is NOT touched (the reverse reset collector tree is unchanged); REPORT carries collector_reach before/after.
Fails (exit 2, nothing written to OUT) when any hop of a touched entry is > 405 um.
"""
import json, random, re, sys
from pathlib import Path

LIM, QMAX, G = 405.0, 390.0, 4
RX = re.compile(r"^core:u_lf\.u_vn\.u_[ab]\.(hq_|hr_|hw_)\w+\|(?:core:)?u_lf\.u_vp\.g_ln\[(\d+)\]\.u_l$")
M = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def ctr(h):
    (x, y), (w, hh) = h['origin_um'], h['outline_um']
    return (x + w / 2, y + hh / 2)


def box_d(p, h):
    (x, y), (w, hh) = h['origin_um'], h['outline_um']
    return max(x - p[0], 0, p[0] - x - w) + max(y - p[1], 0, p[1] - y - hh)


def loc(p, h):
    (ox, oy), (w, hh), o = h['origin_um'], h['outline_um'], h.get('orient', 'R0')
    x, y = p[0] - ox, p[1] - oy
    return (w - x if o in ('MY', 'R180') else x, hh - y if o in ('MX', 'R180') else y)


def glob(lc, h):
    (ox, oy), (w, hh), o = h['origin_um'], h['outline_um'], h.get('orient', 'R0')
    return [round(ox + (w - lc[0] if o in ('MY', 'R180') else lc[0]), 3),
            round(oy + (hh - lc[1] if o in ('MX', 'R180') else lc[1]), 3)]


def near(v, h):       # plan convention for a core end: the lane box point nearest the vn pin (+ track offset)
    (ox, oy), (w, hh) = h['origin_um'], h['outline_um']; dx, dy = h.get('track_offset_um', [0.0, 0.0])
    return [round(min(max(v[0], ox), ox + w) + dx, 3), round(min(max(v[1], oy), oy + hh) + dy, 3)]


def regroup(slots, vn):
    def score(a):
        wl = wf = tot = 0
        for g in range(16 // G):
            q = [slots[a[l]] for l in range(G * g, G * g + G)]
            c = (sum(p[0] for p in q) / G, sum(p[1] for p in q) / G)
            last = max(M(c, p) for p in q); far = max(M(v, c) for v in vn)
            wl, wf, tot = max(wl, last), max(wf, far), tot + last
        return (max(wl - LIM, 0) + max(wf - 2 * LIM, 0), wl, wf, tot)
    best, rnd = None, random.Random(1)
    for start in range(40):
        a = list(range(16))
        if start:
            rnd.shuffle(a)
        s, imp = score(a), True
        while imp:
            imp = False
            for i in range(16):
                for j in range(i + 1, 16):
                    if i // G == j // G:
                        continue
                    a[i], a[j] = a[j], a[i]; s2 = score(a)
                    if s2 < s:
                        s, imp = s2, True
                    else:
                        a[i], a[j] = a[j], a[i]
        if best is None or s < best[0]:
            best = (s, a[:])
    return best[1], score(list(range(16))), best[0]


def center(pts):
    us = [p[0] + p[1] for p in pts]; vs = [p[0] - p[1] for p in pts]
    u, v = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
    return [(u + v) / 2, (u - v) / 2], max(max(us) - min(us), max(vs) - min(vs)) / 2


def do_type(t, T):
    ln = {int(h['inst'].split('g_ln[')[1].split(']')[0]): h for h in T['hard_cores'] if '.g_ln[' in h['inst']}
    assert sorted(ln) == list(range(16)), t
    assert len({(h['module'], tuple(h['outline_um'])) for h in ln.values()}) == 1, t + ': lane cores differ'
    es = [dict(e) for e in T.get('internal_stations', [])]
    hv = [(e, RX.match(e.get('conn', ''))) for e in es]
    hv = [(e, m) for e, m in hv if m]
    if not hv:
        return None, dict(skipped='no vn<->lane entries')
    # stored direction: lane end = the endpoint nearer the lane box
    for e, m in hv:
        h = ln[int(m.group(2))]
        e['_sw'] = box_d(e['from_um'], h) < box_d(e['to_um'], h)
    vp_ = lambda e: e['to_um'] if e['_sw'] else e['from_um']
    lp_ = lambda e: e['from_um'] if e['_sw'] else e['to_um']
    # (1) permutation on the CURRENT slots (hq_d pin per lane when present, else lane centre)
    pin = {}
    for e, m in hv:
        if '.hq_d|' in e['conn']:
            pin.setdefault(int(m.group(2)), tuple(lp_(e)))
    slots = [pin.get(l, ctr(ln[l])) for l in range(16)]
    vn = sorted({tuple(vp_(e)) for e, m in hv})
    perm, s0, s1 = regroup(slots, vn)
    snap = {l: (list(h['origin_um']), h.get('orient', 'R0')) for l, h in ln.items()}
    old = {l: dict(origin_um=list(h['origin_um']), outline_um=list(h['outline_um']), orient=h.get('orient', 'R0')) for l, h in ln.items()}
    moved = 0
    for l, s in enumerate(perm):
        if s != l:
            ln[l]['origin_um'], ln[l]['orient'] = list(snap[s][0]), snap[s][1]; moved += 1
    # (2) templates per vn port (module-local lane pin), add missing port x lane entries
    tpl, have = {}, {e['conn'] for e, m in hv}
    for e, m in hv:
        k = e['conn'].split('|')[0]
        tpl.setdefault(k, (e, m, loc(lp_(e), old[int(m.group(2))])))
    spread = 0.0
    for e, m in hv:
        k = e['conn'].split('|')[0]
        spread = max(spread, M(loc(lp_(e), old[int(m.group(2))]), tpl[k][2]))
    added = 0
    for k, (e0, m0, lc) in sorted(tpl.items()):
        for l in range(16):
            c = '%s|core:u_lf.u_vp.g_ln[%d].u_l' % (k, l)
            if c in have:
                continue
            e = {x: v for x, v in e0.items()}
            e['conn'] = c
            for f in ('capture', 'launch'):
                if 'g_ln[' in str(e0.get(f, '')):
                    e[f] = re.sub(r'g_ln\[\d+\]', 'g_ln[%d]' % l, e0[f])
            e['note'] = 'S81-LEAF-CYC quad2: vn->lane bundle entry (all 16 lanes of the port are stationed)'
            e['_lc'] = lc; es.append(e); hv.append((e, RX.match(c))); added += 1
    grp = {}
    for e, m in hv:
        l = int(m.group(2))
        e.pop('_lc', None)
        np_ = near(vp_(e), ln[l])                          # lane l in its new slot (plan core-end convention)
        if e['_sw']:
            e['from_um'] = np_
        else:
            e['to_um'] = np_
        grp.setdefault((l // 4, 'ho' if m.group(1) == 'hw_' else 'hi'), []).append(e)
    worst, over = [0, 0, 0], []
    for (g, c), ge in sorted(grp.items()):
        F = [vp_(e) for e in ge]; L = [lp_(e) for e in ge]
        cost = lambda q: max(center(F + [q])[1], max(M(q, x) for x in L))
        xs = [p[0] for p in F + L]; ys = [p[1] for p in F + L]
        cand = [[min(xs) + 10 * i, min(ys) + 10 * j] for i in range(int((max(xs) - min(xs)) / 10) + 2)
                for j in range(int((max(ys) - min(ys)) / 10) + 2)]
        Q0 = [sum(p[0] for p in L) / len(L), sum(p[1] for p in L) / len(L)]
        cq = min(cost(q) for q in cand)
        q = min((q for q in cand if cost(q) <= max(cq, QMAX)), key=lambda q: (max(M(q, x) for x in L), M(q, Q0)))
        q = [round(q[0], 3), round(q[1], 3)]
        mm = [round(x, 3) for x in center(F + [q])[0]]
        for e in ge:
            e['regs_um'] = [q, mm] if e['_sw'] else [mm, q]    # stored from_um -> to_um order
            e['note'] = (e.get('note', '') + ' | S81-LEAF-CYC quad2 (CS_H%s_D 2 GS 2 G 4, 63676d718d59): quad %d stages '
                         'm (vn pins/quad minimax) + q (quad), +2 cycles declared' % ('I' if c == 'hi' else 'O', g)).lstrip(' |')
            pts = [vp_(e), mm, q, lp_(e)]
            hs = [M(a, b) for a, b in zip(pts, pts[1:])]
            worst = [max(worst[i], hs[i]) for i in range(3)]
            if max(hs) > LIM + 1e-6:
                over.append(dict(quad=g, cls=c, conn=e['conn'], hop=round(max(hs), 1)))
    for e in es:
        e.pop('_sw', None)
    T['internal_stations'] = es
    return over, dict(perm=perm, lanes_moved=moved, entries_added=added, h_entries=len(hv), local_pin_spread_um=round(spread, 3),
                      quad_reach_before=dict(last=round(s0[1]), far=round(s0[2])), quad_reach_after=dict(last=round(s1[1]), far=round(s1[2])),
                      worst_hop_um=dict(vn_m=round(worst[0], 1), m_q=round(worst[1], 1), q_lane=round(worst[2], 1)), over=over)


def main():
    inp, out, rep = sys.argv[1:4]
    D = json.load(open(inp)); P = D['partition_types']
    kv = sorted({p['type'] for p in D['partitions'] if p['name'].startswith('s_0S_L') and p['type'].startswith('ot_s81sl_leaf__')})
    shared = sorted({p['type'] for p in D['partitions'] if p['type'] in kv and not p['name'].startswith('s_0S_L')})
    if shared:
        raise SystemExit('KV slice leaf types also placed outside s_0S: %s' % shared)
    sys.path.insert(0, str(Path('tools/die_plan').resolve()))
    try:
        import collector_reach as CR
        cr0 = [r for r in CR.find_all(D) if r['type'].startswith('ot_s81sl_leaf__')]
    except ImportError:
        CR, cr0 = None, 'collector_reach.py not in this repo (claude/seam-hop-1@ce278419378a)'
    R, bad = dict(stage='S81-LEAF-CYC quad2', rtl='claude/s81-leaf-cyc2-1111@63676d718d59', kv_excluded=kv, types={}), []
    for t in sorted(P):
        if not t.startswith('ot_s81sl_leaf__') or t in kv:
            continue
        over, r = do_type(t, P[t])
        R['types'][t] = r
        bad += [(t, o) for o in (over or [])]
    R['n_types'] = sum(1 for r in R['types'].values() if 'perm' in r)
    R['collector_reach_leaf_before'] = cr0
    R['collector_reach_leaf_after'] = [r for r in CR.find_all(D) if r['type'].startswith('ot_s81sl_leaf__')] if CR else cr0
    R['hops_over_405'] = len(bad)
    json.dump(R, open(rep, 'w'), indent=1)
    if bad:
        print('FAIL: %d hops > 405 um, e.g. %s' % (len(bad), bad[:3])); sys.exit(2)
    json.dump(D, open(out, 'w'), indent=1)
    w = max((r['worst_hop_um'][k] for r in R['types'].values() if 'perm' in r for k in r['worst_hop_um']), default=0)
    print('quad2: %d types, KV excluded %s, worst hop %.1f um, lanes moved %d, entries added %d, collector leaf findings %s -> %s'
          % (R['n_types'], kv, w, sum(r.get('lanes_moved', 0) for r in R['types'].values()),
             sum(r.get('entries_added', 0) for r in R['types'].values()),
             len(cr0) if isinstance(cr0, list) else cr0, len(R['collector_reach_leaf_after']) if CR else '-'))


if __name__ == '__main__':
    main()
