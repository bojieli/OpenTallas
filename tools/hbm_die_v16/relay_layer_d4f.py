#!/usr/bin/env python3
"""H-NETLIST/D4F-RELAY 1017: d4f relay netlist layer on the F1 forwarded-clock relay family (full_die_v16 revision layer).

Input: an H-DIE routed station list (die_relay_stations.py --route-grid, rows: driver 'inst.p1+p2', sinks, bits, domain,
cls, sink_depths, stations [{depth,x,y,toward,master,tiles,parent,hop_um}], pads [{sink,stages,x,y}]), the contract the
layer applies to (bus bits = driver bits whose sink-instance set equals the row's sinks), the placement manifest and the
DIE-CLOCK region map (instance -> region; else the nearest d4f root site, provisional).

Rules (DIE-CLOCK F1 + H-DIE 10-17, binding):
  * INTRA-region or NEIGHBOUR-region bus (DIE-CLOCK region map 'neighbours'): the existing tiles hbfd_rly_{48,624}_<dir> (ck / rs on the
    regional root), branch points are wire fan-outs, equal-age pads at the sink (list pad counts).
  * NON-NEIGHBOUR inter-region bus: F1 forwarded tiles.  First station clk_in = the source regional root (domain clock binding);
    station k+1 clk_in = station k clk_out (fork: clk_out<b> of the branch it hangs on).  Every sink gets >= 1
    SINK-ROOT stage (fc tile, clk_in = sink regional root; further stages chained clk_out -> clk_in): p2p / cfg 1 stage,
    equal_age_pad buses target = max sink depth + 1 (equal age kept, +1 = the priced F1 region edge).
      - FORKING bus (any station or the driver with > 1 relayed consumer): split at the SOURCE into ceil(bits/48)
        parallel 48-bit lanes, each its own forwarded clock: hbfd_rly_48_<dir>_fc on 1-consumer stations,
        hbfd_rly_48_<dir>_fc_f<N> (N = consumers, 2..4) at fork stations.  (No 624 forks: dropped.)
      - single-branch bus: hbfd_rly_{48|624}_<dir>_fc, ceil(bits/W) tiles side by side, each its own clock chain.
  * The last lane / tile of a width that is not a multiple of W carries REAL driver bits in its spare positions (bit
    j >= bits takes driver bit j % bits): no tied input (strict bind), the spare lanes reach no load.
  * rs = the domain reset (reset forest leaf); never forwarded.
Output: layer json (instances, clocks, edges = clock chains, relay_splice_v2 = data trees for full_die_v16) + report
(tile counts, per-domain equal-age depth, hops > reach, regions used).
    relay_layer_d4f.py --stations S.json[.gz] --contract C.json[.gz] --manifest M.json --root-sites R.json
                       [--region-map MAP.json] --out L.json.gz --report REP.json
"""
import argparse, collections, gzip, json, math
from pathlib import Path

SRC_OLD = 'rtl/hbm_accel/die_glue/hbfd_rly_masters.sv'
SRC_FC = 'rtl/hbm_accel/die_glue/hbfd_rly_fc_masters.sv'
SRC_FCF = 'rtl/hbm_accel/die_glue/hbfd_rly_fcf_masters.sv'
DEPS_FC = ['rtl/hbm_accel/die_glue/ot_hbm_rly_fc.sv', 'rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']
DEPS_FCF = ['rtl/hbm_accel/die_glue/ot_hbm_rly_fcf.sv', 'rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']
DEPS_OLD = ['rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']


