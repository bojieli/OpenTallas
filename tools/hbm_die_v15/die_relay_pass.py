#!/usr/bin/env python3
"""Die relay pass (H-DIE 2026-10-16, coordinator: no unregistered die net longer than one-cycle reach).

    die_relay_pass.py CASE_DIR [--reach 450] [--contract C.json] [--out FILE] [--nets-out FILE]

Reads a die case exactly as case_reach.py does (manifest placement, view LEF pin rectangles, die.v nets, LEF
directions, typed clocks excluded) and plans fixed-latency registered relay stations on every driver -> sink hop longer
than REACH:
  * point-to-point net: stations every REACH along the pin-to-pin Manhattan route, stages = ceil(L / REACH) - 1;
  * multicast net: a registered distribution tree -- rectilinear Prim tree from the driver over the sinks, stations at
    every REACH of tree distance from the driver (shared by every sink below), and pad stages at the near sinks so that
    every sink sees the SAME age (equal-age calendar; the compiler schedule takes one fixed latency per net).
Existing hbfd_rly_* instances are ordinary placed nodes, so a net already relayed is only charged its remaining long
hops.  Nets driven from die ports (reset/por, refclk) are listed separately (reset forest, not data relays).
Output per family (driver master.port -> sink master.port): nets, max hop, added stages (max), station flops, pad flops.
GEOMETRY ONLY (block-pin Manhattan, no routed detour); station area and placement legality are not checked here.
"""
import argparse, collections, json, math, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_reach as CR  # noqa: E402


