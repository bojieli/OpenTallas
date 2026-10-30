#!/usr/bin/env python3
"""Materialize an exact planned clock graph in a fresh native target database.

Rebuilds clock primitives and native tap connections from one matched ctree/tree
pair. Old clock-node identifiers or provider-stage binding tables are never
carried across a clock rebuild. Output is connected but unrouted; provider,
PG, clock routing, phase, reset and token qualification remain separate steps.
"""
from __future__ import annotations
import argparse
import bisect
import copy
import math
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re


def clock_graph(text, tree, prefix='ck_'):
    """Parse the emitted primitive graph, validating all sites and tap aliases."""
    cells = {}; drivers = {'root': 'root'}; loads = defaultdict(list)
    primitive = r'(?m)^\s*(\w+_ASAP7_75t_R)\s+(\w+)\s*\(([^;]+)\);'
    for master, name, pins in re.findall(primitive, text):
        pairs = re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)', pins)
        ports = dict(pairs)
        if len(pairs) != 2 or set(ports) != {'A', 'Y'}:
            raise ValueError('clock primitive must have exactly A/Y pins: '+name)
        if name in cells or name not in tree['sites']:
            raise ValueError('duplicate clock cell or missing planned site: '+name)
        xy = tree['sites'][name]
        if len(xy) != 2 or not all(isinstance(x, (int, float)) for x in xy):
            raise ValueError('invalid planned clock site: '+name)
        cells[name] = dict(inst=prefix+name, master=master, xy_um=xy)
        if ports['Y'] in drivers:
            raise ValueError('multiple clock drivers: '+ports['Y'])
        drivers[ports['Y']] = name
        loads[ports['A']].append(dict(inst=prefix+name, pin='A'))
        cells[name]['ports'] = ports
    if not cells or set(cells) != set(tree['sites']):
        raise ValueError('clock primitive graph differs from planned sites')
    assignments = re.findall(r'(?m)^\s*assign\s+(\w+)\s*=\s*(\w+)\s*;', text)
    aliases = dict(assignments)
    taps = {t['port']: t for t in tree['taps']}
    if len(assignments) != len(aliases) or len(taps) != len(tree['taps']) or set(taps) != set(aliases):
        raise ValueError('clock output aliases differ from planned taps')
    endpoints = set()
    for name, raw in aliases.items():
        t = taps[name]; key = (t['part'], t['tap'])
        if key in endpoints:
            raise ValueError('duplicate native clock endpoint: '+str(key))
        endpoints.add(key)
        loads[raw].append(dict(inst=t['part'], pin=t['tap'], port=name))
    if set(loads) != set(drivers):
        raise ValueError('clock graph has an undriven or unused net')
    # Every primitive must be reachable from the single root, independently of
    # node numbering or legalizer-generated names.
    reached = set(); todo = ['root']
    while todo:
        net = todo.pop()
        for load in loads[net]:
            if 'port' in load:
                continue
            raw = load['inst'][len(prefix):]
            if raw in reached:
                raise ValueError('clock graph cycle or repeated A terminal: '+raw)
            reached.add(raw); todo.append(cells[raw]['ports']['Y'])
    if reached != set(cells):
        raise ValueError('clock graph contains a disconnected component')
    nets = {raw: dict(name=prefix+raw, driver=driver, loads=ls) for raw, ls in loads.items()
            for driver in [drivers[raw]]}
    return dict(cells=cells, nets=nets, aliases=aliases, taps=taps)


def physical_rect(inst, shape):
    signs = {'R0':(1,1), 'MX':(1,-1), 'MY':(-1,1), 'R180':(-1,-1)}
    orient = str(inst.getOrient())
    if orient not in signs:
        raise ValueError('unsupported native orientation: '+orient)
    sx, sy = signs[orient]; ox, oy = inst.getOrigin()
    xs = sorted((ox+sx*shape.xMin(), ox+sx*shape.xMax()))
    ys = sorted((oy+sy*shape.yMin(), oy+sy*shape.yMax()))
    return [xs[0], ys[0], xs[1], ys[1]]