def load(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('--stations', '--contract', '--manifest', '--root-sites', '--out', '--report'):
        ap.add_argument(k, required=True)
    ap.add_argument('--region-map')
    a = ap.parse_args()
    st = load(a.stations); c = load(a.contract); man = load(a.manifest)
    R = st['reach_um']; pl = man['placement']; inst = c['instances']
    sites = load(a.root_sites)['sites']
    rm_ = load(a.region_map) if a.region_map else {}
    rmap = rm_.get('instances', rm_) if isinstance(rm_, dict) else {}
    if rm_.get('regions'):   # DIE-CLOCK map: nearest-site fallback over ITS sites
        sites = [dict(region=k, x=v['site'][0], y=v['site'][1]) for k, v in rm_['regions'].items()]
    neigh = {frozenset(x) for x in rm_.get('neighbours', [])}
    region_src = ('DIE-CLOCK map ' + str(a.region_map)) if rmap else 'nearest d4f root site (PROVISIONAL)'

    def cen(n):
        p = pl.get(n)
        return None if p is None else (p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)

    def region_of_pt(xy):
        return min(sites, key=lambda s: abs(s['x'] - xy[0]) + abs(s['y'] - xy[1]))['region']

    def region(n):
        for k in (n, (inst.get(n) or {}).get('slot')):
            if k in rmap:
                return rmap[k] if isinstance(rmap[k], str) else rmap[k]['region']
        xy = cen(n)
        return None if xy is None else region_of_pt(xy)
    # driver bit -> loads, from the contract edges (final names)
    loads = collections.defaultdict(list)                  # (drv inst, port, bit) -> [(sink, port, bit)]
    for e in c['edges']:
        s, d = e['source'], e['sink']
        for k in range(s[3] - s[2]):
            loads[(s[0], s[1], s[2] + k)].append((d[0], d[1], d[2] + k))
    by_drv = collections.defaultdict(list)
    for (di, p, k), ls in loads.items():
        by_drv[di].append((p, k, ls))
    insts, clocks, edges, splice, consts, problems = [], [], [], [], [], []
    tiles = collections.Counter(); hops_over = []
    used_regions = collections.Counter()
    for bi, r in enumerate(st['rows']):
        di, ports = r['driver'].split('.', 1); ports = set(ports.split('+'))
        sinks = list(r['sinks']); sset = set(sinks)
        if di not in inst:
            problems.append(f'{r["driver"]}: driver not in contract'); continue
        bits = sorted((p, k, ls) for p, k, ls in by_drv[di] if p in ports and {x[0] for x in ls} == sset)
        if len(bits) != r['bits']:
            problems.append(f'{r["driver"]}: {len(bits)} contract bits vs list {r["bits"]}')
            if not bits:
                continue
        n = len(bits); dom = r['domain']; cls = r['cls']
        sl = r['stations']
        rd = region(di); rs_ = {s_: region(s_) for s_ in sinks}
        # DIE-CLOCK 10-17: same region or NEIGHBOUR regions (outlines within 600 um) = plain stations on the own region
        # root (neighbour-matched delivery is DIE-CLOCK's); only non-neighbour pairs get the F1 forwarded chain
        inter = rd is None or any(v is None or (v != rd and frozenset((v, rd)) not in neigh) for v in rs_.values())
        used_regions[rd] += 1
        # sink feed: station at the sink's depth nearest to the sink (depth 0 = driver)
        sdep = dict(zip(sinks, r['sink_depths']))
        feed = {}
        for s_ in sinks:
            d_ = sdep[s_]
            if d_ == 0:
                feed[s_] = None; continue
            cand = [i for i, s in enumerate(sl) if s['depth'] == d_]
            xy = cen(s_) or (0, 0)
            feed[s_] = min(cand, key=lambda i: abs(sl[i]['x'] - xy[0]) + abs(sl[i]['y'] - xy[1])) if cand else None
            if not cand:
                problems.append(f'{r["driver"]}: no station at depth {d_} for sink {s_}')
        # consumers of every station (children stations + fed sinks) and of the driver
        cons = collections.defaultdict(list)
        for i, s in enumerate(sl):
            cons[s['parent']].append(('s', i))
        for s_ in sorted(sinks):
            cons[feed[s_]].append(('k', s_))
        fork = any(len(v) > 1 for k_, v in cons.items() if k_ is not None)
        # sink-root stages
        pads_list = {p['sink']: p['stages'] for p in r.get('pads', [])}
        if inter:
            if cls == 'equal_age_pad':
                tgt = max(sdep.values()) + 1
                stages = {s_: tgt - sdep[s_] for s_ in sinks}
            else:
                stages = {s_: 1 for s_ in sinks}
        else:
            stages = {s_: pads_list.get(s_, 0) for s_ in sinks}
        depth_eff = {s_: sdep[s_] + stages[s_] for s_ in sinks}
        if inter and fork:
            W, T, kind = 48, math.ceil(n / 48), 'fc48lane'
        else:
            W = 48 if n <= 48 else 624
            T = math.ceil(n / W); kind = 'fc' if inter else 'old'
        tag = f'rf{bi:04d}'
        def dir_of(s):
            return s['master'].rsplit('_', 1)[1]
        nodes = []
        for i, s in enumerate(sl):
            ncons = len(cons[i]); dr = dir_of(s)
            if kind == 'old':
                m, src, deps = f'hbfd_rly_{W}_{dr}', SRC_OLD, DEPS_OLD; outs = ['o'] * max(1, ncons)
            elif kind == 'fc':
                m, src, deps = f'hbfd_rly_{W}_{dr}_fc', SRC_FC, DEPS_FC; outs = ['o'] * max(1, ncons)
                if ncons > 1:
                    problems.append(f'{r["driver"]}: fc single-branch bus with a {ncons}-consumer station')
            else:
                if ncons <= 1:
                    m, src, deps = f'hbfd_rly_48_{dr}_fc', SRC_FC, DEPS_FC; outs = ['o']
                elif ncons <= 4:
                    m, src, deps = f'hbfd_rly_48_{dr}_fc_f{ncons}', SRC_FCF, DEPS_FCF; outs = [f'o{k}' for k in range(ncons)]
                else:
                    problems.append(f'{r["driver"]}: station {i} has {ncons} consumers (> 4)'); m, src, deps, outs = None, None, None, []
            names = [f'{tag}_s{i:03d}_l{t}' for t in range(T)]
            pb = None
            if s['parent'] is not None:
                pb = cons[s['parent']].index(('s', i))
            nodes.append(dict(id=i, parent=s['parent'], pbranch=pb, names=names, outs=outs))
            for t in range(T):
                insts.append(dict(name=names[t], master=m, source=src, rtl_deps=deps, params={}, slot=f'd4f_relay:{r["driver"]}',
                                  owner='H-DIE relay route / H-NETLIST',
                                  note=f'{kind} station depth {s["depth"]} lane/tile {t}/{T} toward {s["toward"]}; home ({s["x"]}, {s["y"]}) um'))
                tiles[m] += 1
                clocks.append(dict(inst=names[t], port='rs', domain=dom, kind='reset'))
                if kind == 'old':
                    clocks.append(dict(inst=names[t], port='ck', domain=dom, kind='clock'))
                elif s['parent'] is None:
                    clocks.append(dict(inst=names[t], port='clk_in', domain=dom, kind='clock'))   # source regional root
                else:
                    pn = nodes[s['parent']]
                    cp = 'clk_out' if len(pn['outs']) == 1 else f'clk_out{pb}'
                    edges.append(dict(src=[pn['names'][t], cp], dst=[names[t], 'clk_in'], bits=1, clock=dom,
                                      basis='F1 forwarded clock (station k+1 clk_in = station k clk_out)'))
            if s.get('hop_um', 0) > R + 0.5:
                hops_over.append(dict(bus=r['driver'], station=i, hop_um=s['hop_um'], domain=dom, cls=cls))
        sk = {}
        for s_ in sinks:
            src = feed[s_]
            br = None if src is None else cons[src].index(('k', s_))
            chain = []
            xy = cen(s_) or (0, 0)
            for k in range(stages[s_]):
                names = [f'{tag}_k{sinks.index(s_):02d}_{k:02d}_l{t}' for t in range(T)]
                chain.append(names)
                for t in range(T):
                    if kind == 'old':
                        m, src_f, deps = f'hbfd_rly_{W}_WE', SRC_OLD, DEPS_OLD
                    else:
                        m, src_f, deps = f'hbfd_rly_{W}_WE_fc', SRC_FC, DEPS_FC
                    insts.append(dict(name=names[t], master=m, source=src_f, rtl_deps=deps, params={}, slot=f'd4f_relay_sink:{r["driver"]}->{s_}',
                                      owner='H-DIE relay route / H-NETLIST',
                                      note=f'{"sink-root stage" if kind != "old" else "equal-age pad"} {k + 1}/{stages[s_]} at {s_} lane/tile {t}/{T}; home ({round(xy[0], 1)}, {round(xy[1], 1)}) um'))
                    tiles[m] += 1
                    clocks.append(dict(inst=names[t], port='rs', domain=dom, kind='reset'))
                    if kind == 'old':
                        clocks.append(dict(inst=names[t], port='ck', domain=dom, kind='clock'))
                    elif k == 0:
                        clocks.append(dict(inst=names[t], port='clk_in', domain=dom, kind='clock'))   # SINK regional root
                    else:
                        edges.append(dict(src=[chain[k - 1][t], 'clk_out'], dst=[names[t], 'clk_in'], bits=1, clock=dom,
                                          basis='F1 sink-root chain (forwarded)'))
            sk[s_] = dict(src=[src, br], chain=chain)
        splice.append(dict(bus=tag, driver=di, cls=cls, domain=dom, width=W, tiles=T, bits=n,
                           driver_bits=[[p, k] for p, k, _ in bits], loads=[[list(x) for x in ls] for _, _, ls in bits],
                           nodes=nodes, sinks=sk, kind=kind, inter_region=bool(inter)))
        consts.append(dict(bus=tag, driver=r['driver'], cls=cls, domain=dom, bits=n, kind=kind, lanes=T, inter_region=bool(inter),
                           fork=fork, sink_edges=depth_eff))
    eq = collections.defaultdict(int)
    for x in consts:
        if x['cls'] == 'equal_age_pad':
            eq[x['domain']] = max(eq[x['domain']], max(x['sink_edges'].values()))
    spec = dict(region='relays_d4f', author='Claude H-NETLIST/D4F-RELAY 1017', basis_commit=f'H-DIE station list {a.stations}',
                instances=insts, clocks=clocks, edges=edges, straps=[], gaps=[], relay_splice_v2=splice,
                relay_excluded=st.get('not_relayed', {}), notes=__doc__.split('\n\n')[1])
    with gzip.open(a.out, 'wt') as f:
        json.dump(spec, f)
    import re as _re
    cat = collections.Counter()
    for m_, v in tiles.items():
        mm = _re.match(r'hbfd_rly_(\d+)_[A-Z]+(_fc)?(_f(\d))?$', m_ or '')
        if not mm:
            cat['unknown'] += v; continue
        cat[('fc' if mm.group(2) else 'old') + mm.group(1) + (f'_f{mm.group(4)}' if mm.group(4) else '')] += v
    rep = dict(schema='opentallas.hbm.relays_d4f_report.v1', tile_categories=dict(sorted(cat.items())), reach_um=R, region_source=region_src, buses=len(splice),
               tiles=dict(sorted(tiles.items())), kinds=dict(collections.Counter(x['kind'] for x in consts)),
               fork_buses=sum(1 for x in consts if x['fork']), inter_region_buses=sum(1 for x in consts if x['inter_region']),
               equal_age_max_depth_by_domain=dict(eq), hops_over_reach=hops_over, problems=problems, compiler=consts)
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('buses', 'tile_categories', 'kinds', 'fork_buses', 'inter_region_buses', 'equal_age_max_depth_by_domain')}),
          len(hops_over), 'hops over reach,', len(problems), 'problems', problems[:4])


if __name__ == '__main__':
    main()
