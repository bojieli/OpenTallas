#!/usr/bin/env python3
"""Die-level link pin re-assignment search on an exported S81 construction plan (screen only, never a closure).

Generalises hub_face_repin_search.py from the 11 hub parents to every die-level element whose pins the die
pin tool owns (default: every kind not in FIXED_KINDS, so new kinds of a later
contract, e.g. MIX4/collective children/VM service slots, are included and listed).  Re-packing is done
per MASTER in the master frame: a replicated master (e.g. dsfd_cfifo x128, dsfd_lkck_SE x3) gets ONE pin
plan, so the desired translation of a port is the bit-weighted mean over every instance and every edge,
converted to the master frame through each instance's orientation.  Pins of hard IP / field / station kinds
(phy, link, pqrom, bf/bfcol/seq/cfg/q/qbank/node, rly/stn/sstn/hstn/rstg) never move: they are partners only.

Per face: port slices (overlapping slices merged into rigid groups), anchored pins (no data edge: clock,
reset, exempt, unused) with a very large weight, abacus legalisation inside the face extent, optional
slice-order permutation (--reorder).  ALL edges incident to any moved master are re-measured before/after
at exact LEF pins: bit-um, max, bits > 500 um, bits > 215 um (hub-station reach CC_REACH), pin_align
verdict; worsened edges are listed.  Output: per-(master, port) master-frame translation table + metrics.
"""
import argparse, collections, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import group_placement_opt as G
from hub_face_repin_search import abacus, edge_stats, along, pack_face
PA = G.PA
# partner-only kinds: hard IP, ROM macros, immutable field children, stations/relays (hop finalization owns them)
FIXED_KINDS = {'phy', 'link', 'pqrom', 'bf', 'bfcol', 'seq', 'cfg', 'q', 'qbank', 'node', 'rly', 'stn', 'sstn', 'hstn', 'rstg'}
ANCHOR_W = 1e9


def port_pins(m, inst, port, bits):
    names = m.plan.get('pins', {}).get(inst.name + '|' + port)
    if names is not None:
        return names, True                       # per-instance override: master-level re-pin not allowed
    part = PA._PSL.match(port)
    base = part.group(1) if part else port
    lo = int(part.group(2)) if part else 0
    alias = m.plan.get('port_aliases', {}).get(inst.master, {}).get(base)
    return (alias[lo:lo + bits] if alias is not None else PA.default_names(inst.name, port, bits)), False


def sign(inst, face_local):
    """die-frame direction of a +1 master-frame translation along a face"""
    o = PA.ORI.get(inst.orient, 'N')
    if face_local in ('E', 'W'):
        return -1 if o in ('S', 'FS') else 1
    return -1 if o in ('S', 'FN') else 1


