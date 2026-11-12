"""CLAND-WSTART-1 respace (COORD 11-11): writer START relay stages on a hard-core-free Manhattan route, same depth.

For each listed type, every landing_writer_start branch whose chain (as landing_place places it, origin-anchored) has a
hop > LIMIT um gets new stage sites: the shortest Manhattan route origin -> cland_fstart_out_<bus> face pin that stays
MARGIN um clear of every hard core, cut into depth + 1 equal hops.  A site inside a landing_contract band rect slides
along the route to the nearest clear point.  Each stage keeps the raw_reset of the same index (the start planner's
choice; re-pick with the planner if a stage moved far from its relay).  Same depth: 0 data cycles, no boot change.
Every new site is checked: clear of cores and bands, landing_place relocates none, every hop <= LIMIT.

usage: wstart_respace.py report BASE_PLAN TYPE...            -> one row per respaced branch
       wstart_respace.py delta  BASE_PLAN OUT_DELTA TYPE...  -> {type: {bus: [stage, ...]}} JSON
       wstart_respace.py apply  BASE_PLAN DELTA OUT_PLAN     -> BASE_PLAN with those branches' stages replaced"""
import heapq
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_place as LP

LIMIT = 405.0
MARGIN = 4.32 + 2.16 + 0.5      # landing_place core margin + half stage window + slack
EDGE = 6.5
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def _cores(t):
    return [(x0 - MARGIN, y0 - MARGIN, x1 + MARGIN, y1 + MARGIN) for x0, y0, x1, y1 in LP._hard_core_rects(t)]


def _bands(t):
    return [tuple(b['rect_um']) for b in ((t['clock'].get('landing_contract') or {}).get('bands') or {}).values()]


def _inside(p, rects, grow=0.0):
    return any(r[0] - grow < p[0] < r[2] + grow and r[1] - grow < p[1] < r[3] + grow for r in rects)


def _seg_ok(p, q, cores):
    n = max(2, int(md(p, q) / 4))
    return not any(_inside((p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n), cores) for i in range(n + 1))


def _exit(t, p, cores):
    """p itself, or the nearest point straight out of the inflated cores (an origin on a core edge)."""
    if not _inside(p, cores):
        return [tuple(p)]
    W, H = t['outline_um']
    cands = []
    for c in cores:
        if _inside(p, [c]):
            for q in ((c[0] - 0.05, p[1]), (c[2] + 0.05, p[1]), (p[0], c[1] - 0.05), (p[0], c[3] + 0.05)):
                if EDGE <= q[0] <= W - EDGE and EDGE <= q[1] <= H - EDGE and not _inside(q, cores):
                    cands.append((md(p, q), q))
    if not cands:
        raise ValueError(f'no exit from the core/band margin at {p}')
    return [tuple(p), min(cands)[1]]


def _blocks(t):
    """Routing obstacles: hard cores (MARGIN) and landing_contract band rects (half stage window + 1 um), so equal-hop
    sites on the route are clear of both."""
    g = 2.16 + 1.0
    return _cores(t) + [(x0 - g, y0 - g, x1 + g, y1 + g) for x0, y0, x1, y1 in _bands(t)]


