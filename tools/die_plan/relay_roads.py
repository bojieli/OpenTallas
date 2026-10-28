#!/usr/bin/env python3
"""Compile explicit road-controlled cell sites with exact non-PG connectivity.

The owner supplies legal sites for FFs AND every repair buffer on each road.
This tool does not move clocks, invent stages, or change the netlist.  Re-run
against a fresh graph after repair: an inserted buffer invalidates the old map.
Runtime relay_roads.tcl checks row legality, macro halos, occupancy and identities.
"""
import argparse
import json
from pathlib import Path


class RoadError(ValueError):
    pass


def trace_roads(graph, roads):
    """Resolve each exact source->sink road through actual SIGNAL BUF/INV/HB cells."""
    cells, nets = graph['cells'], graph['nets']
    pin_net = {}
    for net, rec in nets.items():
        for p in rec['pins']:
            if p['pin'] in pin_net and pin_net[p['pin']] != net:
                raise RoadError(f"pin on multiple nets: {p['pin']}")
            pin_net[p['pin']] = net
    traces = []
    for road in roads:
        source, sink = road['source_pin'], road['sink_pin']
        xy = road['polyline_um']
        if len(xy) < 2 or any(a[0] != b[0] and a[1] != b[1] for a, b in zip(xy, xy[1:])):
            raise RoadError(f'non-Manhattan road: {source}->{sink}')
        current, chain, seen = sink, [], set()
        while True:
            if current not in pin_net:
                raise RoadError(f'missing endpoint: {current}')
            net = pin_net[current]
            if any(p["pin"] == current and p["sig_type"] != "SIGNAL" for p in nets[net]["pins"]):
                raise RoadError(f"non-data endpoint: {current}")
            if net in seen:
                raise RoadError(f'buffer loop: {sink}')
            seen.add(net)
            rec = nets[net]
            if rec['sig_type'] != 'SIGNAL':
                raise RoadError(f'non-data road: {net}')
            drivers = [p for p in rec['pins'] if p['direction'] == 'OUTPUT']
            if len(drivers) != 1:
                raise RoadError(f'expected one driver: {net}')
            driver = drivers[0]
            if driver['sig_type'] != 'SIGNAL':
                raise RoadError(f'clock/control pin on road: {driver["pin"]}')
            if driver['pin'] == source:
                break
            name = driver['pin'].rsplit('/', 1)[0]
            cell = cells.get(name)
            if not cell or not cell['master'].startswith(('BUF', 'INV', 'HB')):
                raise RoadError(f'non-buffer predecessor: {driver["pin"]}')
            inputs = [p for p, r in cell['pins'].items() if r['direction'] == 'INPUT']
            outputs = [p for p, r in cell['pins'].items() if r['direction'] == 'OUTPUT']
            if len(inputs) != 1 or len(outputs) != 1:
                raise RoadError(f'non-unary buffer: {name}')
            chain.append(name)
            current = name + '/' + inputs[0]
        traces.append({**road, 'buffers': list(reversed(chain))})
    return traces


