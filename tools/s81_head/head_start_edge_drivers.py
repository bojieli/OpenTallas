#!/usr/bin/env python3
"""Give each planned START branch a local driver and <=180um wire segments.

Uniform structural isolation fixes small mapped Q-restoration inverters driving
multiple long branches. No timing numbers select cells or sites: one BUFx8 per
branch source plus geometrically spaced repeaters, actual LEF bodies and the
plan/clock/start occupancy decide sites. Logical cycles and FF inventory stay
unchanged. Data-vs-clock phase must be remeasured on the built successor.
"""
import argparse,copy,json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/die_plan'));sys.path.insert(0,str(ROOT/'tools/s81_head'))
import schema as S,die_trial as D,start_stage_emit as E
from head_start_pack import lef_sizes
from head_start_sites import Bodies,row_orientation
MASTER='BUFx8_ASAP7_75t_R'
SEGMENT=180.0


def man(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])

def build(mapped,top,stages,physical,plan,ctree_v,ctree_tcl,sizes):
    out=copy.deepcopy(mapped);mod=out['modules'][top];ph=copy.deepcopy(physical)
    cells=mod['cells'];ports=mod['ports'];rows=Bodies();site=D.SiteMap(plan);w,h=sizes[MASTER]
    if h>E.ROW_UM+1e-6:raise ValueError('driver must fit one actual row')
    for c in ph['cells'].values():
        x,y=c['xy_um'];cw,ch=sizes[c['cell']];rows.add(x,x+cw,y)
    clk,xy=E.ctree_cells(ctree_v,ctree_tcl)
    for n,(typ,_,_) in clk.items():x,y=xy[n];rows.add(x,x+sizes[typ][0],y)
    maximum=max(b for c in cells.values() for v in c['connections'].values() for b in v if isinstance(b,int))
    maximum=max(maximum,max(b for p in ports.values() for b in p['bits'] if isinstance(b,int)))
    def fresh():
        nonlocal maximum
        maximum+=1;return maximum
    def place(anchor):
        ax=round(anchor[0]/.054)*.054;ay=round(anchor[1]/E.ROW_UM)*E.ROW_UM
        # Geometry-only local row/site search; maximum11um y and14um x.
        for row in range(40):
            for sign in ((0,) if row==0 else (1,-1)):
                y=round(ay+sign*row*E.ROW_UM,3)
                for col in range(27):
                    for side in ((1,) if col==0 else (1,-1)):
                        x=round(ax+side*col*.54,3)
                        if not rows.free(x,x+w,y):continue
                        if all(site.legal((xx,yy)) for xx in (x,x+w/2,x+w) for yy in (y,y+h)):
                            rows.add(x,x+w,y);return [x,y]
        raise ValueError(f'no complete driver body near {anchor}')
    def centre(name):
        q=ph['cells'][name];x,y=q['xy_um'];cw,ch=sizes[q['cell']];return [x+cw/2,y+ch/2]
    bits={s['id']:mod['netnames']['st_'+s['id']+'_start']['bits'][0] for s in stages['stages']}
    byreg={s['region']:s for s in stages['stages']};drivers={}
    for name,c in list(cells.items()):
        for pin,bs in c['connections'].items():
            if c.get('port_directions',{}).get(pin)=='output':
                for b in bs:
                    if b in bits.values():
                        if b in drivers:raise ValueError('multiple actual source drivers')
                        drivers[b]=name
    if set(drivers)!=set(bits.values()):raise ValueError('START output lacks actual source cell')
    branches=[]
    for dst in stages['stages']:
        if dst['parent'] is None:continue
        src=byreg[dst['parent']];bit=bits[src['id']];targets=[]
        for n,c in cells.items():
            q=ph['cells'].get(n)
            if not q or q['stage']!=dst['id']:continue
            for pin,conn in c['connections'].items():
                if c.get('port_directions',{}).get(pin)=='input' and bit in conn:targets.append((n,pin))
        if not targets:raise ValueError('declared START edge has no actual mapped capture')
        target=centre(targets[0][0])
        branches.append(dict(src=src['id'],dst=dst['id'],bit=bit,targets=targets,xy=target))
    for d in stages['die_outputs']:
        branches.append(dict(src=d['stage'],dst=d['net'],bit=bits[d['stage']],targets=[],port=d['net'],xy=ph['ports'][d['net']]['xy_um']))
    records=[]
    for ordinal,b in enumerate(branches):
        src=centre(drivers[b['bit']]);dst=b['xy'];distance=man(src,dst)
        paths=[]
        for corner in ([dst[0],src[1]],[src[0],dst[1]]):
            chain=[src,corner,dst];points=[]
            total=man(src,corner)+man(corner,dst);steps=max(1,math.ceil(total/SEGMENT))
            for k in range(steps):
                at=k*total/steps
                if at<=man(src,corner):
                    delta=at;point=[src[0]+(1 if corner[0]>=src[0] else -1)*delta,src[1]] if src[1]==corner[1] else [src[0],src[1]+(1 if corner[1]>=src[1] else -1)*delta]
                else:
                    delta=at-man(src,corner);point=[corner[0]+(1 if dst[0]>=corner[0] else -1)*delta,corner[1]] if corner[1]==dst[1] else [corner[0],corner[1]+(1 if dst[1]>=corner[1] else -1)*delta]
                points.append(point)
            # Prefer a polyline whose repeater homes are already free of hard cores.
            score=sum(not site.legal(p) for p in points)
            paths.append((score,points))
        score,points=min(paths,key=lambda q:q[0])
        detour=False
        if score:
            poly=D.legal_detour(site,src,dst,step=5.4,margin=400.0)
            if poly is None:raise ValueError(f'no macro-free driver corridor {b["src"]}->{b["dst"]}')
            _,length=D.polyline_points(poly,[])
            steps=max(1,math.ceil(length/SEGMENT))
            points,_=D.polyline_points(poly,[k/steps for k in range(steps)])
            detour=True
        previous=b['bit'];locations=[]
        for k,point in enumerate(points):
            loc=place(point);name=f'u_st_{b["src"]}.branch_{ordinal}_{k}'
            nbit=fresh();cells[name]=dict(type=MASTER,parameters={},attributes={},port_directions={'A':'input','Y':'output'},connections={'A':[previous],'Y':[nbit]})
            ph['cells'][name]=dict(cell=MASTER,stage=b['src'],xy_um=loc,rect_um=loc+[round(loc[0]+w,3),round(loc[1]+h,3)],orient=row_orientation(loc[1]),branch=b['dst'])
            previous=nbit;locations.append([loc[0]+w/2,loc[1]+h/2])
        for n,pin in b['targets']:cells[n]['connections'][pin]=[previous if v==b['bit'] else v for v in cells[n]['connections'][pin]]
        if 'port' in b:ports[b['port']]['bits']=[previous]
        hops=[man(a,c) for a,c in zip(locations,locations[1:]+[dst])]
        # Source isolation buffers are local to their real mapped driver.
        if man(src,locations[0])>40 or max(hops)>210:
            raise ValueError(f'branch driver placement exceeds prebuild segment budget: {b["src"]}->{b["dst"]} {hops}')
        records.append(dict(src=b['src'],dst=b['dst'],source_distance_um=distance,driver_sites=locations,max_segment_um=max(hops),buffers=len(points),macro_channel_detour=detour))
    report=dict(scope='prebuild uniform per-branch buffering, no data/clock timing claim',master=MASTER,source_max_cap_ff=368.64,wire_cap_ff_per_um=.187426,
                target_segment_um=SEGMENT,accepted_actual_segment_um=210,branches=len(records),buffers=sum(x['buffers'] for x in records),
                max_segment_um=max(x['max_segment_um'] for x in records),worst_wire_cap_ff=max(x['max_segment_um'] for x in records)*.187426,
                logical_cycles_added=0,flops_added=0,rows=records)
    return out,ph,report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('mapped','top','stages','physical','plan','ctree','lef','out'):p.add_argument('--'+n,required=True)
    a=p.parse_args();o=Path(a.out);o.mkdir(parents=True,exist_ok=False)
    raw=json.load(open(a.plan));r=build(json.load(open(a.mapped)),a.top,json.load(open(a.stages)),json.load(open(a.physical)),S.Plan(raw,Path(a.plan)),(Path(a.ctree)/'ctree.v').read_text(),(Path(a.ctree)/'ctree.tcl').read_text(),lef_sizes(Path(a.lef).read_text()))
    for n,d in zip(('mapped','physical','report'),r):(o/(n+'.json')).write_text(json.dumps(d,indent=1))
    print(json.dumps({k:v for k,v in r[2].items() if k!='rows'}))
if __name__=='__main__':main()
