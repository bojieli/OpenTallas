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
LANDING mode (--land, HBM-LANDING 10-18, lanes/LANDING-CONTRACT.md sections 2/3/7; default off = byte-identical output):
  * every F1 forwarded station becomes a HALF-CYCLE lane station with an in-band lane EPOCH bit (cores
    rtl/qwen_split/qfd_fwd_lane.sv): the root station (parent None) = hbfd_lh0_<W>_<dir>[_f<N>] on the SOURCE root
    (ck = domain clock, en = source domain reset leaf: the inverting hop-0 ICG), every other = hbfd_lh_<W>_<dir>[_f<N>]
    (ckf / ea = the parent's ck_o<k> / eb<k>); no rs on lane stations (data flushed by the producer).
  * the FIRST sink-root stage becomes the LANDING hbfd_land_<W>_<dir of the feeding station> (ckf / ea / a from the
    feeding station, ck = sink domain clock = sink regional root, rs = sink domain reset leaf, K strap k2..k0); a
    0-station forwarded sink gets hbfd_land0_<W>_<dir> (ck_s / en = source root / source reset); the remaining
    equal-age pad stages after it are PLAIN root-clocked hbfd_rly_<W>_WE (ck / rs on the sink root).
  * K strap per link (= bus row x sink, all lanes share it) from --land-plan {links: [{link: '<driver row>-><sink>', E,
    K?, stations?}]}: K = (ceil(N/2) + E) mod 8 with the layer's REAL N (source and sink regional resets released on the
    same root edge; 0 encodes 8); a plan K is used only when the entry's 'stations' equals the real N (a K is valid for
    one N only: the DCC pilot plan's K uses its model N); no plan entry -> E = 1 (the ideal-clock value) placeholder,
    listed NO_E in the report.  Checked on RTL 2e482a69f (non-inverting hop 0): relay lockstep 120 buses / 230 landings
    PASS at E = 1 for both parities of N (results/arch/hbm_die_d4g/landing/chain_smoke/lockstep120_rtl2e48).
  * fault: --land-fault pins (default) puts every landing fault on a die status pin <landing>__fault (contract
    die_pins, as S81 dv_bind land_fault); aggregation into the regional fault tree is gap G-D4G-LAND-FAULT.
  * compiler constants per sink (half-cycle): ceil(N/2) + 1 + E + pads edges from the driver pin to the sink pin, N = lane
    stations (contract N/2 + 1 + E + 1 counts the sink input flop too); latency is constant for dL inside the window.

Output: layer json (instances, clocks, edges = clock chains, relay_splice_v2 = data trees for full_die_v16) + report
(tile counts, per-domain equal-age depth, hops > reach, regions used).
    relay_layer_d4f.py --stations S.json[.gz] --contract C.json[.gz] --manifest M.json --root-sites R.json
                       [--region-map MAP.json] --out L.json.gz --report REP.json