class SiteSpace:
    """Native-body origin space serialized from die_trial.clock_site(plan)."""
    def __init__(self, doc, bucket=250.0):
        self.doc=doc;self.bucket=bucket;self.parts=defaultdict(list);self.forbidden=defaultdict(list)
        for key,records in [('parts',doc['parts']),('forbidden',doc['forbidden'])]:
            index=getattr(self,key)
            for r in records:
                for i in range(math.floor(r[0]/bucket),math.floor(r[2]/bucket)+1):
                    for j in range(math.floor(r[1]/bucket),math.floor(r[3]/bucket)+1):index[i,j].append(r)
    def legal(self,x,y):
        x/=1000;y/=1000;k=(math.floor(x/self.bucket),math.floor(y/self.bucket))
        return any(r[0]+.5<=x<=r[2]-.5 and r[1]+.5<=y<=r[3]-.5 for r in self.parts[k]) and not any(
            r[0]<x<r[2] and r[1]<y<r[3] for r in self.forbidden[k])


def legalize_sites(graph, tree, row_specs, dbu, space=None):
    """Nearest unoccupied actual R0 row/site; no timing input or graph change.

    row_specs contain x0/y/x1/spacing in DBU. Preserve every already legal,
    nonoverlapping origin first; then place the other cells deterministically.
    """
    if dbu!=1000:raise ValueError('site-space coordinates require actual 1000 DBU/um')
    by_y=defaultdict(list)
    for r in row_specs:by_y[r['y']].append(r)
    ys=sorted(by_y)
    if not ys:raise ValueError('native target has no R0 rows')
    minimum_pitch=min([r["spacing"] for r in row_specs]+[b-a for a,b in zip(ys,ys[1:])]);occupied=defaultdict(list);placed={};pending=[]
    def free(x,y,width):
        if not any(r['x0']<=x and x+width<=r['x1'] and (x-r['x0'])%r['spacing']==0 for r in by_y.get(y,[])):return False
        if space is not None and not space.legal(x,y):return False
        spans=occupied[y];k=bisect.bisect_left(spans,(x,-1))
        return not ((k and spans[k-1][1]>x) or (k<len(spans) and spans[k][0]<x+width))
    def reserve(name,x,y,width):
        bisect.insort(occupied[y],(x,x+width));placed[name]=[x/dbu,y/dbu]
    for name,c in graph['cells'].items():
        x,y=(round(v*dbu) for v in c['xy_um']);w=c['width_dbu']
        if free(x,y,w):reserve(name,x,y,w)
        else:pending.append((name,c,x,y,w))
    for name,c,x,y,w in pending:
        row_index=bisect.bisect_left(ys,y);radius=2
        while True:
            candidates=[]
            for yy in ys[max(0,row_index-radius):min(len(ys),row_index+radius+1)]:
                for row in by_y[yy]:
                    ix=round((x-row['x0'])/row['spacing'])
                    for j in range(ix-radius,ix+radius+1):
                        xx=row['x0']+j*row['spacing']
                        candidates.append((abs(xx-x)+abs(yy-y),yy,xx))
            found=next(((cost,xx,yy) for cost,yy,xx in sorted(set(candidates)) if free(xx,yy,w)),None)
            # Do not accept a distant row while a closer x site remains outside
            # the current search square. This lower bound makes nearest exact.
            if found is not None and found[0]<=radius*minimum_pitch:
                reserve(name,found[1],found[2],w);break
            if radius>max(len(ys),max((r['x1']-r['x0'])//r['spacing'] for r in row_specs)):
                raise ValueError('no actual native row/site for clock cell '+name)
            radius*=2
    updated=copy.deepcopy(tree);moves=[]
    for name,xy in placed.items():
        before=tree['sites'][name]
        if xy!=before:moves.append(dict(cell=name,before_um=before,after_um=xy,manhattan_um=round(sum(abs(a-b) for a,b in zip(before,xy)),6)))
        updated['sites'][name]=xy;graph['cells'][name]['xy_um']=xy
    for nid,name in updated['node_buf'].items():
        updated['nodes'][str(nid)]['x'],updated['nodes'][str(nid)]['y']=placed[name]
    before=after=0.0
    for child,parent in tree['parent_of'].items():
        before+=sum(abs(a-b) for a,b in zip(tree['sites'][child],tree['sites'][parent]))
        after+=sum(abs(a-b) for a,b in zip(placed[child],placed[parent]))
    report=dict(status='ACTUAL_R0_ROW_SITES',cells=len(placed),moved=len(moves),max_move_um=max((r['manhattan_um'] for r in moves),default=0),
                wire_delta_um=round(after-before,6),added_cells=0,cycles_added=0,moves=moves)
    updated['meta']['native_row_legalization']={k:v for k,v in report.items() if k!='moves'}
    return updated,report


def rewrite_clock_tcl(text, sites):
    pattern=r'(place_inst -name (\w+) -location) \{[^}]+\}'
    seen=set()
    def replace(m):
        name=m[2]
        if name not in sites or name in seen:raise ValueError('placement Tcl differs from clock graph: '+name)
        seen.add(name);x,y=sites[name];return f'{m[1]} {{{x:.3f} {y:.3f}}}'
    out=re.sub(pattern,replace,text)
    if seen!=set(sites):raise ValueError('placement Tcl lacks clock cells')
    return out


def build(target, netlist, tree_path, output, root_xy=None, legalize=False, site_space=None, clock_tcl=None):
    import odb
    tree = json.loads(Path(tree_path).read_text())
    graph = clock_graph(Path(netlist).read_text(), tree)
    database = odb.dbDatabase.create(); odb.read_db(database, str(target))
    block = database.getChip().getBlock(); dbu = block.getDbUnitsPerMicron()
    area = block.getDieArea(); rows = defaultdict(list)
    for row in block.getRows():
        if str(row.getOrient()) == 'R0':
            rows[row.getOrigin()[1]].append(row)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if legalize:
        for c in graph['cells'].values():
            master=database.findMaster(c['master'])
            if master is None:raise ValueError('target lacks exact clock master: '+c['master'])
            c['width_dbu']=master.getWidth()
        rr=[dict(x0=r.getBBox().xMin(),y=r.getOrigin()[1],x1=r.getBBox().xMax(),spacing=r.getSpacing())
            for rs in rows.values() for r in rs]
        space=SiteSpace(json.loads(Path(site_space).read_text())) if site_space else None
        tree,report=legalize_sites(graph,tree,rr,dbu,space)
        (output/'tree_legalized.json').write_text(json.dumps(tree)+'\n')
        (output/'legalization.json').write_text(json.dumps(report)+'\n')
        if clock_tcl:(output/'ctree_legalized.tcl').write_text(rewrite_clock_tcl(Path(clock_tcl).read_text(),tree['sites']))
    endpoint_rows = {}; placed = []
    # Resolve actual native bodies, row sites and pin metal before mutation.
    for name, c in graph['cells'].items():
        if block.findInst(c['inst']):
            raise ValueError('target already contains planned clock cell: '+c['inst'])
        master = database.findMaster(c['master'])
        if not master or not master.findMTerm('A') or not master.findMTerm('Y'):
            raise ValueError('target lacks exact clock master/pins: '+c['master'])
        x, y = (round(v*dbu) for v in c['xy_um'])
        if not (area.xMin() <= x and x+master.getWidth() <= area.xMax() and
                area.yMin() <= y and y+master.getHeight() <= area.yMax()):
            raise ValueError('clock body outside die: '+name)
        if not any(r.getBBox().xMin() <= x and x+master.getWidth() <= r.getBBox().xMax()
                   and (x-r.getOrigin()[0]) % r.getSpacing() == 0 for r in rows.get(y, [])):
            raise ValueError('clock body has no actual reserved R0 row/site: '+name+' xy='+str((x,y))+' rows_at_y='+str([(r.getOrigin(),r.getSpacing(),r.getBBox().xMin(),r.getBBox().xMax()) for r in rows.get(y,[])][:6]))
        placed.append((c, master, x, y))
    for port, raw in graph['aliases'].items():
        tap = graph['taps'][port]; inst = block.findInst(tap['part'])
        iterm = inst.findITerm(tap['tap']) if inst else None
        if not iterm or iterm.getNet():
            raise ValueError('native clock pin is missing or already connected: '+port)
        shapes = [(s.getTechLayer().getName(), physical_rect(inst, s))
                  for p in iterm.getMTerm().getMPins() for s in p.getGeometry()
                  if s.getTechLayer() and s.getTechLayer().getRoutingLevel() > 0]
        if len(shapes) != 1 or shapes[0][0] != 'M7':
            raise ValueError('native clock entry is not one actual M7 rectangle: '+port)
        rect = [v/dbu for v in shapes[0][1]]
        xy = [(rect[0]+rect[2])/2, (rect[1]+rect[3])/2]
        endpoint_rows[port] = dict(net='ck_'+raw, inst=tap['part'], pin=tap['tap'], layer='M7',
                                   xy_um=xy, rect_um=rect, planned_xy_um=tap['xy'])
    for n in graph['nets'].values():
        if block.findNet(n['name']):
            raise ValueError('target already contains planned clock net: '+n['name'])
    if block.findBTerm('root'):
        raise ValueError('target already contains a root clock port')
    for n in graph['nets'].values():
        net = odb.dbNet.create(block, n['name']); net.setSigType('CLOCK')
    for c, master, x, y in placed:
        inst = odb.dbInst.create(block, master, c['inst']); inst.setOrient('R0')
        inst.setLocation(x,y); inst.setPlacementStatus('FIRM')
        for pin, raw in c['ports'].items():
            inst.findITerm(pin).connect(block.findNet('ck_'+raw))
    for port, ep in endpoint_rows.items():
        block.findInst(ep['inst']).findITerm(ep['pin']).connect(block.findNet(ep['net']))
    root = odb.dbBTerm.create(block.findNet('ck_root'), 'root'); root.setIoType('INPUT'); root.setSigType('CLOCK')
    bp = odb.dbBPin.create(root); bp.setPlacementStatus('FIRM')
    xy = root_xy or tree.get('meta',{}).get('root_um')
    if xy is None:
        roots = [n for n in tree['nodes'].values() if n.get('parent') is None]
        if len(roots) != 1: raise ValueError('cannot resolve unique planned clock root')
        xy = [roots[0]['x'], roots[0]['y']]
    x,y = (round(v*dbu) for v in xy)
    odb.dbBox.create(bp, database.getTech().findLayer('M9'), x-20,y-160,x+20,y+160)
    output = Path(output); output.mkdir(parents=True,exist_ok=True)
    odb.write_db(database,str(output/'clock_native.odb'))
    receipt = dict(schema='opentallas.native_clock_source.v1',status='CONNECTED_UNROUTED',
        clock_cells=len(placed),clock_nets=len(graph['nets']),native_taps=len(endpoint_rows),
        preserved_old_clock_ids=False,provider_imported=False,physical_route=False,timing_qualified=False,
        inputs={k:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
                for k,p in [('target',target),('netlist',netlist),('tree',tree_path)]})
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (output/'endpoints.json').write_text(json.dumps(dict(verdict='CONNECTED_UNROUTED',endpoints=endpoint_rows))+'\n')
    return receipt


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('target','netlist','tree','out'):p.add_argument('--'+key,required=True,type=Path)
    p.add_argument('--legalize-sites',action='store_true');p.add_argument('--site-space',type=Path);p.add_argument('--clock-tcl',type=Path)
    a=p.parse_args(argv);print(json.dumps(build(a.target,a.netlist,a.tree,a.out,legalize=a.legalize_sites,site_space=a.site_space,clock_tcl=a.clock_tcl)))

if __name__=='__main__':main()
