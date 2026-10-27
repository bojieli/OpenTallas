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


def allocate(spec, plan, align_inputs=False, exact_jogs=False, lower_face_gap=False, separate_drops=False, mesh_straps=None):
    mesh_straps = mesh_straps or []
    out = copy.deepcopy(spec)
    groups, bydrv, incoming = defaultdict(list), defaultdict(list), {}
    for name, cell in out['cell_sites'].items():
        groups['g' + str(cell['group'])].append((name, cell))
    for cells in groups.values():
        cells.sort(key=lambda p: p[1]['origin_um'][1])
    for edge in out['nets']:
        bydrv[edge['drv']].append(edge)
        incoming[edge['load']] = edge['drv']
    for g in groups:
        bydrv.setdefault(g, [])       # leaf output stubs are physical nets too
    for g, edges in bydrv.items():
        if edges and all(e['layer']=='M8' for e in edges):
            dx = sum(groups[e['load']][0][1]['origin_um'][0]-groups[g][0][1]['origin_um'][0]
                     for e in edges)
            if dx < -1e-6:
                # Put Y on the west-facing side. The arriving A-pin jog then
                # does not cross the departing clock trunk through the bank.
                for _,cell in groups[g]:
                    cell['orient'] = 'MY'
    def pin(g, p):
        _, cell = groups[g][0]
        return D.C128.pin_xy({'c': dict(x=cell['origin_um'][0], y=cell['origin_um'][1],
            orient=cell['orient'])}, 'c', p, D.ROW_Y)
    grid = {v['layer']: v for v in plan.die['pg']['grid']}
    original_layers = {g: edges[0]['layer'] if edges else 'M8' for g, edges in bydrv.items()}
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
        lay, = {e['layer'] for e in edges} if edges else {'M8'}
        layers[g] = lay
        d = pin(g, 'Y')
        ps = [pin(e['load'], 'A') for e in edges] if edges else [(d[0]+8.64,d[1])]
        axis = 0 if lay == 'M8' else 1
        _, cell = groups[g][0]
        coord = (cell['origin_um'][1] + len(groups[g]) * D.ROW_Y / 2
                 if lay == 'M8' else cell['origin_um'][0] + D.BUF_W / 2)
        bucket = round(coord / 8.64) * 8.64
        vals = [d[axis]] + [p[axis] for p in ps]
        # Account for every permitted local-jog displacement before coloring.
        pad = (.08 if lay == 'M8' else 16.0) if exact_jogs else 8.64
        buckets[lay, round(bucket, 3)].append((min(vals)-pad, max(vals)+pad, g))
    targets, counts = {}, {}
    for (lay, bucket), rows in sorted(buckets.items()):
        colors, n = color_intervals(rows)
        counts[f'{lay}@{bucket}'] = n
        pg = grid[lay]
        step = pg['pitch_um'] / 2
        phase = pg['offset_um'] + pg['pitch_um'] / 4
        base = phase + round((bucket-phase)/step) * step
        legal_cols = [base+k*step for k in range(-n//2, 2*n+2)
                      if not any(ss[0]==lay and abs(ss[1]-(base+k*step))<1.5 for ss in mesh_straps)]
        for g, c in colors.items():
            desired = legal_cols[c]
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
    def recolor_horizontal():
        # Vertical-column placement can move a horizontal corner's actual X end.
        # Recolor H intervals from those final pins; Y movement cannot alter them.
        hrows = defaultdict(list)
        hbucket = {g: bucket for (lay,bucket), rows in buckets.items() if lay=='M8' for _,_,g in rows}
        for g, edges in bydrv.items():
            if layers[g] != 'M8':
                continue
            d = pin(g,'Y')
            vals = [d[0]] + ([pin(e['load'],'A')[0] for e in edges] if edges else [d[0]+8.64])
            pad = .08 if exact_jogs else 8.64
            hrows[hbucket[g]].append((min(vals)-pad,max(vals)+pad,g))
        for bucket, rows in hrows.items():
            colors,n = color_intervals(rows); counts[f'M8@{bucket}'] = n
            pg = grid['M8']; step=pg['pitch_um'] if separate_drops else pg['pitch_um']/2; phase=pg['offset_um']+pg['pitch_um']/4
            base=phase+round((bucket-phase)/step)*step
            for g,c in colors.items():
                desired=base+(c-n//2)*step; tr=D.DEFAULT_TRACKS['M8']
                if lower_face_gap:
                    # Reserve the actual bank body below the first face-flop row.
                    # These dimensions belong only to the measured HEAD lower band;
                    # upper spine bands retain their independent open reservation.
                    limits=[]
                    for _,_,gg in rows:
                        cc=groups[gg]; part=cc[0][1]['part']; pp=plan.parts[part]
                        typ=pp['type']; height=plan.types[typ]['outline_um'][1]
                        oy=pp['origin_um'][1]; cy=sum(v['origin_um'][1] for _,v in cc)/len(cc)
                        local=cy-oy
                        if pp.get('orient','R0') in ('MX','R180'):local=height-local
                        band=1036.8 if typ in ('hd_spn','hd_spn_end') and 1365.12<=local<=1416.8 else 0.0
                        if typ not in ('hd_tile','hd_spn','hd_spn_end') or not 328.32<=local-band<=380.0:
                            limits=[];break
                        lowbody,highbody=330.32+band,352.78+band
                        half=len(cc)*D.ROW_Y/2
                        if pp.get('orient','R0') in ('MX','R180'):
                            limits.append((oy+height-highbody+half,oy+height-lowbody-half))
                        else:limits.append((oy+lowbody+half,oy+highbody-half))
                    if limits:
                        low=max(q[0] for q in limits);high=min(q[1] for q in limits)
                        if separate_drops:low-=2.0;high+=2.0
                        import math
                        phases=[phase,phase+step/2] if separate_drops else [phase]
                        starts=[ph+math.ceil((low-ph)/step)*step for ph in phases]
                        starts=[st for st in starts if st+(n-1)*step<=high+1e-6
                                and all(not any(ss[0]=='M8' and abs(ss[1]-(st+j*step))<1.0
                                                    for ss in mesh_straps) for j in range(n))]
                        if not starts:raise D.C128.PlanError([dict(kind='face_landing_lane_capacity',name=str(bucket),detail=dict(colors=n,allowed=[low,high]))])
                        first=min(starts,key=lambda st:abs(st+(n-1)*step/2-(low+high)/2))
                        desired=first+c*step
                        if desired>high+1e-6:
                            raise D.C128.PlanError([dict(kind='face_gap_capacity',name=str(bucket),
                                detail=dict(colors=n,required=desired,allowed=[low,high]))])
                targets[g]=dict(layer='M8',c=round(tr['offset_um']+round((desired-tr['offset_um'])/tr['pitch_um'])*tr['pitch_um'],4),color=c)
        for g,cells in groups.items():
            gy=g if layers.get(g)=='M8' else incoming.get(g)
            if gy in targets and targets[gy]['layer']=='M8':
                y=D.snap(targets[gy]['c']-len(cells)*D.ROW_Y/2,D.ROW_Y)
                if separate_drops and lower_face_gap:
                    pp=plan.parts[cells[0][1]['part']];typ=pp['type'];oy=pp['origin_um'][1]
                    height=plan.types[typ]['outline_um'][1];cy=cells[0][1]['origin_um'][1]-oy
                    flip=pp.get('orient','R0') in ('MX','R180')
                    local=height-cy if flip else cy
                    band=1036.8 if typ in ('hd_spn','hd_spn_end') and 1365.12<=local<=1416.8 else 0
                    if typ in ('hd_tile','hd_spn','hd_spn_end') and 328.32<=local-band<=380:
                        import math
                        lo,hi=(oy+height-352.78-band,oy+height-330.32-band) if flip else (oy+330.32+band,oy+352.78+band)
                        yl=math.ceil((lo-1e-7)/D.ROW_Y)*D.ROW_Y
                        yh=math.floor((hi-len(cells)*D.ROW_Y+1e-7)/D.ROW_Y)*D.ROW_Y
                        if yl>yh:raise ValueError('face bank body capacity')
                        y=min(max(y,yl),yh)
                for k,(_,cell) in enumerate(cells):cell['origin_um'][1]=round(y+k*D.ROW_Y,4)
    recolor_horizontal()
    if separate_drops:
        # Align the root capture bank with the input's first legal M8 landing
        # inside the existing root island. This removes an unnecessary M9 drop
        # sharing the output gap, while retaining the same root buffer stage.
        source_y=plan.raw['clock']['spine']['root_um'][1]
        pg=grid['M8'];step=pg['pitch_um']/2;phase=pg['offset_um']+pg['pitch_um']/4
        landing=phase+round((source_y+D.C128.TREE_OFF_UM-phase)/step)*step
        for g in set(groups)-set(incoming):
            cc=groups[g];y=D.snap(landing-len(cc)*D.ROW_Y/2,D.ROW_Y)
            for k,(_,cell) in enumerate(cc):cell['origin_um'][1]=round(y+k*D.ROW_Y,4)
    original_ax={g:pin(g,'A')[0] for g in groups}
    def allocate_capture_columns():
        # Distinct clock nets cannot share a local "M9" capture drop. Allocate
        # physical capture columns before routing, bounded by real host and
        # actual pin-to-pin clock repeater reach; no extra logic stages.
        pg=grid["M9"]; step=pg["pitch_um"]/2; phase=pg["offset_um"]+pg["pitch_um"]/4
        used=[(ss[1],ss[2],ss[3],'ck_mesh') for ss in mesh_straps if ss[0]=='M9']
        for g,edges in bydrv.items():
            if layers[g]=="M9":
                yy=[pin(g,"Y")[1]]+[pin(e["load"],"A")[1] for e in edges]
                used.append((targets[g]["c"],min(yy)-3,max(yy)+3,g))
        tasks=[]
        for g,parent in incoming.items():
            if layers.get(parent)!="M8" or layers.get(g)!="M8":continue
            ay=pin(g,"A")[1]; ty=targets[parent]["c"]
            if abs(ay-ty)<=D.C128.STACK_RISER_MAX_UM:continue
            tasks.append((abs(ay-ty),g,parent,min(ay,ty)-1,max(ay,ty)+1))
        assigned=[]
        for _,g,parent,lo,hi in sorted(tasks,reverse=True):
            cc=groups[g]; pp=plan.parts[cc[0][1]["part"]]
            x0=pp["origin_um"][0]; x1=x0+plan.types[pp["type"]]["outline_um"][0]
            ax=pin(g,"A")[0]; base=phase+round((ax-phase)/step)*step
            bar=ax-cc[0][1]["origin_um"][0]; old=cc[0][1]["origin_um"][0]
            found=None
            offsets=[0]+[v for k in range(1,13) for v in (-k,k)]
            for k in offsets:
                tr=D.DEFAULT_TRACKS["M9"]; target=base+k*step
                col=tr["offset_um"]+round((target-tr["offset_um"])/tr["pitch_um"])*tr["pitch_um"]
                xx=D.snap(col-bar,D.SITE_X); dx=xx-old
                if xx<x0+2 or xx+D.BUF_WIDTHS[D.BUF]>x1-2:continue
                if any(abs(col-c)<1.0 and a<=hi and lo<=b and net!=parent for c,a,b,net in used):continue
                ap=(pin(g,"A")[0]+dx,pin(g,"A")[1]); yp=(pin(g,"Y")[0]+dx,pin(g,"Y")[1])
                endpoints=[(pin(parent,"Y"),ap)]+[(yp,pin(e["load"],"A")) for e in bydrv[g]]
                if any(abs(a[0]-b[0])+abs(a[1]-b[1])>450 for a,b in endpoints):continue
                rect=(xx,cc[0][1]["origin_um"][1],xx+D.BUF_WIDTHS[D.BUF],cc[-1][1]["origin_um"][1]+D.ROW_Y)
                clash=False
                for other,units in groups.items():
                    if other==g:continue
                    for _,unit in units:
                        ox,oy=unit["origin_um"];w=D.BUF_WIDTHS.get(unit["master"],D.BUF_W)
                        if rect[0]<ox+w+.05 and ox<rect[2]+.05 and rect[1]<oy+D.ROW_Y+.05 and oy<rect[3]+.05:
                            clash=True;break
                    if clash:break
                if clash:continue
                found=(xx,col);break
            if found is None:
                raise D.C128.PlanError([dict(kind="capture_column_capacity",name=g,detail=dict(parent=parent,y=[lo,hi],x=ax))])
            xx,col=found
            for _,cell in cc:cell["origin_um"][0]=xx
            used.append((col,lo,hi,parent));assigned.append(dict(group=g,column=col,dx=round(xx-old,4)))
        out["summary"]["capture_columns"]=assigned
    if separate_drops:
        seen=set()
        while True:
            before=tuple(tuple(c['origin_um']) for c in out['cell_sites'].values())
            if before in seen:raise D.C128.PlanError([dict(kind='capture_allocation_cycle',name='tree',detail='capture columns and trunk interval coloring do not converge')])
            seen.add(before)
            allocate_capture_columns()
            recolor_horizontal()
            after=tuple(tuple(c['origin_um']) for c in out['cell_sites'].values())
            if after==before:break
        out['summary']['capture_allocation_passes']=len(seen)
    corridors = {}
    for g, edges in bydrv.items():
        d = pin(g, 'Y')
        ps = [pin(e['load'], 'A') for e in edges] if edges else [(d[0]+8.64,d[1])]
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


def route(spec, corridors, plan, exact_jogs=False, mesh_straps=None):
    groups=defaultdict(list)
    for unit,cell in spec['cell_sites'].items():groups['g'+str(cell['group'])].append((unit,cell))
    for us in groups.values():us.sort(key=lambda q:q[1]['origin_um'][1])
    children=defaultdict(list)
    for edge in spec['nets']:children[edge['drv']].append(edge['load'])
    netgroups={'ckm_w_'+us[0][0]:g for g,us in groups.items()}
    def pin_window(net,ideal,a0,a1):
        g=netgroups.get(net)
        if g is None:return None
        candidates=[]
        for gg,p in [(g,'Y')]+[(ld,'A') for ld in children[g]]:
            units=groups[gg];pts=[]
            for unit,cell in units:
                model=dict(x=cell['origin_um'][0],y=cell['origin_um'][1],orient=cell['orient'])
                pts.append(D.C128.pin_xy({unit:model},unit,p,D.ROW_Y))
            if abs(ideal-pts[0][1])<=D.C128.TREE_OFF_UM+.01 and min(a0,a1)-.1<=pts[0][0]<=max(a0,a1)+.1:
                candidates.append((abs(ideal-pts[0][1]),min(y for x,y in pts)-D.C128.STACK_RISER_MAX_UM,
                                   max(y for x,y in pts)+D.C128.STACK_RISER_MAX_UM))
        return min(candidates)[1:] if candidates else None
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
            if mesh_straps:
                segs=[(ss[0],ss[2],ss[1],ss[3],ss[1],'ck_mesh','mesh') if ss[0]=='M8'
                      else (ss[0],ss[1],ss[2],ss[1],ss[3],'ck_mesh','mesh') for ss in mesh_straps]
                super().reserve(D.C128.clock_shapes(segs,D.NDR['8w'],'VSS'))
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
            if layer=='M8' and net in self.used:
                window=pin_window(net,ideal,a0,a1)
                if window:
                    existing=kw.get('keep')
                    kw['keep']=(max(window[0],existing[0]),min(window[1],existing[1])) if existing else window
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
    ap.add_argument('--lower-face-gap', action='store_true')
    ap.add_argument('--separate-drops', action='store_true')
    ap.add_argument('--mesh-straps', type=Path, help='actual continuous mesh strap file reserved before all tree metal')
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    plan = S.Plan(S.load(a.plan))
    mesh_straps=json.loads(a.mesh_straps.read_text()) if a.mesh_straps else []
    spec, corridors = allocate(json.loads(a.spec.read_text()), plan, align_inputs=a.align_inputs,
                               exact_jogs=a.exact_local_jogs, lower_face_gap=a.lower_face_gap, separate_drops=a.separate_drops, mesh_straps=mesh_straps)
    (a.out/'explicit_tree.json').write_text(json.dumps(spec, indent=1)+'\n')
    (a.out/'corridors.json').write_text(json.dumps(corridors, indent=1)+'\n')
    try:
        cells, nets, ports, meta = route(spec, corridors, plan, exact_jogs=a.exact_local_jogs, mesh_straps=mesh_straps)
    except D.C128.PlanError as error:
        from collections import Counter
        summary = dict(verdict='FAIL', counts=dict(Counter(r['kind'] for r in error.rows)), errors=len(error.rows))
        (a.out/'plan_errors.json').write_text(json.dumps(dict(error=str(error), rows=error.rows), indent=1)+'\n')
    else:
        summary = dict(verdict='PASS', meta=meta['meta'])
        (a.out/'mesh.json').write_text(json.dumps(meta)+'\n')
        (a.out/'place.json').write_text(json.dumps(cells)+'\n')
        (a.out/'nets.json').write_text(json.dumps(dict(nets=nets, ports=ports))+'\n')
    summary['mesh_straps_reserved']=len(mesh_straps)
    summary['corridor_colors'] = spec['summary']['corridor_colors']
    (a.out/'summary.json').write_text(json.dumps(summary, indent=1)+'\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
