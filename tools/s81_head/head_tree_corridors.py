#!/usr/bin/env python3
"""HEAD physical clock corridor allocation; pure planning, no P&R/STA.

The balanced logical tree is unchanged. Long clock trunks receive interval-
colored PG-gap corridors before local pin jogs are routed. This candidate needs
a fresh per-type island census and geometry review before physical adoption.
"""
import argparse
import copy
import heapq
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.environ.get('HEAD_TREE_SHARED_TOOLS',
    str(Path(__file__).resolve().parent.parent / 'die_plan')))
import die_clock_mesh as D
import schema as S


def color_intervals(rows):
    active, free, result, count = [], [], {}, 0
    for lo, hi, key in sorted(rows):
        while active and active[0][0] < lo - 1e-6:
            _, c = heapq.heappop(active)
            heapq.heappush(free, c)
        c = heapq.heappop(free) if free else count
        if c == count:
            count += 1
        result[key] = c
        heapq.heappush(active, (hi, c))
    return result, count


def allocate(spec, plan, align_inputs=False, exact_jogs=False):
    out = copy.deepcopy(spec)
    groups, bydrv, incoming = defaultdict(list), defaultdict(list), {}
    for name, cell in out['cell_sites'].items():
        groups['g' + str(cell['group'])].append((name, cell))
    for cells in groups.values():
        cells.sort(key=lambda p: p[1]['origin_um'][1])
    for edge in out['nets']:
        bydrv[edge['drv']].append(edge)
        incoming[edge['load']] = edge['drv']
    def pin(g, p):
        _, cell = groups[g][0]
        return D.C128.pin_xy({'c': dict(x=cell['origin_um'][0], y=cell['origin_um'][1],
            orient=cell['orient'])}, 'c', p, D.ROW_Y)
    grid = {v['layer']: v for v in plan.die['pg']['grid']}
    original_layers = {g: edges[0]['layer'] for g, edges in bydrv.items()}
    if align_inputs:
        for g, cells in groups.items():
            if original_layers.get(g) == 'M9' or original_layers.get(incoming.get(g)) == 'M9':
                continue
            pg = grid['M9']; step = pg['pitch_um']/2
            phase = pg['offset_um'] + pg['pitch_um']/4
            ax = pin(g, 'A')[0]
            desired = phase + round((ax-phase)/step)*step
            tr = D.DEFAULT_TRACKS['M9']
            desired = tr['offset_um'] + round((desired-tr['offset_um'])/tr['pitch_um'])*tr['pitch_um']
            bar = ax - cells[0][1]['origin_um'][0]
            x = D.snap(desired-bar, D.SITE_X)
            for _, cell in cells:
                cell['origin_um'][0] = x
    buckets = defaultdict(list)
    layers = {}
    for g, edges in bydrv.items():
        lay, = {e['layer'] for e in edges}
        layers[g] = lay
        d = pin(g, 'Y')
        ps = [pin(e['load'], 'A') for e in edges]
        axis = 0 if lay == 'M8' else 1
        _, cell = groups[g][0]
        coord = (cell['origin_um'][1] + len(groups[g]) * D.ROW_Y / 2
                 if lay == 'M8' else cell['origin_um'][0] + D.BUF_W / 2)
        bucket = round(coord / 8.64) * 8.64
        vals = [d[axis]] + [p[axis] for p in ps]
        # Account for every permitted local-jog displacement before coloring.
        pad = (.08 if lay == 'M8' else D.C128.STACK_RISER_MAX_UM +
               (max(len(v) for v in groups.values())-1)*D.ROW_Y + .08) if exact_jogs else 8.64
        buckets[lay, round(bucket, 3)].append((min(vals)-pad, max(vals)+pad, g))
    targets, counts = {}, {}
    for (lay, bucket), rows in sorted(buckets.items()):
        colors, n = color_intervals(rows)
        counts[f'{lay}@{bucket}'] = n
        pg = grid[lay]
        step = pg['pitch_um'] / 2
        phase = pg['offset_um'] + pg['pitch_um'] / 4
        base = phase + round((bucket-phase)/step) * step
        for g, c in colors.items():
            desired = base + (c - n//2) * step
            tr = D.DEFAULT_TRACKS[lay]
            targets[g] = dict(layer=lay, c=round(tr['offset_um'] +
                round((desired-tr['offset_um'])/tr['pitch_um']) * tr['pitch_um'], 4), color=c)
    for g, cells in groups.items():
        # The producing stage owns its outgoing corridor. Leaves follow their
        # incoming corridor, keeping the local mesh driver on the same row.
        gy = g if layers.get(g) == 'M8' else incoming.get(g)
        gx = g if layers.get(g) == 'M9' else incoming.get(g)
        if gy in targets and targets[gy]['layer'] == 'M8':
            y = D.snap(targets[gy]['c'] - len(cells) * D.ROW_Y / 2, D.ROW_Y)
            for k, (_, cell) in enumerate(cells):
                cell['origin_um'][1] = round(y + k*D.ROW_Y, 4)
        if gx in targets and targets[gx]['layer'] == 'M9':
            p = 'Y' if gx == g else 'A'
            oldx = cells[0][1]['origin_um'][0]
            bar = pin(g, p)[0] - oldx
            x = D.snap(targets[gx]['c'] - bar, D.SITE_X)
            for _, cell in cells:
                cell['origin_um'][0] = x
    corridors = {}
    for g, edges in bydrv.items():
        d = pin(g, 'Y')
        ps = [pin(e['load'], 'A') for e in edges]
        axis = 0 if layers[g] == 'M8' else 1
        vals = [d[axis]] + [p[axis] for p in ps]
        name = 'ckm_w_' + groups[g][0][0]
        pad = (.08 if layers[g] == 'M8' else D.C128.STACK_RISER_MAX_UM +
               (max(len(v) for v in groups.values())-1)*D.ROW_Y + .08) if exact_jogs else 8.64
        corridors[name] = dict(targets[g], lo=min(vals)-pad, hi=max(vals)+pad)
    out['exact_reserve'] = False
    out['summary']['corridor_colors'] = counts
    out['summary']['requires_new_island_census'] = True
    return out, corridors


def route(spec, corridors, plan, exact_jogs=False):
    original = D.C128.TrackRouter
    class CorridorRouter(original):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.preloaded, self.fixed, self.used = False, {}, set()
            self.pending_drops = {}
        def reserve(self, shapes):
            super().reserve(shapes)
            if self.preloaded:
                return
            self.preloaded = True
            errors = []
            for name, row in sorted(corridors.items(), key=lambda p: -(p[1]['hi']-p[1]['lo'])):
                c, mode, ext = super().place(row['layer'], row['c'], row['lo'], row['hi'], name,
                    keep=(row['c']-.001, row['c']+.001))
                if c is None:
                    errors.append(dict(kind='corridor_unavailable', name=name, detail=row))
                else:
                    self.fixed[name] = (c, mode, ext)
            if errors:
                raise D.C128.PlanError(errors)
        def place(self, layer, ideal, a0, a1, net, **kw):
            if net in self.fixed and net not in self.used and corridors[net]['layer'] == layer:
                self.used.add(net)
                c, mode, ext = self.fixed[net]
                if abs(c-ideal) > self.max_move + 1e-6:
                    raise D.C128.PlanError([dict(kind='corridor_pin_reach', name=net,
                        detail=f'{c} vs ideal {ideal}, bound {self.max_move}')])
                return c, mode, ext
            if exact_jogs and net in self.used and corridors[net]['layer'] == 'M8':
                if layer == 'M8' and abs(abs(a1-a0)-2*self.max_move) < 1e-5:
                    # Local drop is anchored to the already-aligned capture A
                    # pin. Reserve its actual short jog, then require that exact
                    # M9 column; failure does not fall back to a distant drop.
                    x = (a0+a1)/2
                    tr = self.tracks['M9']
                    col = tr['offset_um'] + round((x-tr['offset_um'])/tr['pitch_um'])*tr['pitch_um']
                    self.pending_drops[net] = col
                    return super().place(layer, ideal, min(x,col), max(x,col), net, **kw)
                if layer == 'M9' and net in self.pending_drops:
                    col = self.pending_drops.pop(net)
                    return super().place(layer, col, a0, a1, net, keep=(col-.001,col+.001))
            return super().place(layer, ideal, a0, a1, net, **kw)
    D.C128.TrackRouter = CorridorRouter
    try:
        result = D.build_explicit(spec, plan, ndr='16w', root_um=plan.raw['clock']['spine']['root_um']
            if hasattr(plan, 'raw') else None)
        errors = []
        for wire in result[3]['fixed_wires']:
            if wire['name'] not in corridors:
                continue
            r = corridors[wire['name']]
            for layer,x0,y0,x1,y1 in wire['segs'][:1]:
                lo,hi = sorted((x0,x1) if layer=='M8' else (y0,y1))
                if layer != r['layer'] or lo < r['lo']-1e-5 or hi > r['hi']+1e-5:
                    errors.append(dict(kind='corridor_reserve_overflow', name=wire['name'],
                                       detail=dict(actual=[layer,lo,hi], reserved=r)))
        if errors:
            raise D.C128.PlanError(errors)
        return result
    finally:
        D.C128.TrackRouter = original


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    ap.add_argument('spec', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--align-inputs', action='store_true')
    ap.add_argument('--exact-local-jogs', action='store_true')
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    plan = S.Plan(S.load(a.plan))
    spec, corridors = allocate(json.loads(a.spec.read_text()), plan, align_inputs=a.align_inputs,
                               exact_jogs=a.exact_local_jogs)
    (a.out/'explicit_tree.json').write_text(json.dumps(spec, indent=1)+'\n')
    (a.out/'corridors.json').write_text(json.dumps(corridors, indent=1)+'\n')
    try:
        cells, nets, ports, meta = route(spec, corridors, plan, exact_jogs=a.exact_local_jogs)
    except D.C128.PlanError as error:
        from collections import Counter
        summary = dict(verdict='FAIL', counts=dict(Counter(r['kind'] for r in error.rows)), errors=len(error.rows))
        (a.out/'plan_errors.json').write_text(json.dumps(dict(error=str(error), rows=error.rows), indent=1)+'\n')
    else:
        summary = dict(verdict='PASS', meta=meta['meta'])
        (a.out/'mesh.json').write_text(json.dumps(meta)+'\n')
        (a.out/'place.json').write_text(json.dumps(cells)+'\n')
        (a.out/'nets.json').write_text(json.dumps(dict(nets=nets, ports=ports))+'\n')
    summary['corridor_colors'] = spec['summary']['corridor_colors']
    (a.out/'summary.json').write_text(json.dumps(summary, indent=1)+'\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
