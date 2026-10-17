#!/usr/bin/env python3
"""d4b relay stations -> v16 contract revision spec (H-NETLIST/H-ELEM 2026-10-16).

    relay_contract_d4b.py --stations results/arch/hbm_die_v16/d4b_relay_stations_450.json.gz \
        --case /home/ubuntu/artifacts/hdie-d4/d4/d4b_place --case-contract CONTRACT.json \
        --out tools/hbm_die_v15/v16_specs/relays_d4b.json --report results/arch/hbm_die_v16/relays_d4b_report.json

Re-derives every bus of the station list exactly as tools/hbm_die_v15/die_relay_stations.py does (same case nets, same
Prim tree, same station points -- the rows must reproduce bit-for-bit, else REFUSE), keeping the tree parent links the
list does not store, and emits:
  * instances: one hbfd_rly_{48|624}_{dir} tile per (station, tile) and per (pad stage, tile); i[k] -> o[k] chains;
  * clocks: ck / rs of every tile = the bus driver's domain (row 'domain');
  * straps: unused input lanes of the driver-fed tiles tied 0 (dedupe pad: the standard relay widths);
  * relay_splice: per bus, the driver bits (inst, port, bit) in bus order, the station tree (parent of each station),
    each sink's feeding station and pad chain, and the (sink inst, port, bit) loads of every bus bit -- consumed by
    full_die_v16.py, which rewires those load bits through the chain (and refuses if the current contract no longer
    drives a listed load bit from the listed driver bit);
  * compiler constants: per-bus depth and per-sink depth; equal_age_pad buses have one age = max depth;
  * hop check: every hop (driver pin centroid -> station -> ... -> sink pin centroid) <= reach on the frozen case.
Branch points are wire fan-outs of the station at the branch (the Prim tree's branch nodes are sink pins, so no
fan-out node is needed: the relay4 F20 node is not used by this list).
"""
import argparse, collections, gzip, json, math, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_relay_pass as RP  # noqa: E402
import die_relay_stations as RS  # noqa: E402

PIN = re.compile(r'^(\w+)\[(\d+)\]$')