def run(plan_path, lef_path, out_path, iters, kinds, reorder, only_masters=None):
    plan = json.loads(G.read(plan_path))
    kind = {r[0]: r[7] for r in plan['insts'] if len(r) > 7}
    if kinds is None:                               # default: every kind not partner-only (new kinds included)
        kinds = {k for k in kind.values() if k not in FIXED_KINDS}
    movable = {n for n, k in kind.items() if k in kinds}
    keep = [b for b in plan['buses'] if any(n in movable for n, _ in b[3])]
    sub = dict(plan); sub['buses'] = keep
    m = G.Model(sub, [G.read(lef_path)], plan['die'])
    masters = collections.defaultdict(list)
    for n in movable:
        masters[m.insts[n].master].append(n)
    if only_masters:
        masters = {k: v for k, v in masters.items() if k in only_masters}
    report = dict(schema='opentallas.s81.die_link_repin_search.v1',
                  scope='SCREEN_ONLY_DIE_LINK_PIN_REASSIGNMENT_NOT_ADOPTED_NOT_NATIVE',
                  source_sha256={str(p.name): hashlib.sha256(p.read_bytes()).hexdigest() for p in (plan_path, lef_path)},
                  tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  plan_scope=plan.get('scope'), plan_variant_rev=plan.get('variant', {}).get('rev'),
                  rules=dict(kinds=sorted(kinds), fixed_kinds=sorted(FIXED_KINDS), kind_counts=dict(sorted(__import__('collections').Counter(kind.values()).items())), reorder=reorder, master_level=True, partner_side_fixed=True,
                             hub_station_reach_um=215.0, geometry_bound_um=500.0,
                             anchored='pins without a data edge (clock/reset/exempt/unused) do not move'),
                  missing_edges=m.missing, masters={})
    # (inst, port) -> [(edge, end)]
    use = collections.defaultdict(list)
    for i, e in enumerate(m.edges):
        for k, (n, p) in enumerate(e['ends']):
            if n in movable:
                use[(n, p)].append((i, k))
    base_pts = [[list(map(tuple, side)) for side in e['points']] for e in m.edges]
    pts = [[list(side) for side in s] for s in base_pts]
    shift = {}                      # (master, port) -> master-frame translation
    skipped = collections.Counter()
    for _ in range(iters):
        for mst in sorted(masters):
            insts = [m.insts[n] for n in masters[mst]]
            W, H_, pp = m.pins[mst]
            ports = {}              # port -> dict(face, coords(local), pins, w, num)
            for it in insts:
                for (n, p), refs in use.items():
                    if n != it.name:
                        continue
                    i, k = refs[0]
                    bits = m.edges[i]['bits']
                    names, override = port_pins(m, it, p, bits)
                    if override:
                        skipped['per_instance_pin_override'] += 1; continue
                    loc = [pp[x] for x in names]
                    f = loc[0][2]
                    if f is None or any(s[2] != f for s in loc):
                        skipped['area_or_multiface_port'] += 1; continue
                    ax = along(f); sg = sign(it, f)
                    r = ports.setdefault(p, dict(face=f, lo=min(s[ax] for s in loc) - 0.048,
                                                 hi=max(s[ax] for s in loc) + 0.048, names=set(names), num=0.0, den=0.0))
                    for (ii, kk) in refs:
                        own = pts[ii][kk]; oth = pts[ii][1 - kk]
                        r['num'] += sg * sum(o[ax] - s[ax] for s, o in zip(own, oth)); r['den'] += len(own)
            used = set().union(*[r['names'] for r in ports.values()]) if ports else set()
            faces = collections.defaultdict(list)
            for p, r in ports.items():
                cur = shift.get((mst, p), 0.0)
                faces[r['face']].append(dict(port=p, lo0=r['lo'], hi0=r['hi'], w=r['den'], t=cur + r['num'] / r['den']))
            for pname, (px, py, f, lay) in pp.items():
                if f is None or pname in used:
                    continue
                c = (px, py)[along(f)]
                faces[f].append(dict(port=None, lo0=c - 0.048, hi0=c + 0.048, w=ANCHOR_W, t=0.0))
            for f, sl in faces.items():
                if not any(s['port'] for s in sl):
                    continue
                flo, fhi = 0.0, (W, H_)[along(f)]
                sl.sort(key=lambda s: s['lo0'])
                groups = []
                for s in sl:
                    if groups and s['lo0'] < groups[-1]['hi0'] - 1e-9:
                        g = groups[-1]; g['m'].append(s); g['hi0'] = max(g['hi0'], s['hi0'])
                    else:
                        groups.append(dict(m=[s], lo0=s['lo0'], hi0=s['hi0']))
                rows = []
                for g in groups:
                    anchored = any(s['port'] is None for s in g['m'])
                    w = sum(s['w'] for s in g['m'])
                    t = 0.0 if anchored else sum(s['w'] * s['t'] for s in g['m']) / w
                    rows.append(dict(width=g['hi0'] - g['lo0'], desired=g['lo0'] + t, w=ANCHOR_W if anchored else w,
                                     anchored=anchored))
                new = pack_face(rows, flo, fhi, reorder)    # anchors immovable; reorder within anchor intervals
                for g, x in zip(groups, new):
                    for s in g['m']:
                        if s['port'] is not None:
                            shift[(mst, s['port'])] = x - g['lo0']
            for it in insts:
                for (n, p), refs in use.items():
                    if n != it.name or (mst, p) not in shift:
                        continue
                    for (i, k) in refs:
                        side = base_pts[i][k]; ax = along(side[0][2]); d = sign(it, ports[p]['face']) * shift[(mst, p)]
                        pts[i][k] = [tuple(v + (d if j == ax else 0.0) for j, v in enumerate(s[:2])) + tuple(s[2:]) for s in side]
    moved = {n for ns in masters.values() for n in ns}
    per = collections.defaultdict(lambda: dict(instances=0, edges=0, bits=0, before=collections.Counter(),
                                               after=collections.Counter(), fail_before=0, fail_after=0,
                                               worst_before=0.0, worst_after=0.0))
    rows = []
    for i, e in enumerate(m.edges):
        if not any(n in moved for n, _ in e['ends']):
            continue
        b = edge_stats(e, base_pts[i]); a = edge_stats(e, pts[i])
        for mst in {m.insts[n].master for n, _ in e['ends'] if n in moved}:
            r = per[mst]; r['edges'] += 1; r['bits'] += e['bits']
            for k in ('sum_bit_um', 'over500', 'over215'):
                r['before'][k] += b[k]; r['after'][k] += a[k]
            r['fail_before'] += b['verdict'] == 'FAIL'; r['fail_after'] += a['verdict'] == 'FAIL'
            r['worst_before'] = max(r['worst_before'], b['max_um']); r['worst_after'] = max(r['worst_after'], a['max_um'])
        rows.append(dict(bus=e['bus'], cls=e['cls'], ends=e['ends'], kinds=[kind.get(n) for n, _ in e['ends']], bits=e['bits'],
                         before={k: (round(v, 3) if isinstance(v, float) else v) for k, v in b.items() if k != 'why'},
                         after={k: (round(v, 3) if isinstance(v, float) else v) for k, v in a.items() if k != 'why'},
                         why_after=a['why']))
    tb = collections.Counter(); ta = collections.Counter()
    for r in rows:
        for k in ('sum_bit_um', 'over500', 'over215'):
            tb[k] += r['before'][k] * 1.0; ta[k] += r['after'][k] * 1.0
        tb['fail'] += r['before']['verdict'] == 'FAIL'; ta['fail'] += r['after']['verdict'] == 'FAIL'
        tb['max'] = max(tb['max'], r['before']['max_um']); ta['max'] = max(ta['max'], r['after']['max_um'])
    for mst in masters:
        per[mst]['instances'] = len(masters[mst])
    report['skipped_ports'] = dict(skipped)
    report['totals'] = dict(edges=len(rows), before=dict(tb), after=dict(ta))
    report['masters'] = {k: dict(instances=r['instances'], edges=r['edges'], bits=r['bits'], before=dict(r['before']),
                                 after=dict(r['after']), fail_before=r['fail_before'], fail_after=r['fail_after'],
                                 worst_before=round(r['worst_before'], 3), worst_after=round(r['worst_after'], 3))
                         for k, r in sorted(per.items())}
    report['worsened_edges'] = [dict(bus=r['bus'], bits=r['bits'], ends=r['ends'], max_before=r['before']['max_um'],
                                     max_after=r['after']['max_um'], verdict=[r['before']['verdict'], r['after']['verdict']])
                                for r in rows if r['after']['max_um'] > r['before']['max_um'] + 1e-3
                                or r['after']['over500'] > r['before']['over500'] or r['after']['over215'] > r['before']['over215']
                                or (r['after']['verdict'] == 'FAIL' and r['before']['verdict'] != 'FAIL')]
    report['port_shifts_master_frame_um'] = sorted([dict(master=k, port=p, shift_um=round(d, 3)) for (k, p), d in shift.items()
                                                    if abs(d) > 0.0005], key=lambda r: -abs(r['shift_um']))
    rows.sort(key=lambda r: -(r['before']['sum_bit_um'] - r['after']['sum_bit_um']))
    report['edges'] = rows
    out_path.write_text(json.dumps(report, indent=1) + '\n')
    print('FINAL', json.dumps(report['totals']))
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--lef', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--iters', type=int, default=2)
    ap.add_argument('--kinds', default='', help='comma list of movable kinds (default: all kinds except FIXED_KINDS)')
    ap.add_argument('--masters', default='', help='comma list of masters to re-pack (default all of --kinds)')
    ap.add_argument('--reorder', action='store_true')
    a = ap.parse_args()
    run(a.plan, a.lef, a.out, a.iters, set(filter(None, a.kinds.split(','))) or None, a.reorder, set(filter(None, a.masters.split(','))) or None)
