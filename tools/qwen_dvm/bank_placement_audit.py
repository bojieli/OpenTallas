#!/usr/bin/env python3
"""Run with OpenROAD -python after actual placement/CTS, never on a rectangle model.

DVM_ODB and DVM_AUDIT_OUT select the immutable input/output. Net-cut demand is
an actual placed lower bound, not a routed capacity proof or route admission.
"""
import json
import os
import re
from collections import defaultdict
from pathlib import Path
import odb

db = odb.dbDatabase.create()
odb.read_db(db, os.environ['DVM_ODB'])
b = db.getChip().getBlock()
dbu = b.getDbUnitsPerMicron()
die = b.getDieArea()
fail = []
regions = []
for region in b.getRegions():
    if not re.fullmatch(r'dvm_local_bank_[0-7]', region.getName()):
        continue
    boxes = region.getBoundaries()
    box = boxes[0]
    bounds = [box.xMin(), box.yMin(), box.xMax(), box.yMax()]
    cells = list(region.getGroups()[0].getInsts())
    area = 0
    bad = []
    for i in cells:
        m = i.getMaster()
        area += m.getWidth()*m.getHeight()
        xy = i.getBBox()
        if xy.xMin()<bounds[0] or xy.yMin()<bounds[1] or xy.xMax()>bounds[2] or xy.yMax()>bounds[3]:
            bad.append(i.getName())
    if bad:
        fail.append(f'{region.getName()}: {len(bad)} actual cells outside fence')
    regions.append(dict(name=region.getName(), box_um=[v/dbu for v in bounds],
                        cells=len(cells), cell_area_um2=area/dbu**2,
                        outside=bad[:20]))
if len(regions)!=8:
    fail.append(f'expected8 actual bank regions; got{len(regions)}')

# Re-trace the placed *data* cones after resizing/CTS as well. This catches
# new buffers outside the original groups, rather than inspecting group labels
# alone. Clock trees are deliberately excluded from a data locality test.
region_by_key={int(r['name'].rsplit('_',1)[1]):r for r in regions}
roots=defaultdict(list)
for inst in b.getInsts():
    m=re.search(r'g_t\[([01])\].*g_bank\[([0-3])\].*(?:result_q|u_bank/q)\[([0-9]+)\]',inst.getName().replace('\\',''))
    if m and re.search('DFF|SDFF|LATCH',inst.getMaster().getName()):
        roots[int(m[1])*4+int(m[2])].append(inst)
cones=[]
cone_owner={}
for k,rr in sorted(roots.items()):
    queue=list(rr);root_names={r.getName() for r in rr};seen=set();outside=[];shared=[]
    while queue:
        i=queue.pop();name=i.getName()
        if name in seen:continue
        if re.search('TIE(HI|LO)|TIE[01]|LOGIC[01]',i.getMaster().getName(),re.I):continue
        seen.add(name)
        if name in cone_owner and cone_owner[name]!=k:shared.append(name)
        cone_owner[name]=k
        xy=i.getBBox();r=region_by_key[k]['box_um']
        if xy.xMin()/dbu<r[0] or xy.yMin()/dbu<r[1] or xy.xMax()/dbu>r[2] or xy.yMax()/dbu>r[3]:outside.append(name)
        seq=bool(re.search('DFF|SDFF|LATCH',i.getMaster().getName()))
        if seq and name not in root_names:continue
        for it in i.getITerms():
            mt=it.getMTerm()
            if mt.getIoType()!='INPUT' or mt.getSigType()=='CLOCK':continue
            if seq and mt.getName().upper() not in ('D','DATA'):continue
            net=it.getNet()
            if net:
                queue.extend(d.getInst() for d in net.getITerms() if d.getMTerm().getIoType()=='OUTPUT')
    if len(rr)!=17 or outside or shared:fail.append(f'bank{k}: roots{len(rr)} outside{len(outside)} shared{len(shared)} after placement/CTS')
    cones.append(dict(bank=k,roots=len(rr),actual_cone_cells=len(seen),outside=outside[:20],shared=shared[:20]))
if len(cones)!=8:fail.append(f'expected8 placed data cones; got{len(cones)}')

