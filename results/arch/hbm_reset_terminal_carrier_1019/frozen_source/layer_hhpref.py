#!/usr/bin/env python3
"""Plan a source-bound regional synchronous reset forest from placed LEF pins.

Requires a pre-forest contract, its placed case manifest and the exact consumed
LEFs (including hbfd_rrl_sync/hop). Writes a revision layer only on geometric
PASS. Full rectangle homes are reserved outside all placed outlines; fixed
reset release ages are equalized per (domain, POR) and per bridge source.
This is geometry and RTL latency evidence, never physical sign-off: rebuild the
case, check actual post-placement pins/reach, clock phases, TT/FF and DRC.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

import os
import sys
import time

from reset_forest_geometry import Geometry, GeometryError, md
import reset_rows

T0 = time.time()


def log(*a):
    if os.environ.get('OT_FOREST_LOG'):
        print(f'[{time.time() - T0:8.1f}s]', *a, file=sys.stderr, flush=True)

CB0, CB1 = 14970.0, 18831.0
SRC = 'rtl/hbm_accel/die_glue/hbfd_rrl.sv'
DEPS = ['rtl/lib/ot_rst_relay.sv']
# LH-RSTHOP 10-19: reach hops hosted in lane relay stations (hbfd_rly_<W>_<flow>_rf / _rrf, one rfi -> rfo flop)
RF_SRC = 'rtl/hbm_accel/die_glue/hbfd_rly_rf_masters.sv'
RF_DEPS = ['rtl/hbm_accel/die_glue/ot_hbm_rly_rf.sv', 'rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv',
           'rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']


def load(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


MAX_PAD = 128  # rtl/hbm_accel/die_glue/hbfd_rrl.sv defines hbfd_rrl_pad2 .. hbfd_rrl_pad128 (405 um hops on a 31.8 mm die: ages ~90)


def build(c, manifest, views, relay_views=None, reach=405., fanout=2048, zones='d4b', mut_skew=False, max_root_tries=40,
          survey=None, relay_rows=False, overfly=None, host_hops=None):
    if reach <= 0 or fanout < 1:
        raise GeometryError('reach and fanout must be positive')
    if any(i['master'].startswith('hbfd_rrl_') for i in c['instances'].values()):
        raise GeometryError('input already contains reset forest instances; use pre-forest contract')
    g = Geometry(manifest, views, relay_views, reach, overfly=overfly)
    W, H = manifest['die_um']
    host_use = {}
    if host_hops:
        # LH-RSTHOP (coordinator 0jp A, structural H.RST answer): every placed lane relay station (hbfd_rly_<W>_<flow>,
        # 21.6-64.8 um, at <= 405 um pitch along every channel) may host ONE forest reach hop on its own regional clock.
        ckdom = {x['instance']: x['domain'] for x in c['clock_resets'] if x['kind'] == 'clock' and x['port'] == 'ck'}
        hosts, skipped = [], collections.Counter()
        for n, v in sorted(c['instances'].items()):
            m = reset_rows.BASE.match(v['master'])
            if not m:
                continue
            if n not in g.pl or n not in ckdom:
                skipped['unplaced_or_no_ck'] += 1
                continue
            wb, pv = int(m.group(1)), g.pl[n]
            try:
                rfi, rfo = g.pin(n, 'i', wb // 2, wb), g.pin(n, 'o', wb // 2, wb)
            except GeometryError:
                skipped['pin'] += 1
                continue
            hosts.append(dict(inst=n, dom=ckdom[n], rfi=rfi, rfo=rfo, home=(pv['x'], pv['y']), w=pv['w'], h=pv['h']))
        g.set_hosts(hosts, host_hops)
        log('host stations', len(hosts), dict(collections.Counter(h['dom'] for h in hosts)), dict(skipped))
    tiles, edges, clocks, ports, drop = [], [], [], [], []
    report = dict(schema='opentallas.hbm.reset_forest.v2', reach_um=reach, fanout_cap=fanout,
                  domains={}, geometry_gate='PASS', reach_gate='PASS', physical_signoff='OPEN', native_complete=False,
                  unplaced={}, problems=[],
                  home_basis='lower left, R0, exact consumed LEF outline',
                  clock_requirement='downstream regional clock binding and phase validation required',
                  compiler_requirement='bind age constants after physical clock/phase proof; no runtime scheduling/backpressure',
                  age_reference='ideal common-phase RTL edge model; physical recovery/removal and arrival phases OPEN',
                  homes={}, root_alternatives=[], consumed_lef_sha256=g.hashes)
    if host_hops:
        report['host_hops'] = dict(mode=host_hops, stations=len(g.hosts),
                                   stations_by_domain=dict(collections.Counter(h['dom'] for h in g.hosts)))

    def zone(xy):
        x, y = xy
        if zones != 'quadrant' and CB0 <= x <= CB1:
            # FOREST2: the centre column spans the full die height (~31.8 mm); one root at its middle gave 16 mm
            # root->leaf chains (44 release stages on GEN2a).  Split it N/S like the quadrants.
            return 'C' + ('N' if y >= H / 2 else 'S')
        return ('N' if y >= H / 2 else 'S') + ('W' if x < (W / 2 if zones == 'quadrant' else CB0) else 'E')

    # HBM-RSTROW (coordinator 0jp, Proposal A): relay rows carry their own reset (reset_rows.py).  Only row heads are
    # forest sinks; their leaves release at domain age + off (off <= 0) so every station releases by D + 1 + depth.
    rows = reset_rows.plan_rows(c) if relay_rows else None
    offmap, feeds = {}, {}
    if rows:
        for h, o in rows['heads'].items():
            offmap[(h, 'rs')] = o
        report['relay_rows'] = rows['stats']

    def centre(points):
        return tuple(sum(p[i] for p in points) / len(points) for i in (0, 1))

    def set_stages(t, n):
        if n < 1 or n > MAX_PAD:
            raise GeometryError(f'leaf needs {n} release stages; hbfd_rrl_pad<N> exists for N <= {MAX_PAD}')
        if n > 1:
            t['kind'] = f'pad{n}'

    def emit(t, dom, tag, note):
        if t['kind'] == 'host':   # LH-RSTHOP: the station itself is the stage (remastered _rf/_rrf below)
            host_use[t['inst']] = dom
            t['name'] = t['inst']
            return t['inst']
        n = f'rrf_{tag}_{len(tiles) + 1:06d}'
        t['name'] = n
        x, y = t['home']
        tiles.append(dict(name=n, master='hbfd_rrl_' + t['kind'], source=SRC, rtl_deps=DEPS, params={}, slot=None,
                          owner='H-NETLIST reset forest', note=f'{note}; home ({x:.6f}, {y:.6f}) um'))
        clocks.append(dict(inst=n, port='clk', domain=dom, kind='clock'))
        w, h, _ = g.relay_lef(t['kind'])
        report['homes'][n] = dict(x=x, y=y, w=w, h=h, o='R0', m='hbfd_rrl_' + t['kind'])
        return n

    def edge(src, dst, dom):
        if src[0] in host_use and src[1] == 'rst_n':
            src = [src[0], 'rfo']
        if dst[0] in host_use and dst[1] == 'rst_n_in':
            dst = [dst[0], 'rfi']
        edges.append(dict(src=src, dst=dst, bits=1, clock=dom,
                          basis='source-bound regional synchronous reset forest; fixed release age'))

    def wire_chain(prev, chain, dom, tag, note):
        for t in chain:
            n = emit(t, dom, tag, note)
            edge(prev, [n, 'rst_n_in'], dom)
            prev = [n, 'rst_n']
        return prev

    def plan_region(z, Z, site, pnodes, allowed):
        root = g.reserve('sync', site, max_distance=reach, allowed=allowed)
        # FOREST2: the POR trunk is a tree too: each region's root chains from the nearest node of the domain trunk
        # (ingress or an earlier region's POR hop), so the crowded ckgen neighbourhood is left once per domain.
        rin = g.tile_pin(root, 'rst_n_in')
        last = None
        for psrc, page in sorted(pnodes, key=lambda n: (n[1] + md(g.tile_pin(n[0], 'rst_n'), rin) / g.budget,
                                                          md(g.tile_pin(n[0], 'rst_n'), rin)))[:4]:
            snap = g.snapshot()
            try:
                pre = g.chain(g.tile_pin(psrc, 'rst_n'), root, src_host=psrc['kind'] == 'host')
                break
            except GeometryError as e:
                g.restore(snap)
                last = e
        else:
            raise last
        new_pnodes = [(t, page + i + 1) for i, t in enumerate(pre)]
        cells = collections.defaultdict(list)
        for ref, xy in Z:   # one leaf drives sinks of ONE release target (offset class)
            cells[(int(xy[0] // (reach / 2)), int(xy[1] // (reach / 2)), offmap.get(ref[:2], 0))].append((ref, xy))
        placed = []
        for _, cell in sorted(cells.items()):
            pending = [cell[k:k + fanout] for k in range(0, len(cell), fanout)]
            while pending:
                chunk = pending.pop(0)
                try:
                    leaf = g.reserve('hop', centre([s[1] for s in chunk]),
                                     targets=[('rst_n', s[1]) for s in chunk], allowed=allowed)
                except GeometryError:
                    if len(chunk) == 1 and rows and chunk[0][0][:2] in offmap and chunk[0][0][0] in rows['alts']:
                        # HBM-RSTROW: an unhomable row head (row starts in a narrow channel) -> feed the row at a deeper
                        # station of its heaviest branch; the stations above it take the reset backwards (rso -> rs)
                        h, alt = chunk[0][0][0], None
                        for f in rows['alts'][h]:
                            try:
                                fxy = g.pin(f, 'rs')
                                alt = g.reserve('hop', fxy, targets=[('rst_n', fxy)], allowed=allowed)
                            except GeometryError:
                                continue
                            feeds[h] = f
                            offmap[(f, 'rs')] = reset_rows.feed_offset(rows, f)
                            placed.append((alt, [((f, 'rs', 0, 1), fxy)]))
                            break
                        if alt is not None:
                            continue
                    if len(chunk) == 1:
                        if survey is not None:   # --survey: record the unhomable sink, keep planning (layer refused)
                            survey.append(dict(pin=f'{chunk[0][0][0]}.{chunk[0][0][1]}', xy=[round(v, 1) for v in chunk[0][1]],
                                               zone=z, reason='no reachable leaf home within reach'))
                            continue
                        raise
                    mid = len(chunk) // 2
                    pending[0:0] = [chunk[:mid], chunk[mid:]]
                    continue
                placed.append((leaf, chunk))
        # FOREST2: a TREE, not a star of root->leaf chains: leaves nearest the root first, each chained from the nearest
        # existing node (root or an earlier reach hop), so trunks are shared (GEN2a stream C: 30-70 s per 16 mm star
        # chain, hundreds of leaves).  Ages differ per leaf and are equalized inside the leaf (pad<N>).
        rp = g.tile_pin(root, 'rst_n')
        nodes = [(root, page + len(pre) + 3)]
        leaves = []
        for leaf, chunk in sorted(placed, key=lambda t: md(rp, g.tile_pin(t[0], 'rst_n_in'))):
            end = g.tile_pin(leaf, 'rst_n_in')
            # shallowest arrival first: node age + estimated hops (md / hop budget); shares trunks without the deep
            # winding branches nearest-node chaining built (GEN2a serial: 65 release stages)
            order = sorted(nodes, key=lambda n: (n[1] + md(g.tile_pin(n[0], 'rst_n'), end) / g.budget,
                                                 md(g.tile_pin(n[0], 'rst_n'), end)))
            tries = order[:4] + ([nodes[0]] if nodes[0] not in order[:4] else [])
            last = None
            for src, src_age in tries:   # nearest nodes first, the root last; reach budget unchanged
                snap = g.snapshot()
                try:
                    chain = g.chain(g.tile_pin(src, 'rst_n'), leaf, src_host=src['kind'] == 'host')
                    break
                except GeometryError as e:
                    g.restore(snap)   # a failed chain may have reserved part of its hops
                    last = e
            else:
                raise last
            nodes += [(t, src_age + i + 1) for i, t in enumerate(chain)]
            leaves.append(dict(tile=leaf, src=src, chain=chain, sinks=chunk, age=src_age + len(chain) + 1,
                               off=offmap.get(chunk[0][0][:2], 0)))
        return dict(zone=z, root=root, pre=pre, psrc=psrc, leaves=leaves, new_pnodes=new_pnodes)

    sinks = collections.defaultdict(list)
    head_age, dom_age = {}, {}
    seen = set()
    for x in c['clock_resets']:
        if x['kind'] != 'reset' or x['source'][0] != 'hb_ckgen':
            continue
        if rows and x['port'] == 'rs' and x['instance'] in rows['parent']:
            continue   # chained relay station: rs <- parent rso (emitted below)
        for bit in range(x['bits']):
            ref = (x['instance'], x['port'], bit, x['bits'])
            if ref[:3] in seen:
                raise GeometryError(f'duplicate reset sink: {ref}')
            seen.add(ref[:3])
            xy = g.pin(*ref)
            sinks[(x['domain'], x['source'][1])].append((ref, xy))
    for (dom, por), S in sorted(sinks.items()):
        g.host_dom = dom
        source = g.pin('hb_ckgen', por)
        ingress = g.reserve('sync', source, targets=[('rst_n_in', source)])
        distributed_source = g.tile_pin(ingress, 'rst_n')
        log('domain', dom, por, 'sinks', len(S), 'flood start')
        allowed = g.reach_mask(distributed_source)
        pnodes = [(ingress, 3)]
        log('flood done, reachable cells', sum(allowed))
        groups = collections.defaultdict(list)
        for ref, xy in S:
            groups[zone(xy)].append((ref, xy))
        plans = []
        for z, Z in sorted(groups.items()):
            plan, errs = None, []
            # Regional-root home: try the sink centroid, then alternative homes around it, and keep the FIRST site whose
            # whole region (POR hop chain + every leaf chain) routes inside the fixed reach budget.  A pocket that is
            # walled off within the budget is skipped; the budget is never relaxed.
            for k, site in enumerate(g.root_sites(centre([s[1] for s in Z]))[:max_root_tries]):
                snap = g.snapshot()
                log('  region', z, 'try', k, 'site', [round(v) for v in site])
                try:
                    plan = plan_region(z, Z, site, pnodes, allowed)
                    plan['root_try'] = k
                    break
                except GeometryError as e:
                    g.restore(snap)
                    errs.append(f'{k}@({site[0]:.0f},{site[1]:.0f}): {e}')
                    log('    rejected:', errs[-1])
            if plan is None:
                raise GeometryError(f'{dom} {z}: no regional root home routes within reach after {len(errs)} sites; '
                                    f'first {errs[0]}; last {errs[-1]}')
            if plan['root_try']:
                report['root_alternatives'].append(dict(domain=dom, por=por, zone=z, try_index=plan['root_try'],
                                                        rejected=errs))
            pnodes += plan['new_pnodes']
            plans.append(plan)
        age = max(l['age'] - l['off'] for p in plans for l in p['leaves'])
        log('domain', dom, 'release age', age, 'min leaf age', min(l['age'] for p in plans for l in p['leaves']),
            'leaves', sum(len(p['leaves']) for p in plans))
        ingress_name = emit(ingress, dom, f'{dom}_por', 'local POR synchronization before registered distribution')
        edge(['hb_ckgen', por], [ingress_name, 'rst_n_in'], dom)
        ages = []
        mutated = False
        for plan in plans:
            z, root, pre = plan['zone'], plan['root'], plan['pre']
            tag = f'{dom}_{z}'
            prev = wire_chain([plan['psrc']['name'], 'rst_n'], pre, dom, tag, 'synchronized POR reach hop')
            rt = emit(root, dom, tag, 'regional root: two sync stages and one relay stage')
            edge(prev, [rt, 'rst_n_in'], dom)
            for leaf in plan['leaves']:
                chain, tile = leaf['chain'], leaf['tile']
                prev = wire_chain([leaf['src']['name'], 'rst_n'], chain, dom, tag, 'regional reach hop')
                pads = age + leaf['off'] - leaf['age']
                if mut_skew and not mutated:
                    pads += 1
                    mutated = True
                # Equal-age padding lives INSIDE the leaf tile (hbfd_rrl_pad<N>: N registered stages, same footprint
                # and pins as hbfd_rrl_hop): no extra pad homes to find in crowded strips.
                set_stages(tile, 1 + pads)
                lf = emit(tile, dom, tag, f'leaf: {len(leaf["sinks"])} reset pins, {1 + pads} release stages')
                edge(prev, [lf, 'rst_n_in'], dom)
                for (i, p, b, nb), _ in leaf['sinks']:
                    edge([lf, 'rst_n'], [i, p, b, b + 1] if nb > 1 else [i, p], dom)
                    if b == 0:
                        ports.append([i, p])
                ages.append(leaf['age'] + pads)
                for (i, p, b, nb), _ in leaf['sinks']:
                    head_age[i] = leaf['age'] + pads
        dom_age[(dom, por)] = age
        report['domains'][f'{dom}:{por}'] = dict(sinks=len(S), regions=len(plans), age=age,
                                                       actual_leaf_ages=sorted(set(ages)))
    bridges = collections.defaultdict(list)
    for e in c['edges']:
        if e['source'][1] == 'bridge_rst_n':
            if len(e['source']) != 2 or len(e['sink']) != 2 or e['bits'] != 1:
                raise GeometryError('bridge reset must be an unsliced scalar edge')
            bridges[e['source'][0]].append(e['sink'])
    g.host_dom = 'stream'
    for src, dsts in sorted(bridges.items()):
        source = g.pin(src, 'bridge_rst_n')
        paths = []
        for dst in dsts:
            dp = g.pin(*dst)
            leaf = g.reserve('hop', dp, targets=[('rst_n', dp)])
            chain = g.chain(source, leaf)
            paths.append((dst, leaf, chain))
        age = max(len(p[2]) + 1 for p in paths)
        for dst, leaf, chain in paths:
            prev = wire_chain([src, 'bridge_rst_n'], chain, 'stream', 'br_' + src, 'bridge reach hop')
            set_stages(leaf, age - len(chain))
            prev = wire_chain(prev, [leaf], 'stream', 'br_' + src, f'bridge leaf, {age - len(chain)} release stages')
            edge(prev, dst, 'stream')
            drop.append([src, 'bridge_rst_n', dst[0]])
        report['domains'][f'bridge:{src}'] = dict(sinks=len(dsts), age=age, actual_leaf_ages=[age])
    remaster = []
    if rows:
        por_of = {x['instance']: (x['domain'], x['source'][1]) for x in c['clock_resets']
                  if x['kind'] == 'reset' and x['port'] == 'rs' and x['instance'] in rows['depth']}
        fin = reset_rows.finalize(rows, feeds)
        missing = [f for f in fin['feeds'] if f not in head_age]
        if missing and not survey:
            raise GeometryError(f'{len(missing)} relay row feeds got no forest leaf, e.g. {missing[:5]}')
        if not missing:
            st_age, bad = reset_rows.check_release(rows, fin, head_age, {h: dom_age[por_of[h]] for h in rows['heads']})
            if bad:
                raise GeometryError(f'relay row release check: {len(bad)} stations release after D + 1 + depth, e.g. {bad[:5]}')
            report['relay_rows']['max_station_rs_age'] = max(st_age.values(), default=0)
        report['relay_rows'].update(fed_below_head=len(feeds), feeds_below_head={h: f for h, f in sorted(feeds.items())},
                                    remastered=len(fin['remaster']),
                                    rr_masters=dict(collections.Counter(x['master'] for x in fin['remaster'])))
        hops = []
        for r, p in sorted(fin['rparent'].items()):
            dom = por_of[r][0]
            w = int(reset_rows.BASE.match(c['instances'][p]['master']).group(1))
            # rso sits on the o face of the _rr master (kit HBM-RSTROW-RTL); the placed base LEF has no rso yet: the
            # middle o pin stands for it here, die_case_v16's reset gate checks the actual _rr LEF pins.
            hops.append(md(g.pin(p, 'o', w // 2, w), g.pin(r, 'rs')))
            edges.append(dict(src=[p, 'rso'], dst=[r, 'rs'], bits=1, clock=dom,
                              basis='HBM-RSTROW relay-row reset: parent rso -> station rs (1 release edge a station)'))
            ports.append([r, 'rs'])
        report['relay_rows'].update(max_row_hop_um=max(hops, default=0), row_hops_over_reach=sum(h > reach for h in hops))
        if any(h > reach for h in hops):
            raise GeometryError(f'{sum(h > reach for h in hops)} relay-row reset hops exceed the reach')
        remaster = fin['remaster']
    if host_use:
        # LH-RSTHOP: hosting stations -> _rf (base) / _rrf (already a row-reset _rr driver); rfi is the one added input,
        # driven by the forest edge (d4g_relay_splice checks it)
        byinst = {x['inst']: x for x in remaster}
        for n, dom in sorted(host_use.items()):
            x = byinst.get(n)
            if x is None:
                old = c['instances'][n]['master']
                x = dict(inst=n, old=old, master=old + '_rf')
                remaster.append(x)
            else:
                x['master'] = x['master'] + 'f'
            x.update(source=RF_SRC, rtl_deps=list(RF_DEPS), added_inputs=['rfi'])
        report['host_hops'].update(hosted=len(host_use), hosted_by_domain=dict(collections.Counter(host_use.values())),
                                   masters=dict(collections.Counter(x['master'] for x in remaster
                                                                    if x['inst'] in host_use)))
    if survey:
        raise GeometryError(f'{len(survey)} reset sinks have no reachable leaf home (survey: see report unhomable)')
    if mut_skew:
        report['geometry_gate'] = report['reach_gate'] = 'FAIL_MUTANT_RELEASE_AGE'
    # Independent check of emitted actual pin distances, including all pad links.
    byname = {t['name']: t for t in g.reserved.values()}
    def endpoint(ref):
        if ref[0] in byname:
            return g.tile_pin(byname[ref[0]], ref[1])
        return g.pin(ref[0], f'{ref[1]}[{ref[2]}]' if len(ref) > 2 else ref[1])
    lengths = [md(endpoint(e['src']), endpoint(e['dst'])) for e in edges if e['src'][1] != 'rso']
    if any(d > reach + 1e-6 for d in lengths):
        raise GeometryError('emitted edge exceeds actual placed pin reach')
    report.update(tiles=len(tiles), reset_ports=len(ports), max_actual_pin_hop_um=max(lengths, default=0),
                  tiles_by_master=dict(collections.Counter(t['master'] for t in tiles)))
    spec = dict(region='reset_forest', author='H-NETLIST source-bound reset planner',
                basis_commit='regional synchronous reset owner standard 10-16',
                instances=tiles, edges=edges, clocks=clocks, straps=[], gaps=[], drop_edges=drop, remaster=remaster,
                reset_forest_ports=ports, notes=__doc__)
    return spec, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('contract', 'manifest', 'out', 'report', 'views'):
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--relay-views', type=Path)
    ap.add_argument('--reach', type=float, default=405.)
    ap.add_argument('--fanout', type=int, default=2048)
    ap.add_argument('--zones', choices=('d4b', 'quadrant'), default='d4b')
    ap.add_argument('--mut-skew', action='store_true', help='emit an explicitly failing release-age bench mutant')
    ap.add_argument('--survey', action='store_true', help='plan around unhomable sinks and list them all (still no layer)')
    ap.add_argument('--relay-rows', action='store_true', help='HBM-RSTROW: relay rows carry their reset; heads only')
    ap.add_argument('--diag', action='store_true', help='compatibility: failures still refuse layer emission and exit 3')
    ap.add_argument('--max-root-tries', type=int, default=40,
                    help='LH-GEN2CD 10-19: regional-root alternative sites tried (rings 0..3240 um, 8 per ring = 57 sites); '
                         'the reach budget of every route is unchanged')
    ap.add_argument('--overfly-masters', default=None,
                    help='LH-GEN2CD 10-19: regex of placed masters (<= 64.8 um tiles, e.g. lane-row relays) that reset wires overfly '
                         '(routing budget) while still blocking homes; default none')
    ap.add_argument('--host-hops', choices=('prefer', 'fallback'), default=None,
                    help='LH-RSTHOP 10-19: forest reach hops hosted in placed lane relay stations (remastered '
                         'hbfd_rly_*_rf/_rrf, one rfi->rfo flop on the station clock); default off')
    a = ap.parse_args()
    try:
        survey = [] if a.survey else None
        spec, rep = build(load(a.contract), load(a.manifest), a.views, a.relay_views,
                          a.reach, a.fanout, a.zones, a.mut_skew, max_root_tries=a.max_root_tries, survey=survey,
                          relay_rows=a.relay_rows, overfly=a.overfly_masters, host_hops=a.host_hops)
    except GeometryError as e:
        a.report.write_text(json.dumps(dict(schema='opentallas.hbm.reset_forest.v2', geometry_gate='FAIL', reach_gate='FAIL',
                                           physical_signoff='OPEN', problems=[str(e)], unhomable=survey or []), indent=2) + '\n')
        print(f'reset forest FAIL: {e}')
        raise SystemExit(3)
    rep['input_sha256'] = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (a.contract, a.manifest, Path(__file__), Path(__file__).with_name('reset_forest_geometry.py'), Path(__file__).with_name('reset_rows.py'),
                                     Path(__file__).resolve().parents[2] / SRC,
                                     Path(__file__).resolve().parents[2] / DEPS[0])}
    if a.host_hops:
        for q in [RF_SRC] + RF_DEPS[:1]:
            p = Path(__file__).resolve().parents[2] / q
            rep['input_sha256'][str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    a.out.write_text(json.dumps(spec) + '\n')
    rep['layer_sha256'] = hashlib.sha256(a.out.read_bytes()).hexdigest()
    a.report.write_text(json.dumps(rep, indent=2) + '\n')
    print(json.dumps({k: rep[k] for k in ('tiles', 'reset_ports', 'max_actual_pin_hop_um', 'geometry_gate')}))


if __name__ == '__main__':
    main()