def compile_sites(graph, roads, sites, dbu=1000, halo_um=8.64):
    if dbu <= 0 or halo_um < 8.64:
        raise RoadError("invalid DBU or halo below 8.64um")
    traces = trace_roads(graph, roads)
    needed = {n for r in traces for n in r['buffers']}
    missing = needed - sites.keys()
    if missing:
        raise RoadError(f'{len(missing)} road buffers lack explicit legal sites: {sorted(missing)[:5]}')
    # Every controlled FF must actually be an endpoint of a reviewed road.
    endpoints = {r[k].rsplit('/', 1)[0] for r in roads for k in ('source_pin', 'sink_pin')}
    if not sites or any(n not in needed | endpoints for n in sites):
        raise RoadError('unreviewed/empty site map')
    lines = ['DBU\t' + str(dbu)]
    for name, site in sorted(sites.items()):
        cell = graph['cells'].get(name)
        if cell is None:
            raise RoadError(f'cell absent from snapshot: {name}')
        master = cell['master']
        if 'DFF' not in master and not master.startswith(('BUF', 'INV', 'HB')):
            raise RoadError(f'unsupported cell: {name}')
        x, y = site['origin_um']
        vals = [name, master, str(round(x * dbu)), str(round(y * dbu)), site['orient'], str(round(halo_um * dbu))]
        if any('\t' in v or '\n' in v for v in vals):
            raise RoadError('invalid TSV identifier')
        lines.append('CELL\t' + '\t'.join(vals))
        for pin, info in sorted(cell['pins'].items()):
            if info.get('sig_type') in ('POWER', 'GROUND'):
                continue
            fields = ["PIN", name, pin, info.get("net") or "-"]
            if any("\t" in v or "\n" in v for v in fields):
                raise RoadError("invalid TSV pin/net identifier")
            lines.append("\t".join(fields))
    return '\n'.join(lines) + '\n', traces