def load_case(c, contract):
    clock_pins = CR.typed_clock_pins(contract) if contract else set()
    man = json.loads((c / 'manifest.json').read_text())
    L = {}
    for f in (c / 'views').glob('*.lef'):
        L.update(CR.lef(f))
    pl = {n: dict(v, orient=v.get('orient', v.get('o')), master=v.get('master', v.get('m')))
          for n, v in man['placement'].items()}
    txt = (c / 'die.v').read_text()
    top_inputs = set()
    for hi, lo, name in re.findall(r'\binput\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s*)?(\w+)', txt):
        top_inputs.update([f'{name}[{k}]' for k in range(int(lo), int(hi) + 1)] if hi else [name])
    nets, directions = collections.defaultdict(list), {}
    for m in re.finditer(r'^\s+(\w+) (\w+) \(\n(.*?)\n\s+\);', txt, re.M | re.S):
        mas, inst = m.group(1), m.group(2)
        if inst not in pl or mas not in L:
            continue
        v = pl[inst]; lv = L[mas]
        for pm in re.finditer(r'\.(\w+)\((.*?)\)(?:,|$)', m.group(3), re.S):
            p, e = pm.group(1), pm.group(2).strip()
            items = []
            if e.startswith('{'):
                parts = [s.strip() for s in e[1:-1].split(',')]
                items = [(s, f'{p}[{len(parts) - 1 - i}]') for i, s in enumerate(parts)]
            elif e:
                items = [(e, p)]
            for s, pn in items:
                if s.startswith('nc_') or pn not in lv['pins']:
                    continue
                if lv['uses'][pn] == 'CLOCK' or (inst, pn) in clock_pins:
                    continue
                nets[s].append((inst, pn, CR.xf(v, lv['w'], lv['h'], *lv['pins'][pn])))
                directions[(inst, pn)] = lv['directions'][pn]
    return pl, nets, directions, top_inputs


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def plan_net(driver, loads, R):
    """Registered tree: returns (stages_max, station_count, pad_flops, longest_hop_without_relays)."""
    pts = [driver[2]] + [l[2] for l in loads]
    n = len(pts)
    dist = [0.0] + [math.inf] * (n - 1)       # tree distance from the driver
    best = [math.inf] * n; par = [-1] * n; done = [False] * n
    best[0] = 0.0
    edges = []
    for _ in range(n):                         # Prim on Manhattan distance, root = driver
        u = min((i for i in range(n) if not done[i]), key=lambda i: best[i])
        done[u] = True
        if par[u] >= 0:
            dist[u] = dist[par[u]] + md(pts[par[u]], pts[u]); edges.append((par[u], u))
        for v in range(n):
            if not done[v]:
                d = md(pts[u], pts[v])
                if d < best[v]:
                    best[v] = d; par[v] = u
    stations = sum(int(dist[v] // R) - int(dist[u] // R) for u, v in edges)
    # a station exactly at a sink distance is not needed at the sink itself
    sink_st = [max(0, math.ceil(dist[i] / R) - 1) for i in range(1, n)]
    smax = max(sink_st, default=0)
    pads = sum(smax - s for s in sink_st)
    return smax, stations, pads, max(md(driver[2], l[2]) for l in loads)


def base(pn):
    return re.sub(r'\[\d+\]$', '', pn)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('case'); ap.add_argument('--reach', type=float, default=450.0)
    ap.add_argument('--contract'); ap.add_argument('--out'); ap.add_argument('--nets-out')
    a = ap.parse_args()
    c = Path(a.case)
    contract = json.loads(Path(a.contract).read_text()) if a.contract else None
    pl, nets, directions, top_inputs = load_case(c, contract)
    R = a.reach
    fam = collections.defaultdict(lambda: dict(nets=0, max_hop_um=0.0, stages_max=0, stage_hist=collections.Counter(),
                                               station_flops=0, pad_flops=0, sinks_max=0, stages_sum=0,
                                               driver_master='', driver_port='', sink_masters=[], sink_ports=[]))
    top, ambiguous, per_net = collections.Counter(), 0, []
    isrly = lambda inst: pl[inst]['master'].startswith('hbfd_rly_')
    hop_st, net_drv, net_loads, rly_in = {}, {}, {}, {}   # end-to-end trace through existing relay instances
    for n, ends in nets.items():
        if n in top_inputs:
            top[re.sub(r'\d+', '#', n)] += 1
            continue
        if len(ends) < 2:
            continue
        drivers = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']
        loads = [e for e in ends if directions.get(e[:2]) == 'INPUT']
        if len(drivers) != 1 or len(drivers) + len(loads) != len(ends):
            ambiguous += 1
            continue
        d = drivers[0]
        smax, st, pads, hop = plan_net(d, loads, R)
        hop_st[n] = smax; net_drv[n] = d; net_loads[n] = loads
        for l in loads:
            if isrly(l[0]):
                k = re.search(r'\[(\d+)\]$', l[1]); rly_in[(l[0], k.group(1) if k else '')] = n
        lm = sorted({pl[l[0]]['master'] for l in loads})
        key = f"{pl[d[0]]['master']}.{base(d[1])} -> {'+'.join(lm)[:120]}.{'+'.join(sorted({base(l[1]) for l in loads}))[:60]}"
        f = fam[key]
        f['nets'] += 1; f['max_hop_um'] = max(f['max_hop_um'], round(hop, 1)); f['stages_max'] = max(f['stages_max'], smax)
        f['stage_hist'][smax] += 1; f['stages_sum'] += smax
        f['driver_master'] = pl[d[0]]['master']; f['driver_port'] = base(d[1]); f['sink_masters'] = lm
        f['sink_ports'] = sorted({base(l[1]) for l in loads})
        f['station_flops'] += st; f['pad_flops'] += pads
        f['sinks_max'] = max(f['sinks_max'], len(loads))
        if smax and a.nets_out:
            per_net.append(dict(net=n, driver=f'{d[0]}/{d[1]}', sinks=len(loads), stages=smax, stations=st, pads=pads))
    # end-to-end: every net with a non-relay sink, walked back through relay o[k] <- i[k] to its origin driver
    e2e = collections.defaultdict(lambda: dict(nets=0, existing_relays_max=0, added_max=0, total_max=0, total_sum=0))
    for n, loads in net_loads.items():
        term = [l for l in loads if not isrly(l[0])]
        if not term:
            continue
        added, relays, cur, seen = hop_st[n], 0, n, set()
        while isrly(net_drv[cur][0]) and cur not in seen:
            seen.add(cur)
            k = re.search(r'\[(\d+)\]$', net_drv[cur][1]); prev = rly_in.get((net_drv[cur][0], k.group(1) if k else ''))
            relays += 1
            if prev is None:
                break
            added += hop_st[prev]; cur = prev
        o = net_drv[cur]
        key = (f"{pl[o[0]]['master']}.{base(o[1])}", '+'.join(sorted({f"{pl[l[0]]['master']}.{base(l[1])}" for l in term}))[:160])
        e = e2e[key]; e['nets'] += 1; e['existing_relays_max'] = max(e['existing_relays_max'], relays)
        e['added_max'] = max(e['added_max'], added); e['total_max'] = max(e['total_max'], added + relays)
        e['total_sum'] += added + relays
    over = {k: v for k, v in fam.items() if v['stages_max'] > 0}
    rows = sorted(over.items(), key=lambda kv: -(kv[1]['station_flops'] + kv[1]['pad_flops']))
    res = dict(schema='opentallas.hbm.die_relay_pass.v1', case=str(c), reach_um=R,
               rule='no unregistered die hop > reach; multicast = registered equal-age tree (pads at near sinks)',
               families=len(fam), families_over_reach=len(over),
               nets_over_reach=sum(v['nets'] - v['stage_hist'][0] for v in over.values()),
               station_flops=sum(v['station_flops'] for v in over.values()),
               pad_flops=sum(v['pad_flops'] for v in over.values()),
               ambiguous_nets=ambiguous, top_driven_families=dict(top.most_common()),
               qualification='GEOMETRY_ONLY (pin-to-pin Manhattan, Prim tree); not routed, not placed, not timed',
               end_to_end=sorted([dict(origin=k[0], sinks=k[1], **v, total_mean=round(v['total_sum'] / v['nets'], 2))
                                  for k, v in e2e.items()], key=lambda r: -r['total_sum']),
               rows=[dict(family=k, **{x: (dict(sorted(y.items())) if isinstance(y, collections.Counter) else y)
                                       for x, y in v.items()}) for k, v in rows])
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    if a.nets_out:
        Path(a.nets_out).write_text(json.dumps(per_net) + '\n')
    print(f"reach {R} um: {res['nets_over_reach']} nets over reach in {len(over)}/{len(fam)} families; "
          f"station flops {res['station_flops']}, pad flops {res['pad_flops']}, ambiguous {ambiguous}")
    for k, v in rows[:40]:
        print(f"{v['nets']:7d} nets  hop<={v['max_hop_um']:8.0f}  +{v['stages_max']:2d} st  "
              f"st_ff {v['station_flops']:8d} pad_ff {v['pad_flops']:8d} fo {v['sinks_max']:3d}  {k}")


if __name__ == '__main__':
    main()
