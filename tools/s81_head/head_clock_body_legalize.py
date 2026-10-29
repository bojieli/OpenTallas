#!/usr/bin/env python3
"""Legalize inherited HEAD clock cells by full LEF body on native ODB rows.

Geometry only: preserve every master, net, cell identity and physical tap. No
arrival, slack or measured latency is an input. New timing proof is required.
"""
import argparse,copy,heapq,json,math,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
import schema as S
import die_trial as D
from start_stage_emit import ctree_cells
from clock_reach import actual_reach
from head_start_sites import Bodies,row_orientation
GX=.054;GY=.27;EPS=1e-6


def dimensions(lef,masters):
    out={}
    for n in masters:
        m=re.search(r'(?ms)^MACRO\s+'+re.escape(n)+r'\b(.*?)^END\s+'+re.escape(n)+r'\b',lef)
        if not m:raise ValueError('actual LEF master missing '+n)
        z=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',m[1]);out[n]=tuple(map(float,z.groups()))
        if abs(out[n][1]-GY)>EPS:raise ValueError('review multi-height clock cell before using one-row occupancy')
    return out


def overlaps(boxes):
    active=[];pairs=[]
    for name,r in sorted(boxes.items(),key=lambda q:(q[1][0],q[0])):
        active=[(n,b) for n,b in active if b[2]>r[0]+EPS]
        for n,b in active:
            if min(r[3],b[3])>max(r[1],b[1])+EPS:pairs.append([n,name])
        active.append((name,r))
    return pairs


def geometry(cells,sites,taps):
    driven={v[2]:n for n,v in cells.items()};edges=[]
    for n,(_,a,_) in cells.items():
        if a in driven:
            p=driven[a];edges.append(dict(kind='cell',src=p,dst=n,um=sum(abs(x-y) for x,y in zip(sites[p],sites[n]))))
    for t in taps:
        d=t.get('driver')
        if d is None:raise ValueError('tap has no actual driver')
        edges.append(dict(kind='tap',src=d,dst=t['port'],um=sum(abs(x-y) for x,y in zip(sites[d],t['xy']))))
    return edges


def regional_spread(tree,sites,mapping):
    lengths={};visiting=set();up=tree['parent_of']
    def length(n):
        if n in lengths:return lengths[n]
        if n in visiting:raise ValueError('clock topology cycle')
        visiting.add(n);p=up.get(n)
        lengths[n]=(length(p)+sum(abs(a-b) for a,b in zip(sites[n],sites[p]))) if p else 0.
        visiting.remove(n);return lengths[n]
    groups={}
    for t in tree['taps']:
        d=t['driver'];v=length(d)+sum(abs(a-b) for a,b in zip(sites[d],t['xy']))
        groups.setdefault(mapping[t['part']],[]).append(v)
    return {n:round(max(v)-min(v),6) for n,v in groups.items()}