def route(t, a, b, with_bands=True):
    cores = _blocks(t) if with_bands else _cores(t)
    W, H = t['outline_um']
    ha, hb = _exit(t, a, cores), _exit(t, b, cores)[::-1]
    s, e = ha[-1], hb[0]
    # grid lines 0.05 um OUTSIDE every obstacle, so sites rounded to 0.01 um stay clear
    xs = sorted({s[0], e[0], EDGE, W - EDGE} | {v for c in cores for v in (c[0] - 0.05, c[2] + 0.05)})
    ys = sorted({s[1], e[1], EDGE, H - EDGE} | {v for c in cores for v in (c[1] - 0.05, c[3] + 0.05)})
    nodes = {(x, y) for x in xs for y in ys if EDGE <= x <= W - EDGE and EDGE <= y <= H - EDGE
             and not _inside((x, y), cores)} | {s, e}
    lines = {}
    for n in nodes:
        lines.setdefault(('r', n[1]), []).append(n)
        lines.setdefault(('c', n[0]), []).append(n)
    adj = {n: [] for n in nodes}
    for line in lines.values():
        line.sort()
        for p, q in zip(line, line[1:]):
            if _seg_ok(p, q, cores):
                adj[p].append(q)
                adj[q].append(p)
    dist, prev, pq = {s: 0.0}, {}, [(0.0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == e:
            break
        if d > dist[u]:
            continue
        for v in adj[u]:
            nd = d + md(u, v)
            if nd < dist.get(v, 1e18) - 1e-9:
                dist[v], prev[v] = nd, u
                heapq.heappush(pq, (nd, v))
    if e != s and e not in prev:
        return None
    path = [e]
    while path[-1] != s:
        path.append(prev[path[-1]])
    return ha[:-1] + path[::-1] + hb[1:]


def _at(path, s):
    for p, q in zip(path, path[1:]):
        d = md(p, q)
        if s <= d + 1e-9:
            f = s / d if d else 0.0
            return (round(p[0] + (q[0] - p[0]) * f, 2), round(p[1] + (q[1] - p[1]) * f, 2))
        s -= d
    return tuple(path[-1])


def respace(t, origin, face, n, with_bands=True):
    """with_bands: the wire also avoids band rects (sites then fall clear by construction); False: the wire may cross a
    band (only sites must not sit in one) and a site that lands in a band slides along the route."""
    try:
        path = route(t, origin, face, with_bands)
    except ValueError:
        return None
    if path is None:
        return None
    L = sum(md(p, q) for p, q in zip(path, path[1:]))
    cores, bands = _cores(t), _bands(t)
    sites = []
    for k in range(1, n + 1):
        s0 = L * k / (n + 1)
        for off in sorted({0.0} | {sg * i * 2.16 for i in range(1, 60) for sg in (1, -1)}, key=abs):
            q = _at(path, min(max(s0 + off, 0.0), L))
            if not _inside(q, cores) and not _inside(q, bands, grow=2.16 + 1.0):
                sites.append(q)
                break
        else:
            return None
    return L, sites


def plan_rows(P, types):
    rows = []
    for tn in types:
        t = P['partition_types'][tn]
        o = LP._start_origin_xy(t)
        pins = {p['name']: tuple(p['xy_um']) for p in t['clock']['landing_contract']['pins']}
        for bus, br in sorted(t['clock']['landing_writer_start']['branches'].items()):
            face = pins.get('cland_fstart_out_' + bus)
            cs = [LP._centre(r) for r in LP._chain_clear_of_hard_cores(t, o, br['stages'])]
            old = [md(o, cs[0])] + [md(p, q) for p, q in zip(cs, cs[1:])] + ([md(cs[-1], face)] if face else [])
            if o is None or face is None or max(old) <= LIMIT:
                continue
            n = len(br['stages'])
            cands = []
            for wb in (False, True):
                got = respace(t, o, face, n, wb)
                if got is None:
                    continue
                L, sites = got
                new = [md(o, sites[0])] + [md(p, q) for p, q in zip(sites, sites[1:])] + [md(sites[-1], face)]
                placed = [LP._centre(r) for r in LP._chain_clear_of_hard_cores(t, o, [{'xy_um': list(s)} for s in sites])]
                moved = sum(md(a, b) > 0.01 for a, b in zip(sites, placed))
                ok = max(new) <= LIMIT and moved == 0 and not any(_inside(s, _bands(t), grow=2.16) for s in sites)
                cands.append((not ok, max(new), dict(
                    type=tn, bus=bus, depth=n, old_max_hop=round(max(old)), new_max_hop=round(max(new)),
                    route_um=round(L), relocated=moved, ok=ok, wire_avoids_bands=wb,
                    stages=[dict(xy_um=list(s), raw_reset=st.get('raw_reset')) for s, st in zip(sites, br['stages'])])))
            if not cands:
                rows.append(dict(type=tn, bus=bus, depth=n, old_max_hop=round(max(old)),
                                 error='no core-free route or no band-clear site'))
                continue
            rows.append(min(cands, key=lambda c: c[:2])[2])
    return rows


def main(argv):
    mode = argv[0]
    if mode == 'apply':
        P, D = json.load(open(argv[1])), json.load(open(argv[2]))
        for tn, buses in D['types'].items():
            br = P['partition_types'][tn]['clock']['landing_writer_start']['branches']
            for bus, stages in buses.items():
                if len(stages) != len(br[bus]['stages']):
                    raise SystemExit(f'{tn}.{bus}: depth changed ({len(br[bus]["stages"])} -> {len(stages)})')
                br[bus]['stages'] = stages
        Path(argv[3]).write_text(json.dumps(P, indent=1) + '\n')
        return 0
    P = json.load(open(argv[1]))
    types = argv[3:] if mode == 'delta' else argv[2:]
    rows = plan_rows(P, types)
    bad = [r for r in rows if not r.get('ok')]
    for r in rows:
        print('|'.join(str(r.get(k)) for k in ('type', 'bus', 'depth', 'old_max_hop', 'new_max_hop', 'relocated', 'ok'))
              + '|' + ' '.join(f"[{s['xy_um'][0]},{s['xy_um'][1]}]" for s in r.get('stages', [])) + ('|' + r['error'] if 'error' in r else ''))
    if mode == 'delta':
        out = dict(schema='opentallas.wstart_respace_delta.v1', limit_um=LIMIT, margin_um=MARGIN,
                   note='same depth (0 data cycles, no boot change); raw_reset kept by stage index', types={})
        for r in rows:
            if r.get('ok'):
                out['types'].setdefault(r['type'], {})[r['bus']] = r['stages']
        out['rows'] = [{k: v for k, v in r.items() if k != 'stages'} for r in rows]
        Path(argv[2]).write_text(json.dumps(out, indent=1) + '\n')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