# Actual track locations from the ODB, not a guessed technology pitch. M2/M4
# horizontal wires do not add capacity to the horizontal (N/S) cuts below.
tracks = {}
horizontal_tracks={}
for layer in db.getTech().getLayers():
    if layer.getName() in ('M2','M4'):
        horizontal_tracks[layer.getName()]=[int(y) for y in b.findTrackGrid(layer).getGridY() if die.yMin()<=y<=die.yMax()]
    if layer.getName() not in ('M3','M5'):
        continue
    grid = b.findTrackGrid(layer)
    tracks[layer.getName()] = [int(x) for x in grid.getGridX() if die.xMin()<=x<=die.xMax()]

nets = []
net_points=[]
for net in b.getNets():
    if net.getSigType() in ('POWER','GROUND'):
        continue
    points = []
    for it in net.getITerms():
        xy = it.getAvgXY()
        if xy[0]:
            points.append((xy[1],xy[2]))
    for bt in net.getBTerms():
        for bp in bt.getBPins():
            for box in bp.getBoxes():
                points.append(((box.xMin()+box.xMax())/2,(box.yMin()+box.yMax())/2))
    if len(points)>1:
        net_points.append((net.getName(),points))
        nets.append((net.getName(),min(p[1] for p in points),max(p[1] for p in points)))

routing_adjustment=float(os.environ.get("DVM_ROUTING_LAYER_ADJUSTMENT","0.25"))
if not 0<=routing_adjustment<1:raise ValueError("invalid routing layer adjustment")
cuts = []
ordered_regions=sorted(regions,key=lambda r:r['box_um'][1])
cut_ys=[(r['box_um'][1]+r['box_um'][3])/2 for r in ordered_regions]
cut_ys += [(a['box_um'][3]+c['box_um'][1])/2 for a,c in zip(ordered_regions,ordered_regions[1:])]
for y_um in sorted(set(cut_ys)):
    y = round(y_um*dbu)
    crossing = [name for name,lo,hi in nets if lo<y<hi]
    # Fixed PG special wires and actual block obstructions can consume tracks.
    # Master OBS are also counted at this cut. Pin metal is audited separately.
    blocked = defaultdict(set)
    def obstruct(layer,x0,y0,x1,y1):
        if layer not in tracks or not y0<=y<=y1:
            return
        for x in tracks[layer]:
            if x0<=x<=x1:
                blocked[layer].add(x)
    for obs in b.getObstructions():
        box = obs.getBBox()
        obstruct(box.getTechLayer().getName(),box.xMin(),box.yMin(),box.xMax(),box.yMax())
    for net in b.getNets():
        if net.getSigType() not in ('POWER','GROUND'):
            continue
        for sw in net.getSWires():
            for box in sw.getWires():
                layer=box.getTechLayer()
                if layer:
                    obstruct(layer.getName(),box.xMin(),box.yMin(),box.xMax(),box.yMax())
    # Conservative master OBS transform: this design has standard cells only.
    # Use their full placed bbox for any M3/M5 obstruction, avoiding optimistic
    # treatment of rotated offsets or unexamined macro interiors.
    for i in b.getInsts():
        xy=i.getBBox()
        if not xy.yMin()<=y<=xy.yMax():
            continue
        for obs in i.getMaster().getObstructions():
            layer=obs.getTechLayer()
            if layer and layer.getName() in tracks:
                obstruct(layer.getName(),xy.xMin(),xy.yMin(),xy.xMax(),xy.yMax())
    available=sum(len(xs)-len(blocked[l]) for l,xs in tracks.items())
    derated_available=available*(1-routing_adjustment)
    cuts.append(dict(y_um=y_um, placed_net_crossing_lower_bound=len(crossing),
                     available_vertical_tracks=available,
                     blocked_tracks={l:len(blocked[l]) for l in tracks},
                     lower_bound_util=len(crossing)/available if available else None,
                     derated_available_vertical_tracks=derated_available,
                     lower_bound_util_derated=len(crossing)/derated_available if derated_available else None,
                     largest_names=crossing[:12]))