def legalize(plan,cells,old,dim,max_move=8.64):
    site=D.SiteMap(plan);site.in_part((0.,0.));occupied=Bodies();new={};moves=[]
    def body_legal(x,y,w,h):
        if not any(r[0]+.5<=x and r[1]+.5<=y and x+w<=r[2]-.5 and y+h<=r[3]-.5
                   for r in site._pidx.get((int((x+w/2)//site.b),int((y+h/2)//site.b)),())):return False
        seen=set()
        for i in range(math.floor(x/site.b),math.floor((x+w)/site.b)+1):
            for j in range(math.floor(y/site.b),math.floor((y+h)/site.b)+1):
                for k in site.idx.get((i,j),()):
                    if k in seen:continue
                    seen.add(k);r=site.forb[k]
                    if min(x+w,r[2])>max(x,r[0])+EPS and min(y+h,r[3])>max(y,r[1])+EPS:return False
        return True
    for name,(master,_,_) in cells.items():
        x,y=old[name];w,h=dim[master];ix=int(round(x/GX));iy=int(round(y/GY));q=[];seen=set()
        def add(i,j):
            if (i,j) in seen:return
            seen.add((i,j));xx=round(i*GX,6);yy=round(j*GY,6);d=abs(xx-x)+abs(yy-y)
            if d<=max_move+EPS:heapq.heappush(q,(d,i,j,xx,yy))
        add(ix,iy)
        while q:
            distance,i,j,xx,yy=heapq.heappop(q)
            if body_legal(xx,yy,w,h) and occupied.free(xx,xx+w,yy):
                new[name]=[xx,yy];occupied.add(xx,xx+w,yy)
                if distance>EPS:moves.append(dict(cell=name,old_xy_um=[x,y],xy_um=[xx,yy],distance_um=round(distance,6)))
                break
            for a,b in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):add(a,b)
        else:raise ValueError(f'{name}: no full-body row site within the existing8.64-um clock-island neighborhood')
    boxes={n:[*xy,xy[0]+dim[cells[n][0]][0],xy[1]+dim[cells[n][0]][1]] for n,xy in new.items()}
    bad=overlaps(boxes)
    if bad:raise ValueError('independent full-XY overlap census failed '+str(bad[:3]))
    return new,moves,boxes


def main():
    a=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','v','tcl','tree','lef','regions','proof','stages','out'):a.add_argument('--'+n,required=True)
    z=a.parse_args();out=Path(z.out);out.mkdir(parents=True,exist_ok=False)
    ver=Path(z.v).read_text();tcl=Path(z.tcl).read_text();cells,old=ctree_cells(ver,tcl);tree=json.load(open(z.tree));dim=dimensions(Path(z.lef).read_text(),{r[0] for r in cells.values()})
    if set(cells)!=set(old):raise ValueError('ctree placement does not cover actual cell inventory')
    if set(old)!=set(tree['sites']):raise ValueError('tree sites differ from actual netlist/Tcl cell identities')
    P=S.Plan(S.load(z.plan),Path(z.plan));mapping=json.load(open(z.regions))['part_region']
    before_boxes={n:[*xy,xy[0]+dim[cells[n][0]][0],xy[1]+dim[cells[n][0]][1]] for n,xy in old.items()}
    oldpairs=overlaps(before_boxes);new,moves,boxes=legalize(P,cells,old,dim)
    # Keep place_inst syntax compatible with existing die clock importers. Native
    # row parity/orientation is from the measured ODB ROW_0=R0,ROW_1=MX authority.
    def placement(m):
        n=m[1];x,y=new[n];ori=row_orientation(y)
        return f'place_inst -name {n} -location {{{x:.6f} {y:.6f}}} -orientation {ori} -status FIRM'
    tcl,n=re.subn(r'place_inst -name (\S+) -location \{[-\d.]+ [-\d.]+\}[^\n]*',placement,tcl)
    if n!=len(cells):raise ValueError('did not update every actual clock-cell placement')
    tree=copy.deepcopy(tree);tree['sites']=new
    for nid,nd in tree['nodes'].items():
        cell=tree['node_buf'][str(nid)];nd['x'],nd['y']=new[cell]
    b=geometry(cells,old,tree['taps']);after=geometry(cells,new,tree['taps']);over=[e for e in after if e['um']>405+EPS]
    if over:raise ValueError('actual clock reach fails after geometry legalization '+str(over[:2]))
    old_sp=regional_spread(tree,old,mapping);new_sp=regional_spread(tree,new,mapping)
    changes={n:round(new_sp[n]-old_sp[n],6) for n in old_sp}
    tree['meta']['wire_um']=round(sum(e['um'] for e in after),3)
    tree['meta']['geometry_legalization']=dict(native_site_um=[GX,GY],row_orient='even R0 / odd MX',full_body=True,timing_status='NOT RUN: fresh GRT/proof required')
    proof=json.load(open(z.proof));nc=proof['node_cell'];missing=[n for n,c in nc.items() if c not in new]
    if missing:raise ValueError('proof node has no actual clock cell '+str(missing[:3]))
    pg=dict(node_cell=nc,node_xy_um={n:new[c] for n,c in nc.items()},node_stages=proof['node_stages'],
        status='GEOMETRY ONLY; old timing arrays intentionally omitted; rebuild measured proof after GRT')
    stages=json.load(open(z.stages))
    for st in stages['stages']:
        n=st['node_cell'];dx,dy=[new[n][k]-old[n][k] for k in range(2)]
        st['node_xy_um']=new[n];st['clock_pin_xy_um']=[round(st['clock_pin_xy_um'][0]+dx,6),round(st['clock_pin_xy_um'][1]+dy,6)]
        r=st['rect_um'];st['rect_um']=[round(r[0]+dx,6),round(r[1]+dy,6),round(r[2]+dx,6),round(r[3]+dy,6)]
        if st.get('reset_source'):
            st['reset_hop_um']=round(sum(abs(v-w) for v,w in zip(st['clock_pin_xy_um'],st['reset_source']['xy_um'])),6)
    stages['geometry_status']='new legal clock-node anchors; actual full-cell packing and fresh measured phase required'
    # Standalone diagnostic t_st ports follow their node anchors. Physical735
    # partition taps and the root pad remain fixed. The actual overlay removes
    # diagnostic t_st ports and replaces them with real FF/driver loads.
    for st in stages['stages']:
        p=st['clock_port'];x,y=st['clock_pin_xy_um'];pat=r'(place_pin -pin_name '+re.escape(p)+r' -layer \S+ -location )\{[-\d.]+ [-\d.]+\}'
        tcl,k=re.subn(pat,lambda m:m[1]+f'{{{x:.6f} {y:.6f}}}',tcl)
        if k!=1:raise ValueError('missing stage clock diagnostic pin '+p)
    report=dict(cells=len(cells),physical_taps=len(tree['taps']),input_clock_body_overlaps=len(oldpairs),output_clock_body_overlaps=0,
        moved=len(moves),max_move_um=max(r['distance_um'] for r in moves),cell_and_tap_edges=len(after),max_clock_hop_um=max(e['um'] for e in after),
        wire_um_before=sum(e['um'] for e in b),wire_um_after=sum(e['um'] for e in after),
        max_regional_geometric_spread_before_um=max(old_sp.values()),max_regional_geometric_spread_after_um=max(new_sp.values()),
        max_regional_geometric_spread_change_um=max(abs(v) for v in changes.values()),regional_spread_changes_um=changes,
        topology='unchanged exact Verilog; cell/port identities and735physicaltap locations retained',timing='NOT RUN; old phase and CA origins are stale',moves=moves)
    (out/'ctree.v').write_text(ver);(out/'ctree.tcl').write_text(tcl)
    for fn,obj in [('tree.json',tree),('proof_geometry.json',pg),('start_stages_geometry.json',stages),('report.json',report),('actual_reach.json',actual_reach(tree,405)),('clock_bodies.json',boxes)]:
        (out/fn).write_text(json.dumps(obj,indent=1)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('moves','regional_spread_changes_um')}))
if __name__=='__main__':main()
