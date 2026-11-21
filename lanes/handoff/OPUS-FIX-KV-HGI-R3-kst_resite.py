#!/usr/bin/env python3
"""OPUS-FIX-KV-HGI-R3 (lever 8, FAM-KV-HUB-R2 proposal): move the head kt station registers out of the head cores.
For every kv3_hg* type: each internal_stations row conn 'core:u_headN_eK.kp_o..|core:u_headN_e0.u_kt__kp_in..' whose regs_um
lie inside a hard core is re-sited on its from->to line (x interpolated; if a row of the line is blocked, the nearest free x within --lateral um) into the free street intervals of that
column (cores + MARGIN um kept clear), station count unchanged (uniform kt depth, 0 added cycles), positions chosen to
minimise the max hop from_um -> regs -> to_um (must be <= HOP_MAX).  relay_sites entries of the same type at an old reg
coordinate move with it (exact coordinate map; refused if an old coordinate is shared by two rows).
usage: kst_resite.py PLAN_IN PLAN_OUT REPORT [--margin 9.72] [--hop-max 405] [--types REGEX]"""
import argparse, json, re, sys, copy
ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('report')
ap.add_argument('--margin', type=float, default=9.72); ap.add_argument('--hop-max', type=float, default=405.0)
ap.add_argument('--types', default=r'^kv3_hg'); ap.add_argument('--step', type=float, default=1.08); ap.add_argument('--lateral', type=float, default=200.0)
a = ap.parse_args()
d = json.load(open(a.plan)); rep = dict(margin=a.margin, hop_max=a.hop_max, types={}, skipped=[])
CONN = re.compile(r'^core:u_head\d+_e\d+\.kp_o.*\|core:u_head\d+_e0\.u_kt__kp_in')
def boxes(t):
    return [(h['inst'], h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + h['outline_um'][0], h['origin_um'][1] + h['outline_um'][1])
            for h in t.get('hard_cores', [])]
def inside(p, bx, m=0.0):
    return any(x0 - m < p[0] < x1 + m and y0 - m < p[1] < y1 + m for _, x0, y0, x1, y1 in bx)
for tn in sorted(d['partition_types']):
    if not re.search(a.types, tn): continue
    t = d['partition_types'][tn]; bx = boxes(t); moved = []; cmap = {}
    for e in t.get('internal_stations', []):
        if not CONN.match(e.get('conn', '')) or not e.get('regs_um'): continue
        regs = e['regs_um']
        if not any(inside(r, bx) for r in regs): continue
        f, to = e['from_um'], e['to_um']; n = len(regs)
        if n not in (1, 2):
            rep['skipped'].append(dict(type=tn, conn=e['conn'], why='%d stations: not handled' % n)); continue
        lo, hi = sorted((f[1], to[1]))
        def xline(y):
            return f[0] + (to[0] - f[0]) * (y - f[1]) / (to[1] - f[1]) if to[1] != f[1] else f[0]
        cand = []; y = lo + a.step
        while y < hi:
            x0 = xline(y); pt = None
            if not inside((x0, y), bx, a.margin): pt = (x0, y)
            else:   # lateral: nearest free x on this row within LATERAL um (street beside a blocking core)
                for dx in [i * a.step for i in range(1, int(a.lateral / a.step))]:
                    for xx in (x0 - dx, x0 + dx):
                        if 4.32 + a.margin < xx and not inside((xx, y), bx, a.margin): pt = (xx, y); break
                    if pt: break
            if pt: cand.append((round(pt[0], 3), round(pt[1], 3)))
            y += a.step
        on_line = [c for c in cand if abs(c[0] - round(xline(c[1]), 3)) < 1e-6]
        def solve(cand):
            cand = sorted(cand, key=lambda p: -p[1] if f[1] > to[1] else p[1]); best = None
            if n == 1:
                for c in cand:
                    h = max(L(f, c), L(c, to))
                    if best is None or h < best[0]: best = (h, [c])
            else:
                for i, c0 in enumerate(cand):
                    h0_ = L(f, c0)
                    if best is not None and h0_ >= best[0]: continue
                    for c1 in cand[i + 1:]:
                        h = max(h0_, L(c0, c1), L(c1, to))
                        if best is None or h < best[0]: best = (h, [c0, c1])
            return best
        L = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
        best = solve(on_line)          # stay on the row's own line when it fits; a lateral jog only when it must
        if best is None or best[0] > a.hop_max: best = solve(cand)
        if best is None or best[0] > a.hop_max:
            rep['skipped'].append(dict(type=tn, conn=e['conn'], why='no street sites within hop %.0f' % a.hop_max, best=best and best[0])); continue
        hp = lambda pts: max(L(p, q) for p, q in zip([f] + pts, pts + [to]))
        old = [list(r) for r in regs]; new = [list(c) for c in best[1]]
        h0 = hp([tuple(r) for r in regs])
        for o, nw in zip(old, new):
            k = (round(o[0], 4), round(o[1], 4))
            if k in cmap and cmap[k] != nw: sys.exit('REFUSE %s: old coordinate %s shared by two rows' % (tn, k))
            cmap[k] = nw
        e['regs_um'] = new
        e['note'] = (e.get('note', '') + ' | OPUS-FIX-KV-HGI-R3 lever 8: kt station regs moved out of the head cores into the column streets '
                     '(margin %.2f um), stations %d unchanged, max hop %.1f -> %.1f um' % (a.margin, n, h0, best[0])).strip(' |')
        moved.append(dict(conn=e['conn'], old=old, new=new, hop=[round(h0, 1), round(best[0], 1)]))
    rs = t.get('relay_sites') or {}; nrs = 0
    for k, v in rs.items():
        kk = (round(v[0], 4), round(v[1], 4))
        if kk in cmap: rs[k] = list(cmap[kk]); nrs += 1
    left = sum(1 for v in rs.values() if inside(v, bx))
    rows_left = sum(1 for e in t.get('internal_stations', []) if CONN.match(e.get('conn', '')) and any(inside(r, bx) for r in e.get('regs_um') or []))
    if moved or left:
        rep['types'][tn] = dict(rows=len(moved), relay_sites_moved=nrs, relay_sites_inside_left=left, kst_rows_inside_left=rows_left,
                                max_hop=max([m['hop'][1] for m in moved] or [0]), moved=moved)
json.dump(d, open(a.out, 'w'), indent=1); open(a.out, 'a').write('\n')
json.dump(rep, open(a.report, 'w'), indent=1)
for tn, r in rep['types'].items():
    print('KST_RESITE %s rows %d relay_sites %d inside_left %d rows_left %d max_hop %.1f' % (tn, r['rows'], r['relay_sites_moved'], r['relay_sites_inside_left'], r['kst_rows_inside_left'], r['max_hop']))
print('KST_RESITE skipped', len(rep['skipped']), json.dumps(rep['skipped'])[:600])