def pinbit(pn):
    m = PIN.match(pn)
    return (m.group(1), int(m.group(2))) if m else (pn, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--stations', required=True); ap.add_argument('--case', required=True)
    ap.add_argument('--case-contract', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    st = json.loads(gzip.open(a.stations).read() if a.stations.endswith('.gz') else Path(a.stations).read_text())
    R = st['reach_um']
    rows_by_key = {}
    # H-DIE 1815: reset nets go to the reset forest (per-region reset relays/sync), as por_* already do, never into data
    # relay stations: a list row whose driver ports are all resets (e.g. subr_<q>.bridge_rst_n) is excluded here and its
    # tiles are removed from the reconciliation target.
    reset_rx = re.compile(r'^(por_\w*|\w*rst_n|\w*_rst|\w*reset\w*)$')
    reset_rows, reset_tiles = [], collections.Counter()
    for r in st['rows']:
        if all(reset_rx.match(p_) for p_ in r['driver'].split('.', 1)[1].split('+')):
            reset_rows.append(r['driver'])
            W_ = 48 if r['bits'] <= 48 else 624; T_ = math.ceil(r['bits'] / W_)
            reset_tiles[f'hbfd_rly_{W_}'] += sum(int(s_.get('tiles', T_)) for s_ in r['stations'])
            reset_tiles[f'hbfd_rly_{W_}'] += sum(int(p_['stages']) * T_ for p_ in r.get('pads', []))
            continue
        rows_by_key[(r['driver'].split('.')[0], tuple(sorted(r['sinks'])))] = r
    contract = json.loads(Path(a.case_contract).read_text())
    pl, nets, directions, top_inputs = RP.load_case(Path(a.case), contract)
    GRID = (st.get('route') or {}).get('grid_um', 0) or 0
    router = None
    if GRID > 0:                                       # d4b-r: obstacle-aware routed stations (relay_router.py)
        import relay_router as RR
        man_ = json.loads((Path(a.case) / 'manifest.json').read_text())
        router = RR.Router(man_['placement'], man_['die_um'], R, G=GRID, carved=man_.get('carved_feedthrough'))
    buses = collections.defaultdict(lambda: dict(bits=0, dpts=[], spts=collections.defaultdict(list), nets=[], ports=set()))
    for n, ends in nets.items():
        if n in top_inputs or len(ends) < 2:
            continue
        drv = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']
        lds = [e for e in ends if directions.get(e[:2]) == 'INPUT']
        if len(drv) != 1 or len(drv) + len(lds) != len(ends):
            continue
        d = drv[0]
        if max(RP.md(d[2], l[2]) for l in lds) <= R:
            continue
        key = (d[0], tuple(sorted({l[0] for l in lds})))
        b = buses[key]; b['bits'] += 1; b['dpts'].append(d[2]); b['nets'].append((d, lds)); b['ports'].add(RP.base(d[1]))
        for l in lds:
            b['spts'][l[0]].append(l[2])
    insts, clocks, straps, splice, consts, problems = [], [], [], [], [], []
    tiles = collections.Counter(); pad_tiles = 0; hops = []; worst = (0, None); hop_viol = []
    seen = set()
    for bi, ((di, sk), b) in enumerate(sorted(buses.items(), key=lambda kv: -kv[1]['bits'])):
        r = rows_by_key.get((di, tuple(sorted(sk))))
        if r is None:
            continue                                   # skipped (reset forest / su_prog) or depth 0
        seen.add((di, tuple(sorted(sk))))
        cen = lambda pts: (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        root = cen(b['dpts']); sinks = list(b['spts']); spts = [cen(b['spts'][s]) for s in sinks]
        P, par, dist = RS.tree(root, spts)
        W = 48 if b['bits'] <= 48 else 624
        T = math.ceil(b['bits'] / W)
        if b['bits'] != r['bits'] or sinks != r['sinks']:
            problems.append(f"bus {r['driver']}: bits/sinks differ from the list ({b['bits']} vs {r['bits']})"); continue
        # stations with tree membership
        sl = []
        tail = {0: None}                               # node -> last station id on root..node (None = driver)
        kids_ = collections.defaultdict(list)
        for v in range(1, len(P)):
            kids_[par[v]].append(v)
        order, q = [], [0]
        while q:                                       # BFS from the driver: parents before children
            u = q.pop(0)
            for v in kids_[u]:
                order.append(v); q.append(v)
        if router is not None:
            sl, tail, depth_r, _v = RR.plan_bus(router, P, par, R, W, sinks)
            for s_ in sl:
                s_['pt'] = (s_['x'], s_['y'])
            order = []
        for v in order:
            u = par[v]; k0 = int(dist[u] // R) + 1; k1 = math.ceil(dist[v] / R) - 1
            prev = tail[u]
            for k in range(k0, k1 + 1):
                x, y = RS.along(P[u], P[v], k * R - dist[u])
                sl.append(dict(id=len(sl), depth=k, x=round(x, 1), y=round(y, 1), toward=sinks[v - 1],
                               master=f'hbfd_rly_{W}_{RS.flow(P[u], P[v])}', parent=prev, pt=(x, y)))
                prev = sl[-1]['id']
            tail[v] = prev
        a_ = sorted((s['depth'], s['x'], s['y'], s['toward'], s['master']) for s in sl)
        b_ = sorted((s['depth'], s['x'], s['y'], s['toward'], s['master']) for s in r['stations'])
        if a_ != b_:
            problems.append(f"bus {r['driver']}: stations do not reproduce ({len(a_)} vs {len(b_)})"); continue
        depth = depth_r if router is not None else [max(0, math.ceil(dist[i] / R) - 1) for i in range(1, len(P))]
        dmax = max(depth)
        pads = {}
        if r['cls'] == 'equal_age_pad':
            for i, s in enumerate(sinks):
                if depth[i] < dmax:
                    pads[s] = dmax - depth[i]
        # instances
        tag = f'rly{bi:04d}'
        def tname(sid, t): return f'{tag}_s{sid:03d}_t{t}'
        for s in sl:
            for t in range(T):
                insts.append(dict(name=tname(s['id'], t), master=s['master'], source='rtl/hbm_accel/die_glue/hbfd_rly_masters.sv',
                                  params={}, slot=f"d4b_relay:{r['driver']}", owner='H-DIE relay pass / H-NETLIST',
                                  note=f"d4b station depth {s['depth']} toward {s['toward']} tile {t}/{T}; home ({s['x']}, {s['y']}) um"))
                tiles[f'hbfd_rly_{W}'] += 1
        padhome = {p_['sink']: (p_['x'], p_['y']) for p_ in r.get('pads', [])}
        for s_, n in pads.items():
            i = sinks.index(s_)
            for k in range(n):
                for t in range(T):
                    insts.append(dict(name=f'{tag}_p{i:02d}_{k:02d}_t{t}', master=f'hbfd_rly_{W}_WE',
                                      source='rtl/hbm_accel/die_glue/hbfd_rly_masters.sv', params={},
                                      slot=f"d4b_relay_pad:{r['driver']}->{s_}", owner='H-DIE relay pass / H-NETLIST',
                                      note=f"equal-age pad stage {k + 1}/{n} at sink {s_} tile {t}/{T}; home ({padhome[s_][0]}, {padhome[s_][1]}) um"))
                    tiles[f'hbfd_rly_{W}'] += 1; pad_tiles += 1
        names = [x['name'] for x in insts if x['name'].startswith(tag + '_')]
        for nm in names:
            clocks.append(dict(inst=nm, port='ck', domain=r['domain'], kind='clock'))
            clocks.append(dict(inst=nm, port='rs', domain=r['domain'], kind='reset'))
        # bus bit order: driver (port, bit) sorted
        bits = sorted(((pinbit(d[1]), [(l[0],) + pinbit(l[1]) for l in lds]) for d, lds in b['nets']), key=lambda x: x[0])
        drv_bits = [[p, k] for (p, k), _ in bits]
        loads = [[list(x) for x in ls] for _, ls in bits]
        last = b['bits'] - (T - 1) * W
        for s in sl:
            if s['parent'] is None and last < W:
                straps.append(dict(inst=tname(s['id'], T - 1), port='i', lo=last, hi=W, value=0,
                                   reason=f'PAD standard relay hbfd_rly_{W}: bus {b["bits"]} b, lanes {last}..{W - 1} of the last tile tied low (outputs open)'))
        feed = {s_: tail[i + 1] for i, s_ in enumerate(sinks)}
        for s_, n in pads.items():
            if feed[s_] is None and last < W:          # pad chain fed straight from the driver
                straps.append(dict(inst=f'{tag}_p{sinks.index(s_):02d}_00_t{T - 1}', port='i', lo=last, hi=W, value=0,
                                   reason=f'PAD standard relay hbfd_rly_{W}: bus {b["bits"]} b, lanes {last}..{W - 1} tied low'))
        splice.append(dict(bus=tag, driver=di, cls=r['cls'], domain=r['domain'], width=W, tiles=T, bits=b['bits'],
                           driver_bits=drv_bits, loads=loads,
                           stations=[dict(id=s['id'], parent=s['parent']) for s in sl],
                           sink_feed=feed, pads={s_: n for s_, n in pads.items()},
                           pad_names={s_: [[f'{tag}_p{sinks.index(s_):02d}_{k:02d}_t{t}' for t in range(T)] for k in range(n)] for s_, n in pads.items()}))
        consts.append(dict(bus=tag, driver=r['driver'], cls=r['cls'], domain=r['domain'], bits=b['bits'], depth=dmax,
                           sink_edges={s_: (dmax if r['cls'] == 'equal_age_pad' else depth[i]) for i, s_ in enumerate(sinks)}))
        # hops: driver -> station chain -> sink pin centroid
        pos = {s['id']: s['pt'] for s in sl}
        for s in sl:
            p0 = root if s['parent'] is None else pos[s['parent']]
            h = s['hop_um'] if router is not None else RP.md(p0, s['pt']); hops.append(h)
            if h > R + 0.5: hop_viol.append(dict(bus=r['driver'], to=f"station {s['id']}", hop_um=round(h, 1)))
            if h > worst[0]: worst = (h, f"{r['driver']} -> station {s['id']}")
        for i, s_ in enumerate(sinks):
            p0 = root if tail[i + 1] is None else pos[tail[i + 1]]
            h = RP.md(p0, spts[i]); hops.append(h)
            if h > R + 0.5: hop_viol.append(dict(bus=r['driver'], to=f'sink {s_}', hop_um=round(h, 1)))
            if h > worst[0]: worst = (h, f"{r['driver']} -> sink {s_}")
    missing = [k for k in rows_by_key if k not in seen]
    for k in missing:
        problems.append(f'list bus {k[0]} -> {len(k[1])} sinks not found in the case')
    eq = collections.defaultdict(int)
    for c in consts:
        if c['cls'] == 'equal_age_pad':
            eq[c['domain']] = max(eq[c['domain']], c['depth'])
    spec = dict(region='relays_d4b', author='Claude H-NETLIST/H-ELEM 2026-10-16',
                basis_commit='d4b_relay_stations_450 (H-DIE) on the frozen d4b placement',
                instances=insts, clocks=clocks, straps=straps, relay_splice=splice,
                relay_excluded=dict(st['not_relayed'], **{'reset_forest (H-DIE 1815: bridge resets, as por_*)': reset_rows}),
                notes='d4b registered relay stations (reach 450 um): each station = 1 edge; p2p and cfg_no_pad sinks see their own depth, equal_age_pad sinks all see the bus max depth (pad stages at near sinks). Branches are wire fan-outs of the branch station.')
    Path(a.out).write_text(json.dumps(spec) + '\n')
    rep = dict(schema='opentallas.hbm.relays_d4b_report.v1', reach_um=R, buses=len(splice),
               tiles=dict(tiles), pad_tiles=pad_tiles, list_station_tiles=st['station_tiles'],
               reconciliation=dict(rly_624=tiles['hbfd_rly_624'], rly_48=tiles['hbfd_rly_48'], pads=pad_tiles,
                                   reset_forest_tiles=dict(reset_tiles),
                                   match=(dict(tiles) == {k: v - reset_tiles[k] for k, v in st['station_tiles'].items()})),
               reset_forest_rows=reset_rows, hop_violations=hop_viol,
               hops=len(hops), worst_hop_um=round(worst[0], 1), worst_hop=worst[1], hop_rule_pass=worst[0] <= R + 0.5,
               excluded=st['not_relayed'], compiler=dict(equal_age_max_depth_by_domain=dict(eq), buses=consts),
               problems=problems)
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('buses', 'tiles', 'pad_tiles', 'reconciliation', 'worst_hop_um', 'hop_rule_pass')}),
          len(problems), 'problems', problems[:5])
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