# An admission screen requires explicit20% residual margin after the actual
# platform routing adjustment. Actual global-route/via access still required.
for c in cuts:
    if c['lower_bound_util_derated'] is None or c['lower_bound_util_derated']>0.80:
        fail.append(f"cut y={c['y_um']:.3f}: actual demand{c['placed_net_crossing_lower_bound']} lacks20% margin in derated track estimate")

# Also screen both directions *inside each bank*. A whole-die cut alone
# can hide a bank with too little horizontal routing capacity. These bbox
# demands deliberately overcount nets that can escape a bank rectangle;
# neither a low value nor pin-box nonoverlap proves actual via access.
local_cuts=[]
for r in regions:
    x0,y0,x1,y1=[round(v*dbu) for v in r['box_um']]
    cx,cy=(x0+x1)/2,(y0+y1)/2
    vnames=[];hnames=[]
    for name,points in net_points:
        inside=[(x,y) for x,y in points if x0<=x<=x1 and y0<=y<=y1]
        if not inside:continue
        xs=[x for x,y in points];ys=[y for x,y in points]
        if min(xs)<cx<max(xs):vnames.append(name)
        if min(ys)<cy<max(ys):hnames.append(name)
    hcap=sum(sum(y0<=y<=y1 for y in ys) for ys in horizontal_tracks.values())
    vcap=sum(sum(x0<=x<=x1 for x in xs) for xs in tracks.values())
    local_cuts.append(dict(bank=r['name'],vertical_cut_horizontal_tracks_raw=hcap,
        vertical_cut_bbox_demand=len(vnames),horizontal_cut_vertical_tracks_raw=vcap,
        horizontal_cut_bbox_demand=len(hnames),
        vertical_cut_bbox_util=len(vnames)/hcap if hcap else None,
        horizontal_cut_bbox_util=len(hnames)/vcap if vcap else None))

pins=[]
for bt in b.getBTerms():
    for bp in bt.getBPins():
        for box in bp.getBoxes():
            pins.append((bt.getName(),box.getTechLayer().getName(),box.xMin(),box.yMin(),box.xMax(),box.yMax()))
pin_overlaps=[]
for j,a in enumerate(pins):
    for c in pins[j+1:]:
        if a[0]!=c[0] and a[1]==c[1] and max(a[2],c[2])<min(a[4],c[4]) and max(a[3],c[3])<min(a[5],c[5]):
            pin_overlaps.append([a[0],c[0],a[1]])
if pin_overlaps:
    fail.append(f'{len(pin_overlaps)} distinct signal pin box overlaps')
result=dict(schema='opentallas.qwen.dvm.actual_bank_placement.v1',odb=os.environ['DVM_ODB'],
            die_um=[die.xMin()/dbu,die.yMin()/dbu,die.xMax()/dbu,die.yMax()/dbu],
            routing_layer_adjustment=routing_adjustment,
            adjustment_source='Actual ORFS ASAP7 platform config.mk default0.25; override must match run config',
            clock_pin_boxes=[dict(pin=p[0],layer=p[1],box_um=[v/dbu for v in p[2:]]) for p in pins if p[0] in ('clk','ck')],
            actual_cell_area_um2=sum(i.getMaster().getWidth()*i.getMaster().getHeight()/dbu**2 for i in b.getInsts()),
            actual_flop_count=sum(bool(re.search('DFF|SDFF|LATCH',i.getMaster().getName())) for i in b.getInsts()),
            regions=regions,placed_data_cones=cones,local_bank_cuts=local_cuts,horizontal_tracks={l:len(ys) for l,ys in horizontal_tracks.items()},tracks={l:len(xs) for l,xs in tracks.items()},cuts=cuts,
            pin_box_count=len(pins),pin_overlaps=pin_overlaps[:50],
            placement_screen_pass=not fail,fail=fail,route_admitted=False,
            limits='Actual placed cut demand is a lower bound; detailed via access and actual global-route congestion remain required. No routed OBS/export qualification.')
Path(os.environ['DVM_AUDIT_OUT']).write_text(json.dumps(result,indent=1)+'\n')
print(json.dumps({k:result[k] for k in ['placement_screen_pass','fail','tracks','pin_box_count','route_admitted']}))

if fail:
    raise SystemExit(1)