def allocate_buffer_sites(graph, traces, row_sites, flop_sites, corridor_um, move_flops=False, flop_radii=None):
    """Place existing road buffers in legal rows near EVERY branch they drive.

    This is a pre-GPL placement proposal. Existing movable cells are not treated
    as immutable obstacles; real fixed cells/macro halos must be in row_sites.
    The caller prices the actual resulting pin-to-pin legs and reviews the
    complete image before any physical continuation. No extra buffers/stages.
    """
    import copy
    from core_plan_to_infra import SiteMap
    if corridor_um <= 0:
        raise RoadError('owner-reviewed positive road corridor required')

    def distance(x, y, road):
        return min(abs(x - min(max(x, min(a[0], b[0])), max(a[0], b[0]))) +
                   abs(y - min(max(y, min(a[1], b[1])), max(a[1], b[1])))
                   for a, b in zip(road, road[1:]))

    def point(road, fraction):
        lengths = [abs(a[0]-b[0])+abs(a[1]-b[1]) for a, b in zip(road, road[1:])]
        left = sum(lengths) * fraction
        for a, b, length in zip(road, road[1:], lengths):
            if left <= length and length:
                return [a[k] + (b[k]-a[k])*left/length for k in (0, 1)]
            left -= length
        return road[-1]

    rows = copy.deepcopy(row_sites)
    # M5 stripe-center avoidance is for clock stacks. Ordinary data FF/BUF
    # placement must respect body obstacles, not invent a PG upper-metal gate.
    rows['pg'] = {**rows.get('pg', {}), 'M5': []}

    class RoadSites(SiteMap):
        roads = []
        width = 0
        def __init__(self, original):
            # OpenDB rows are cut into fragments around macros/taps. Group by
            # physical y, not fragment index: separate occupancy arrays for the
            # same physical row would permit duplicate placements.
            original = copy.deepcopy(original)
            sw = original['row0']['site_w']
            x0 = min(r[0] for r in original['rows'])
            by_y = {}
            for x, y, orient, count in original['rows']:
                start = round((x-x0)/sw)
                if abs(x0+start*sw-x) > 1e-6:
                    raise RoadError('row fragments do not share a site grid')
                item = by_y.setdefault(y, {'orient': orient, 'ranges': []})
                if item['orient'] != orient:
                    raise RoadError('row fragments disagree on orientation')
                item['ranges'].append((start, start+count))
            ns = max(b for v in by_y.values() for a,b in v['ranges'])
            original['rows'] = [(x0,y,v['orient'],ns) for y,v in sorted(by_y.items())]
            original['row0']['nsites'] = ns
            self.allowed = [v['ranges'] for y,v in sorted(by_y.items())]
            super().__init__(original)
        def free(self, k, s, n):
            if not super().free(k, s, n):
                return False
            if not any(a <= s and s+n <= b for a,b in self.allowed[k]):
                return False
            x = self.rows[k][0] + (s+n/2)*self.sw
            y = self.rows[k][1] + self.sh/2
            return all(distance(x, y, road) <= corridor_um + 1e-9 for road in self.roads)

    sm = RoadSites(rows)
    result = {}
    def uses_of(rows_):
        uses = {}
        for trace in rows_:
            for j,name in enumerate(trace['buffers']):
                uses.setdefault(name,[]).append((trace['polyline_um'],(j+1)/(len(trace['buffers'])+1)))
        return uses
    all_uses = uses_of(traces)
    def place_buffer(name, uses_):
        sm.roads = [r for r, _ in uses_]
        targets = [point(r, f) for r, f in uses_]
        # Select a target on the common corridor. Source/common branch vertices
        # are included so divergent shared roads cannot silently be averaged.
        candidates = targets + [p for r, _ in uses_ for p in r]
        valid = [p for p in candidates if all(distance(*p, r) <= corridor_um for r, _ in uses_)]
        if not valid:
            raise RoadError(f'no common branch corridor for existing buffer: {name}')
        target = min(valid, key=lambda p: sum(abs(p[0]-t[0])+abs(p[1]-t[1]) for t in targets))
        master = graph['cells'][name]['master']
        radius = max(sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(r,r[1:])) for r,_ in uses_)
        try:
            placed = sm.place(name, master, *target, max_um=max(radius, corridor_um))
        except ValueError as exc:
            error = RoadError(f'buffer road packing failed: {name}: {exc}')
            error.partial_sites = result
            error.blocked_buffer = name
            error.branch_roads = sm.roads
            raise error from exc
        result[name] = {k: placed[k] for k in ('origin_um', 'orient')}
    for name, xy in flop_sites.items():
        sm.roads = []
        c = graph['cells'][name]
        ff_radius = (flop_radii or {}).get(name,corridor_um)
        if move_flops:
            w,h = rows['masters'][c['master']]
            placed = sm.place(name,c['master'],xy[0]+w/2,xy[1]+h/2,max_um=2*ff_radius)
            if placed['displacement_um'] > ff_radius+1e-6:
                raise RoadError(f'FF legal site exceeds reviewed displacement: {name}')
            result[name] = {k:placed[k] for k in ('origin_um','orient')}
        else:
            k = next((k for k,r in enumerate(sm.rows) if abs(r[1]-xy[1]) < 1e-6),None)
            if k is None:
                raise RoadError(f'FF site is not a row: {name}')
            s = int(round((xy[0]-sm.rows[k][0])/sm.sw))
            n = sm.width_sites(c['master'])
            if abs(sm.rows[k][0]+s*sm.sw-xy[0]) > 1e-6 or not sm.free(k,s,n):
                raise RoadError(f'FF site body/grid conflict: {name}')
            for q in range(s,s+n):sm.occ[k][q]=name
            result[name]={'origin_um':xy,'orient':sm.rows[k][2]}

        # Reserve the exact shared fork prefix alongside its source FF before
        # other FFs consume that local bay. INV parity and branch order stay.
        owned = [t for t in traces if t['source_pin'].rsplit('/',1)[0] == name]
        owned = update_road_endpoints(graph,owned,result)
        local_uses = uses_of(owned)
        for trace in owned:
            for buffer in trace['buffers']:
                if buffer not in result and len(all_uses[buffer]) > 1:
                    place_buffer(buffer,local_uses[buffer])
    traces = update_road_endpoints(graph,traces,result)
    for name,uses_ in sorted(uses_of(traces).items(),key=lambda kv:(-len(kv[1]),kv[0])):
        if name not in result:
            place_buffer(name,uses_)
    return result


def moved_pin(graph, sites, fullpin):
    name, pin = fullpin.rsplit('/', 1)
    cell = graph['cells'][name]
    xy = cell['pins'][pin]['xy_um']
    ox, oy = cell['origin_um']
    x, y = xy[0]-ox, xy[1]-oy
    if cell['orient'] not in ('R0', 'MX') or sites[name]['orient'] not in ('R0', 'MX'):
        raise RoadError('unsupported pin orientation')
    if cell['orient'] != sites[name]['orient']:
        y = cell['height_um']-y
    nx, ny = sites[name]['origin_um']
    return [nx+x, ny+y]


