#!/usr/bin/env python3
"""Plan a source-bound regional synchronous reset forest from placed LEF pins.

Requires a pre-forest contract, its placed case manifest and the exact consumed
LEFs (including hbfd_rrl_sync/hop). Writes a revision layer only on geometric
PASS. Full rectangle homes are reserved outside all placed outlines; fixed
reset release ages are equalized per (domain, POR) and per bridge source.
Equalization lives INSIDE the leaf: a leaf that needs p extra edges is one
multi-stage delay tile hbfd_rrl_d<p+1> (same outline as the hop), never p
separate pad tiles. Regional roots and leaves are homed only on free cells
reachable from the synchronized POR under the strict bounded-run rule (no
pocket roots that need an overflight longer than the reach budget).
This is geometry and RTL latency evidence, never physical sign-off: rebuild the
case, check actual post-placement pins/reach, clock phases, TT/FF and DRC.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

from reset_forest_geometry import Geometry, GeometryError, md

CB0, CB1 = 14970.0, 18831.0
SRC = 'rtl/hbm_accel/die_glue/hbfd_rrl.sv'
DEPS = ['rtl/lib/ot_rst_relay.sv']


def load(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


def build(c, manifest, views, relay_views=None, reach=405., fanout=2048, zones='d4b', mut_skew=False,
          provisional_delay=False):
    if reach <= 0 or fanout < 1:
        raise GeometryError('reach and fanout must be positive')
    if any(i['master'].startswith('hbfd_rrl_') for i in c['instances'].values()):
        raise GeometryError('input already contains reset forest instances; use pre-forest contract')
    g = Geometry(manifest, views, relay_views, reach, provisional_delay)
    W, H = manifest['die_um']
    tiles, edges, clocks, ports, drop = [], [], [], [], []
    report = dict(schema='opentallas.hbm.reset_forest.v2', reach_um=reach, fanout_cap=fanout,
                  domains={}, geometry_gate='PASS', reach_gate='PASS', physical_signoff='OPEN', native_complete=False,
                  unplaced={}, problems=[],
                  home_basis='lower left, R0, exact consumed LEF outline',
                  clock_requirement='downstream regional clock binding and phase validation required',
                  compiler_requirement='bind age constants after physical clock/phase proof; no runtime scheduling/backpressure',
                  age_reference='ideal common-phase RTL edge model; physical recovery/removal and arrival phases OPEN',
                  homes={}, consumed_lef_sha256=g.hashes)

    def zone(xy):
        x, y = xy
        if zones != 'quadrant' and CB0 <= x <= CB1:
            return 'C'
        return ('N' if y >= H / 2 else 'S') + ('W' if x < (W / 2 if zones == 'quadrant' else CB0) else 'E')

    def centre(points):
        return tuple(sum(p[i] for p in points) / len(points) for i in (0, 1))

    def emit(t, dom, tag, note):
        n = f'rrf_{tag}_{len(tiles) + 1:06d}'
        t['name'] = n
        x, y = t['home']
        tiles.append(dict(name=n, master='hbfd_rrl_' + t['kind'], source=SRC, rtl_deps=DEPS, params={}, slot=None,
                          owner='H-NETLIST reset forest', note=f'{note}; home ({x:.6f}, {y:.6f}) um'))
        clocks.append(dict(inst=n, port='clk', domain=dom, kind='clock'))
        w, h, _ = g.relay[t['kind']]
        report['homes'][n] = dict(x=x, y=y, w=w, h=h, o='R0', m='hbfd_rrl_' + t['kind'])
        return n

    def edge(src, dst, dom):
        edges.append(dict(src=src, dst=dst, bits=1, clock=dom,
                          basis='source-bound regional synchronous reset forest; fixed release age'))

    def wire_chain(prev, chain, dom, tag, note):
        for t in chain:
            n = emit(t, dom, tag, note)
            edge(prev, [n, 'rst_n_in'], dom)
            prev = [n, 'rst_n']
        return prev

    sinks = collections.defaultdict(list)
    seen = set()
    for x in c['clock_resets']:
        if x['kind'] != 'reset' or x['source'][0] != 'hb_ckgen':
            continue
        for bit in range(x['bits']):
            ref = (x['instance'], x['port'], bit, x['bits'])
            if ref[:3] in seen:
                raise GeometryError(f'duplicate reset sink: {ref}')
            seen.add(ref[:3])
            xy = g.pin(*ref)
            sinks[(x['domain'], x['source'][1])].append((ref, xy))
    for (dom, por), S in sorted(sinks.items()):
        source = g.pin('hb_ckgen', por)
        ingress = g.reserve('sync', source, targets=[('rst_n_in', source)])
        distributed_source = g.tile_pin(ingress, 'rst_n')
        comp = g.component(distributed_source)
        groups = collections.defaultdict(list)
        for ref, xy in S:
            groups[zone(xy)].append((ref, xy))
        plans = []
        for z, Z in sorted(groups.items()):
            root = g.reserve('sync', centre([s[1] for s in Z]), max_distance=max(W, H), allowed=comp)
            pre = g.chain(distributed_source, root)
            cells = collections.defaultdict(list)
            for ref, xy in Z:
                cells[(int(xy[0] // (reach / 2)), int(xy[1] // (reach / 2)))].append((ref, xy))
            leaves = []
            for _, cell in sorted(cells.items()):
                pending = [cell[k:k + fanout] for k in range(0, len(cell), fanout)]
                while pending:
                    chunk = pending.pop(0)
                    try:
                        leaf = g.reserve('hop', centre([s[1] for s in chunk]),
                                         targets=[('rst_n', s[1]) for s in chunk], allowed=comp)
                    except GeometryError:
                        if len(chunk) == 1:
                            raise
                        mid = len(chunk) // 2
                        pending[0:0] = [chunk[:mid], chunk[mid:]]
                        continue
                    chain = g.chain(g.tile_pin(root, 'rst_n'), leaf)
                    leaves.append(dict(tile=leaf, chain=chain, sinks=chunk, age=3 + len(pre) + 3 + len(chain) + 1))
            plans.append(dict(zone=z, root=root, pre=pre, leaves=leaves))
        age = max(l['age'] for p in plans for l in p['leaves'])
        ingress_name = emit(ingress, dom, f'{dom}_por', 'local POR synchronization before registered distribution')
        edge(['hb_ckgen', por], [ingress_name, 'rst_n_in'], dom)
        ages = []
        mutated = False
        for plan in plans:
            z, root, pre = plan['zone'], plan['root'], plan['pre']
            tag = f'{dom}_{z}'
            prev = wire_chain([ingress_name, 'rst_n'], pre, dom, tag, 'synchronized POR reach hop')
            rt = emit(root, dom, tag, 'regional root: two sync stages and one relay stage')
            edge(prev, [rt, 'rst_n_in'], dom)
            for leaf in plan['leaves']:
                chain, tile = leaf['chain'], leaf['tile']
                prev = wire_chain([rt, 'rst_n'], chain, dom, tag, 'regional reach hop')
                pads = age - leaf['age']
                if mut_skew and not mutated:
                    pads += 1
                    mutated = True
                tile['kind'] = g.delay_kind(pads + 1)
                lf = emit(tile, dom, tag, f'leaf: {pads + 1} registered stages, {len(leaf["sinks"])} reset pins')
                edge(prev, [lf, 'rst_n_in'], dom)
                for (i, p, b, nb), _ in leaf['sinks']:
                    edge([lf, 'rst_n'], [i, p, b, b + 1] if nb > 1 else [i, p], dom)
                    if b == 0:
                        ports.append([i, p])
                ages.append(leaf['age'] + pads)
        report['domains'][f'{dom}:{por}'] = dict(sinks=len(S), regions=len(plans), age=age,
                                                       actual_leaf_ages=sorted(set(ages)))
    bridges = collections.defaultdict(list)
    for e in c['edges']:
        if e['source'][1] == 'bridge_rst_n':
            if len(e['source']) != 2 or len(e['sink']) != 2 or e['bits'] != 1:
                raise GeometryError('bridge reset must be an unsliced scalar edge')
            bridges[e['source'][0]].append(e['sink'])
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
            leaf['kind'] = g.delay_kind(age - len(chain))
            prev = wire_chain(prev, [leaf], 'stream', 'br_' + src, f'bridge leaf: {age - len(chain)} registered stages')
            edge(prev, dst, 'stream')
            drop.append([src, 'bridge_rst_n', dst[0]])
        report['domains'][f'bridge:{src}'] = dict(sinks=len(dsts), age=age, actual_leaf_ages=[age])
    if mut_skew:
        report['geometry_gate'] = report['reach_gate'] = 'FAIL_MUTANT_RELEASE_AGE'
    # Independent check of emitted actual pin distances, including all pad links.
    byname = {t['name']: t for t in g.reserved.values()}
    def endpoint(ref):
        if ref[0] in byname:
            return g.tile_pin(byname[ref[0]], ref[1])
        return g.pin(ref[0], f'{ref[1]}[{ref[2]}]' if len(ref) > 2 else ref[1])
    lengths = [md(endpoint(e['src']), endpoint(e['dst'])) for e in edges]
    if any(d > reach + 1e-6 for d in lengths):
        raise GeometryError('emitted edge exceeds actual placed pin reach')
    report.update(tiles=len(tiles), reset_ports=len(ports), max_actual_pin_hop_um=max(lengths, default=0),
                  tiles_by_master=dict(collections.Counter(t['master'] for t in tiles)))
    if g.provisional_used:
        report['geometry_gate'] = 'PROVISIONAL_DELAY_LEF'
        report['provisional_delay_masters'] = sorted('hbfd_rrl_' + k for k in g.provisional_used)
        report['provisional_note'] = ('delay-leaf masters planned on the hop LEF geometry (their gated LEFs are not in '
                                      '--relay-views yet); re-run strictly with the gated LEFs before any splice')
    spec = dict(region='reset_forest', author='H-NETLIST source-bound reset planner',
                basis_commit='regional synchronous reset owner standard 10-16',
                instances=tiles, edges=edges, clocks=clocks, straps=[], gaps=[], drop_edges=drop,
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
    ap.add_argument('--provisional-delay', action='store_true',
                    help='plan missing hbfd_rrl_d<N> LEFs on the hop geometry (report PROVISIONAL_DELAY_LEF)')
    ap.add_argument('--diag', action='store_true', help='compatibility: failures still refuse layer emission and exit 3')
    a = ap.parse_args()
    try:
        spec, rep = build(load(a.contract), load(a.manifest), a.views, a.relay_views,
                          a.reach, a.fanout, a.zones, a.mut_skew, a.provisional_delay)
    except GeometryError as e:
        a.report.write_text(json.dumps(dict(schema='opentallas.hbm.reset_forest.v2', geometry_gate='FAIL', reach_gate='FAIL',
                                           physical_signoff='OPEN', problems=[str(e)]), indent=2) + '\n')
        print(f'reset forest FAIL: {e}')
        raise SystemExit(3)
    rep['input_sha256'] = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (a.contract, a.manifest, Path(__file__), Path(__file__).with_name('reset_forest_geometry.py'),
                                     Path(__file__).resolve().parents[2] / SRC,
                                     Path(__file__).resolve().parents[2] / DEPS[0])}
    a.out.write_text(json.dumps(spec) + '\n')
    rep['layer_sha256'] = hashlib.sha256(a.out.read_bytes()).hexdigest()
    a.report.write_text(json.dumps(rep, indent=2) + '\n')
    print(json.dumps({k: rep[k] for k in ('tiles', 'reset_ports', 'max_actual_pin_hop_um', 'geometry_gate')}))


if __name__ == '__main__':
    main()