"""
import argparse, collections, gzip, json, math, re
from pathlib import Path

SRC_OLD = 'rtl/hbm_accel/die_glue/hbfd_rly_masters.sv'
SRC_FC = 'rtl/hbm_accel/die_glue/hbfd_rly_fc_masters.sv'
SRC_FCF = 'rtl/hbm_accel/die_glue/hbfd_rly_fcf_masters.sv'
DEPS_FC = ['rtl/hbm_accel/die_glue/ot_hbm_rly_fc.sv', 'rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']
DEPS_FCF = ['rtl/hbm_accel/die_glue/ot_hbm_rly_fcf.sv', 'rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']
DEPS_OLD = ['rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']
SRC_LANE = 'rtl/hbm_accel/die_glue/hbfd_lane_masters.sv'
DEPS_LANE = ['rtl/hbm_accel/die_glue/ot_hbm_lane.sv', 'rtl/qwen_split/qfd_fwd_lane.sv', 'rtl/hdc/ot_hdc_cg.sv']


def load(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('--stations', '--contract', '--manifest', '--root-sites', '--out', '--report'):
        ap.add_argument(k, required=True)
    ap.add_argument('--region-map')
    ap.add_argument('--fork-lane-width', type=int, default=48,
                    help='H-RELAY 10-17 lane model: lane width of a FORKING inter-region bus (48 = the r8b form; 136 = '
                         'wide fork lanes, ceil(bits/136) lanes each with its own forwarded clock, hbfd_rly_136_*_fc[_f<N>])')
    ap.add_argument('--lane-rows', action='store_true',
                    help="H-RELAY 10-17: each station = ONE row of its T lane tiles at a fixed site (note 'lane row <id> "
                         "<t>/<T> <flow>; site (x, y) um', placed as a unit by die_case_v16); sink-root stages sit at the "
                         "sink PIN centroid (row 'pins', relay_lanes_d4f.py), not the sink instance centre")
    ap.add_argument('--exclude-re', help='rows whose driver or any sink instance matches are left to another layer '
                    '(e.g. ^(rfr|sfr)_: the fixed-depth SU RF / SFU chains, su_chain_rehome_d4f.py)')
    ap.add_argument('--land', action='store_true', help='HBM-LANDING 10-18: half-cycle lane stations + LANDINGS (module doc)')
    ap.add_argument('--land-plan', help="--land: per-link E / K JSON {links: [{link: '<driver row>-><sink>', E, K?}]}")
    ap.add_argument('--land-fault', choices=('pins', 'open'), default='pins',
                    help='--land: landing fault outputs -> die status pins (default) or left open (diagnostic only)')
    a = ap.parse_args()
    LP = {}
    if a.land and a.land_plan:
        LP = {x['link']: x for x in load(a.land_plan).get('links', [])}
    land_rows, straps, die_pins = [], [], []
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
    # bus bits per row: driver bits on the row's ports whose sink-instance set is the row's; a row whose ports no longer
    # exist (remastered driver, e.g. the writer per-SM port split) takes the UNCLAIMED driver bits with the same sink set
    rowbits, claimed, notes = {}, collections.defaultdict(set), []
    if a.exclude_re:
        xr = re.compile(a.exclude_re); n0 = len(st['rows'])
        st['rows'] = [r for r in st['rows'] if not (xr.match(r['driver']) or any(xr.match(k) for k in r['sinks']))]
        notes.append(f'excluded {n0 - len(st["rows"])} rows matching {a.exclude_re}')
    for bi, r in enumerate(st['rows']):
        di, ports = r['driver'].split('.', 1); ports = set(ports.split('+'))
        rowbits[bi] = sorted((p, k, ls) for p, k, ls in by_drv.get(di, []) if p in ports and {x[0] for x in ls} == set(r['sinks']))
        claimed[di] |= {(p, k) for p, k, _ in rowbits[bi]}
    for bi, r in enumerate(st['rows']):
        di = r['driver'].split('.', 1)[0]
        if not rowbits[bi] and di in inst:
            rowbits[bi] = sorted((p, k, ls) for p, k, ls in by_drv[di] if (p, k) not in claimed[di] and {x[0] for x in ls} == set(r['sinks']))
            claimed[di] |= {(p, k) for p, k, _ in rowbits[bi]}
            if rowbits[bi]:
                notes.append(f'{r["driver"]}: ports remastered -> {len(rowbits[bi])} bits on {sorted({p for p, _, _ in rowbits[bi]})[:6]}')
    # remaining unclaimed bits of a listed driver whose sink set matches a row of it (port split into more face groups,
    # e.g. sfu _w/_e -> _w/_n/_e/_s): join the row with the same port stem (else the first such row)
    import re as _re0
    stem = lambda p: _re0.sub(r'_[wnes]$', '', p)
    rows_of = collections.defaultdict(list)
    for bi, r in enumerate(st['rows']):
        rows_of[r['driver'].split('.', 1)[0]].append(bi)
    unmatched = collections.Counter()
    for di, bis in rows_of.items():
        for p, k, ls in by_drv.get(di, []):
            if (p, k) in claimed[di]:
                continue
            ss = {x[0] for x in ls}
            cand = [bi for bi in bis if set(st['rows'][bi]['sinks']) == ss]
            if not cand:
                unmatched[di] += 1; continue
            pick = next((bi for bi in cand if stem(p) in {stem(q) for q in st['rows'][bi]['driver'].split('.', 1)[1].split('+')}), cand[0])
            rowbits[pick].append((p, k, ls)); claimed[di].add((p, k))
            notes.append(f'{st["rows"][pick]["driver"]}: +{p}[{k}] (new face port, same sinks)') if k == 0 else None
    for bi in rowbits:
        rowbits[bi].sort()
    for di, v in unmatched.items():
        notes.append(f'{di}: {v} driver bits with no list row of the same sink set (not relayed: local or new sink set)')
    for bi, r in enumerate(st['rows']):
        di, ports = r['driver'].split('.', 1); ports = set(ports.split('+'))
        sinks = list(r['sinks']); sset = set(sinks)
        if di not in inst:
            problems.append(f'{r["driver"]}: driver not in contract'); continue
        bits = rowbits[bi]
        if not bits:
            problems.append(f'{r["driver"]}: no contract bits (list {r["bits"]})'); continue
        if len(bits) != r['bits']:
            notes.append(f'{r["driver"]}: {len(bits)} contract bits relayed (list {r["bits"]})')
        n = len(bits); dom = r['domain']; cls = r['cls']
        sl = [dict(x) for x in r['stations']]
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
            # the last station routed toward the sink feeds it (H-DIE hand re-homed rows: list sink depths are pre-split)
            tw = [i for i, s in enumerate(sl) if s.get('toward') == s_]
            if tw:
                feed[s_] = max(tw, key=lambda i: sl[i]['depth'])
                if sl[feed[s_]]['depth'] != d_ and not r.get('hand_rehomed'):
                    problems.append(f'{r["driver"]}: sink {s_} list depth {d_} != last station toward it {sl[feed[s_]]["depth"]}')
                continue
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
        lane48 = inter and fork
        # fork degree > 4 (lane48 buses): cascade at the same home -- an f4 keeps 3 consumers and its 4th branch feeds a
        # co-located fork station holding the rest (+1 stage for those; equal-age targets below use the TREE depth)
        for i in range(len(sl)):
            while lane48 and len(cons[i]) > 4:
                j = len(sl); s0 = sl[i]
                sl.append(dict(depth=s0['depth'] + 1, x=s0['x'], y=s0['y'], toward=s0['toward'], master=s0['master'],
                               tiles=s0.get('tiles'), parent=i, hop_um=0.0, cascade=True))
                rest = cons[i][3:]; cons[i] = cons[i][:3] + [('s', j)]; cons[j] = rest
                for kind_, x in rest:
                    if kind_ == 's':
                        sl[x]['parent'] = j
                    else:
                        feed[x] = j
        def tdep(i):
            d_ = 0
            while i is not None:
                d_ += 1; i = sl[i]['parent']
            return d_
        sdep0, sdep = sdep, {s_: tdep(feed[s_]) for s_ in sinks}
        bad = [s_ for s_ in sinks if sdep[s_] != sdep0[s_] and not (feed[s_] is not None and sl[feed[s_]].get('cascade'))]
        if bad:
            problems.append(f'{r["driver"]}: list sink depth != tree depth for {bad[:3]}')
        order, q = [], [i for i, x in enumerate(sl) if x['parent'] is None]
        while q:
            i = q.pop(0); order.append(i); q += [x for k_, x in cons[i] if k_ == 's']
        if len(order) != len(sl):
            problems.append(f'{r["driver"]}: station tree not connected ({len(order)}/{len(sl)})')
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
        if lane48:
            WF = a.fork_lane_width
            W, T, kind = WF, math.ceil(n / WF), ('fc48lane' if WF == 48 else f'fc{WF}lane')
        else:
            W = 48 if n <= 48 else 624
            T = math.ceil(n / W); kind = 'fc' if inter else 'old'
        tag = f'rf{bi:04d}'
        def dir_of(s):
            return s['master'].rsplit('_', 1)[1]
        nodes = {}
        for i in order:
            s = sl[i]; ncons = len(cons[i]); dr = dir_of(s)
            if kind == 'old':
                m, src, deps = f'hbfd_rly_{W}_{dr}', SRC_OLD, DEPS_OLD; outs = ['o'] * max(1, ncons)
            elif kind == 'fc':
                m, src, deps = f'hbfd_rly_{W}_{dr}_fc', SRC_FC, DEPS_FC; outs = ['o'] * max(1, ncons)
                if ncons > 1:
                    problems.append(f'{r["driver"]}: fc single-branch bus with a {ncons}-consumer station')
            else:
                if ncons <= 1:
                    m, src, deps = f'hbfd_rly_{W}_{dr}_fc', SRC_FC, DEPS_FC; outs = ['o']
                elif ncons <= 4:
                    m, src, deps = f'hbfd_rly_{W}_{dr}_fc_f{ncons}', SRC_FCF, DEPS_FCF; outs = [f'o{k}' for k in range(ncons)]
                else:
                    problems.append(f'{r["driver"]}: station {i} has {ncons} consumers (> 4)'); m, src, deps, outs = None, None, None, []
            lane = a.land and kind != 'old'
            iport = 'i'
            if lane and m:
                hop0 = s['parent'] is None
                nb = len(outs)
                m = f"hbfd_lh{'0' if hop0 else ''}_{W}_{dr}" + (f'_f{nb}' if nb > 1 else '')
                src, deps, iport = SRC_LANE, DEPS_LANE, 'a'
                outs = ['b'] if nb == 1 else [['b', k * W, (k + 1) * W] for k in range(nb)]
            names = [f'{tag}_s{i:03d}_l{t}' for t in range(T)]
            pb = None
            if s['parent'] is not None:
                pb = cons[s['parent']].index(('s', i))
            nodes[i] = dict(id=i, parent=s['parent'], pbranch=pb, names=names, outs=outs)
            if lane:
                nodes[i]['iport'] = iport
            for t in range(T if m else 0):
                site = (f'lane row {tag}_s{i:03d} {t}/{T} {dr}; site ({s["x"]}, {s["y"]}) um' if a.lane_rows
                        else f'home ({s["x"]}, {s["y"]}) um')
                insts.append(dict(name=names[t], master=m, source=src, rtl_deps=deps, params={}, slot=f'd4f_relay:{r["driver"]}',
                                  owner='H-DIE relay route / H-NETLIST',
                                  note=f'{kind} station depth {s["depth"]} lane/tile {t}/{T} toward {s["toward"]}; {site}'))
                tiles[m] += 1
                if lane:
                    if s['parent'] is None:      # hop 0: inverting ICG on the source root, opened by the source reset
                        clocks.append(dict(inst=names[t], port='ck', domain=dom, kind='clock'))
                        clocks.append(dict(inst=names[t], port='en', domain=dom, kind='reset'))
                    else:
                        pn = nodes[s['parent']]; br_ = [] if len(pn['outs']) == 1 else [pb, pb + 1]
                        edges.append(dict(src=[pn['names'][t], 'ck_o'] + br_, dst=[names[t], 'ckf'], bits=1, clock=dom,
                                          basis='half-cycle lane clock (station k+1 ckf = station k ck_o = ~cap)'))
                        edges.append(dict(src=[pn['names'][t], 'eb'] + br_, dst=[names[t], 'ea'], bits=1, clock=dom,
                                          basis='lane epoch (source released reset, one station per forwarded edge)'))
                    continue
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
            pin_ = (r.get('pins') or {}).get('sinks', {}).get(s_) if a.lane_rows else None
            if pin_:
                xy = tuple(pin_)
            lane = a.land and kind != 'old'
            cports = []
            if lane:
                lk = f'{r["driver"]}->{s_}'; pe = LP.get(lk)
                E_ = pe.get('E') if pe else None
                N_ = 0 if src is None else tdep(src)
                # K: the read offset counts from the common reset release; the lane epoch reaches the ring ceil(N/2)
                # edges later (half-cycle stations), so K = ceil(N/2) + E (mod 8, 0 encodes 8) -- bench-calibrated
                # (relay_lockstep_bench.py: ideal clocks give E = 1, latency ceil(N/2) + 2 at the sink pin)
                K_ = (pe['K'] % 8) if (pe and pe.get('K') is not None and pe.get('stations') == N_) \
                    else ((-(-N_ // 2) + (E_ if E_ is not None else 1)) % 8)
                if src is None:
                    sx = cen(di) or xy
                    dx, dy = xy[0] - sx[0], xy[1] - sx[1]
                    ldir = ('WE' if dx >= 0 else 'EW') if abs(dx) >= abs(dy) else ('SN' if dy >= 0 else 'NS')
                else:
                    ldir = dir_of(sl[src])
            for k in range(stages[s_]):
                names = [f'{tag}_k{sinks.index(s_):02d}_{k:02d}_l{t}' for t in range(T)]
                chain.append(names)
                if lane:
                    cports.append(['a', 'b'] if k == 0 else ['i', 'o'])
                for t in range(T):
                    if lane:
                        if k == 0:
                            m = f'hbfd_land{"0" if src is None else ""}_{W}_{ldir}'; src_f, deps = SRC_LANE, DEPS_LANE
                            what = f'LANDING (K {K_}{"" if E_ is not None else " NO_E placeholder"}) N {N_}'
                        else:
                            m, src_f, deps = f'hbfd_rly_{W}_WE', SRC_OLD, DEPS_OLD; what = f'equal-age pad (sink root) {k}/{stages[s_] - 1}'
                        insts.append(dict(name=names[t], master=m, source=src_f, rtl_deps=deps, params={}, slot=f'd4f_relay_sink:{r["driver"]}->{s_}',
                                          owner='HBM-LANDING / H-NETLIST',
                                          note=f'{what} at {s_} lane/tile {t}/{T}; '
                                               + (f'lane row {tag}_k{sinks.index(s_):02d}_{k:02d} {t}/{T} {ldir if k == 0 else "WE"}; site ({round(xy[0], 1)}, {round(xy[1], 1)}) um'
                                                  if a.lane_rows else f'home ({round(xy[0], 1)}, {round(xy[1], 1)}) um')))
                        tiles[m] += 1
                        if k == 0:
                            if src is None:
                                clocks.append(dict(inst=names[t], port='ck_s', domain=dom, kind='clock'))   # source root
                                clocks.append(dict(inst=names[t], port='en', domain=dom, kind='reset'))
                            else:
                                pn = nodes[src]; br_ = [] if len(pn['outs']) == 1 else [br, br + 1]
                                edges.append(dict(src=[pn['names'][t], 'ck_o'] + br_, dst=[names[t], 'ckf'], bits=1, clock=dom,
                                                  basis='landing ring write clock = last station ck_o'))
                                edges.append(dict(src=[pn['names'][t], 'eb'] + br_, dst=[names[t], 'ea'], bits=1, clock=dom,
                                                  basis='landing write epoch = lane epoch'))
                            clocks.append(dict(inst=names[t], port='ck', domain=dom, kind='clock'))   # SINK regional root
                            clocks.append(dict(inst=names[t], port='rs', domain=dom, kind='reset'))
                            for j_ in range(3):
                                straps.append(dict(inst=names[t], port=f'k{j_}', value=(K_ >> j_) & 1, lo=0, hi=1, master=m,
                                                   reason=f'identity: landing K strap bit {j_} of link {lk} (K {K_}, E {E_}; '
                                                          f'{"land plan" if pe else "NO_E placeholder"})'))
                            if a.land_fault == 'pins':
                                die_pins.append(dict(name=f'{names[t]}__fault', direction='output', bits=1, instance=names[t], port='fault'))
                        else:
                            clocks.append(dict(inst=names[t], port='ck', domain=dom, kind='clock'))
                            clocks.append(dict(inst=names[t], port='rs', domain=dom, kind='reset'))
                        continue
                    rdr = 'WE'
                    if kind == 'old':
                        m, src_f, deps = f'hbfd_rly_{W}_WE', SRC_OLD, DEPS_OLD
                    else:
                        m, src_f, deps = f'hbfd_rly_{W}_WE_fc', SRC_FC, DEPS_FC
                    insts.append(dict(name=names[t], master=m, source=src_f, rtl_deps=deps, params={}, slot=f'd4f_relay_sink:{r["driver"]}->{s_}',
                                      owner='H-DIE relay route / H-NETLIST',
                                      note=f'{"sink-root stage" if kind != "old" else "equal-age pad"} {k + 1}/{stages[s_]} at {s_} lane/tile {t}/{T}; '
                                           + (f'lane row {tag}_k{sinks.index(s_):02d}_{k:02d} {t}/{T} {rdr}; site ({round(xy[0], 1)}, {round(xy[1], 1)}) um'
                                              if a.lane_rows else f'home ({round(xy[0], 1)}, {round(xy[1], 1)}) um')))
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
            if lane and chain:
                sk[s_]['chain_ports'] = cports
                lat = (-(-N_ // 2) + 1 + E_ + (stages[s_] - 1)) if E_ is not None else None
                land_rows.append(dict(link=lk, bus=tag, sink=s_, master=f'hbfd_land{"0" if src is None else ""}_{W}_{ldir}', width=W,
                                      lanes=T, stations=N_, E=E_, K=K_, pads=stages[s_] - 1, latency_edges=lat,
                                      latency_formula='ceil(N/2) + 1 + E + pads edges to the sink pin (+1 = the sink input flop: '
                                                      'contract N/2 + 1 + E + 1)', K_source='land plan' if pe else 'NO_E placeholder',
                                      domain=dom, cls=cls))
        splice.append(dict(bus=tag, driver=di, cls=cls, domain=dom, width=W, tiles=T, bits=n,
                           driver_bits=[[p, k] for p, k, _ in bits], loads=[[list(x) for x in ls] for _, _, ls in bits],
                           nodes=[nodes[i] for i in order], sinks=sk, kind=kind, inter_region=bool(inter)))
        if a.land and kind != 'old':
            lr = {x['sink']: x for x in land_rows if x['bus'] == tag}
            depth_eff = {s_: (lr[s_]['latency_edges'] if s_ in lr else depth_eff[s_]) for s_ in sinks}
        consts.append(dict(bus=tag, driver=r['driver'], cls=cls, domain=dom, bits=n, kind=kind, lanes=T, inter_region=bool(inter),
                           fork=fork, sink_edges=depth_eff))
    eq = collections.defaultdict(int)
    for x in consts:
        if x['cls'] == 'equal_age_pad':
            v_ = [v for v in x['sink_edges'].values() if v is not None]   # --land without E: latency open (NO_E)
            if v_:
                eq[x['domain']] = max(eq[x['domain']], max(v_))
    spec = dict(region='relays_d4f', author='Claude H-NETLIST/D4F-RELAY 1017', basis_commit=f'H-DIE station list {a.stations}',
                instances=insts, clocks=clocks, edges=edges, straps=straps, gaps=[], relay_splice_v2=splice,
                relay_excluded=st.get('not_relayed', {}), notes=__doc__.split('\n\n')[1])
    if a.land:
        spec['die_pins'] = die_pins
        spec['gaps'].append(dict(id='G-D4G-LAND-FAULT', what=f'{len(die_pins)} landing fault outputs on die status pins '
                                 '(<landing>__fault), not yet ORed into the regional fault tree (hbm_fault_1017.py fr_<Q>)',
                                 owner='HBM-LANDING / HBM-FAULT') if a.land_fault == 'pins' else
                         dict(id='G-D4G-LAND-FAULT', what='landing fault outputs left OPEN (diagnostic --land-fault open)'))
    with gzip.open(a.out, 'wt') as f:
        json.dump(spec, f)
    import re as _re
    cat = collections.Counter()
    for m_, v in tiles.items():
        mm = _re.match(r'hbfd_rly_(\d+)_[A-Z]+(_fc)?(_f(\d))?$', m_ or '')
        ml = _re.match(r'hbfd_(lh0|lh|land0|land)_(\d+)_[A-Z]+(_f(\d))?$', m_ or '')
        if ml:
            cat[ml.group(1) + ml.group(2) + (f'_f{ml.group(4)}' if ml.group(4) else '')] += v; continue
        if not mm:
            cat['unknown'] += v; continue
        cat[('fc' if mm.group(2) else 'old') + mm.group(1) + (f'_f{mm.group(4)}' if mm.group(4) else '')] += v
    rep = dict(schema='opentallas.hbm.relays_d4f_report.v1', tile_categories=dict(sorted(cat.items())), reach_um=R, region_source=region_src, buses=len(splice),
               tiles=dict(sorted(tiles.items())), kinds=dict(collections.Counter(x['kind'] for x in consts)),
               fork_buses=sum(1 for x in consts if x['fork']), inter_region_buses=sum(1 for x in consts if x['inter_region']),
               equal_age_max_depth_by_domain=dict(eq), hops_over_reach=hops_over, problems=problems, notes=notes, compiler=consts)
    if a.land:
        rep['landing'] = dict(links=len(land_rows), landing_tiles=sum(x['lanes'] for x in land_rows),
                              by_master=dict(collections.Counter(x['master'] for x in land_rows for _ in range(x['lanes']))),
                              by_width=dict(collections.Counter(str(x['width']) for x in land_rows for _ in range(x['lanes']))),
                              no_E=sum(1 for x in land_rows if x['E'] is None), land_plan=a.land_plan, fault=a.land_fault,
                              rows=land_rows)
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('buses', 'tile_categories', 'kinds', 'fork_buses', 'inter_region_buses', 'equal_age_max_depth_by_domain')}),
          len(hops_over), 'hops over reach,', len(problems), 'problems', problems[:4])


if __name__ == '__main__':
    main()