def update_road_endpoints(graph, traces, sites):
    import copy
    result = copy.deepcopy(traces)
    for trace in result:
        road = trace['polyline_um']
        old = [p[:] for p in road]
        for key, end in (('source_pin', 0), ('sink_pin', -1)):
            if trace[key].rsplit('/', 1)[0] in sites:
                road[end] = moved_pin(graph, sites, trace[key])
        if len(road) == 2:
            if old[0][0] == old[1][0]:
                road.insert(1, [road[0][0], road[-1][1]])
            else:
                road.insert(1, [road[-1][0], road[0][1]])
        else:
            if old[0][0] == old[1][0]: road[1][0] = road[0][0]
            else: road[1][1] = road[0][1]
            if old[-1][0] == old[-2][0]: road[-2][0] = road[-1][0]
            else: road[-2][1] = road[-1][1]
        trace['road_length_um'] = sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(road,road[1:]))
    return result


def price_buffer_paths(graph, traces, sites, limit_um=405):
    """Conservative explicit path through each actual input/output buffer pin.

    Connect pin to its nearest projection on the reviewed polyline, follow that
    polyline between projections, then connect to the next pin. Includes actual
    buffer order/backtracking; never substitutes straight FF distance or R/3.
    This reports a proposal: owner must check corridor/body/opaque geometry of
    the emitted waypoint paths before a physical run.
    """
    def project(p, road):
        options=[]; arc=0
        for a,b in zip(road,road[1:]):
            q=[min(max(p[k],min(a[k],b[k])),max(a[k],b[k])) for k in (0,1)]
            off=abs(p[0]-q[0])+abs(p[1]-q[1])
            options.append((off,arc+abs(a[0]-q[0])+abs(a[1]-q[1]),q))
            arc+=abs(a[0]-b[0])+abs(a[1]-b[1])
        return min(options)
    result=[]
    for trace in update_road_endpoints(graph,traces,sites):
        road=trace['polyline_um'];points=[road[0]]
        for name in trace['buffers']:
            c=graph['cells'][name]
            for direction in ('INPUT','OUTPUT'):
                pin=next(p for p,r in c['pins'].items() if r['direction']==direction)
                points.append(moved_pin(graph,sites,name+'/'+pin))
        points.append(road[-1]);total=0;legs=[]
        for a,b in zip(points[0::2],points[1::2]):
            da,sa,pa=project(a,road);db,sb,pb=project(b,road)
            cost=da+abs(sb-sa)+db;total+=cost
            legs.append({'from_um':a,'to_um':b,'from_projection_um':pa,'to_projection_um':pb,'length_um':cost})
        result.append({'source_pin':trace['source_pin'],'sink_pin':trace['sink_pin'],'buffers':trace['buffers'],
                       'wire_length_um':total,'limit_um':limit_um,'pass':total<=limit_um+1e-6,'legs':legs})
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--graph', type=Path, required=True)
    ap.add_argument('--roads', type=Path, required=True)
    ap.add_argument('--sites', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--dbu', type=int, default=1000)
    ap.add_argument('--halo-um', type=float, default=8.64)
    args = ap.parse_args()
    graph = json.loads(args.graph.read_text())
    roads = json.loads(args.roads.read_text())['roads']
    if args.sites:
        text, traces = compile_sites(graph, roads, json.loads(args.sites.read_text()), args.dbu, args.halo_um)
        args.out.write_text(text)
        args.out.with_suffix('.traces.json').write_text(json.dumps(traces, indent=2) + '\n')
    else:
        args.out.write_text(json.dumps(trace_roads(graph, roads), indent=2) + '\n')


if __name__ == '__main__':
    main()
