#!/usr/bin/env python3
"""Analysis-only distributed PDNSim load surrogate on an existing PG database.

Run inside OpenROAD Python. Existing PG wires, vias, bumps and macro instances
are retained. The supplied exact per-instance watts are divided over sample
points on its actual PG terminals; no floorplan or release view is changed.
"""
import argparse, hashlib, json, math
from collections import defaultdict
from pathlib import Path


def points(rects, width, height, pitch):
    nx, ny = max(1, math.ceil(width/pitch)), max(1, math.ceil(height/pitch))
    def near(x,y):
        candidates=[]
        for x0,y0,x1,y1 in rects:
            a,b=(x0+x1)/2,max(y0+.05,min(y1-.05,y))
            if y1-y0 >= .1:
                candidates.append((abs(a-x)+abs(b-y),round(a,6),round(b,6)))
        if not candidates: raise ValueError('no usable M7 PG terminal')
        _,x,y=min(candidates)
        return x,y
    return [near((ix+.5)*width/nx,(iy+.5)*height/ny) for ix in range(nx) for iy in range(ny)]


def main():
    import odb
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--odb',required=True);ap.add_argument('--power',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--pitch',type=float,default=384)
    a=ap.parse_args()
    if not 0<a.pitch<=405:raise ValueError('sampling pitch must be positive and <=405 um')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    power=json.loads(Path(a.power).read_text());power=power.get('parts',power)
    db=odb.dbDatabase.create();odb.read_db(db,a.odb);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
    rows=[];masters={};totals={};orig=[]
    def pg_rects(i,pin):
        it=i.findITerm(pin)
        if not it or not it.getNet():raise ValueError(f'{i.getName()} missing connected {pin}')
        rr=[]
        for mp in it.getMTerm().getMPins():
            for r in mp.getGeometry():
                if r.getTechLayer().getName()=='M7':rr.append(tuple(v/u for v in [r.xMin(),r.yMin(),r.xMax(),r.yMax()]))
        if not rr:raise ValueError(f'{i.getName()} has no M7 {pin} shapes')
        return rr,it.getNet().getName()
    for name,watts in sorted(power.items()):
        i=b.findInst(name)
        if not i:raise ValueError(f'missing power instance {name}')
        if watts<0 or not math.isfinite(watts):raise ValueError('invalid power')
        m=i.getMaster();w,h=m.getWidth()/u,m.getHeight()/u
        vr,vnet=pg_rects(i,'VDD');gr,gnet=pg_rects(i,'VSS')
        samples=points(vr,w,h,a.pitch);n=len(samples);orig.append((name,watts))
        orient=str(i.getOrient());ox,oy=(v/u for v in i.getLocation())
        if orient not in ('R0','MX','MY','R180'):raise ValueError(f'unsupported orientation {orient}')
        def glob(x,y):
            return (ox+(w-x if orient in ('MY','R180') else x),oy+(h-y if orient in ('MX','R180') else y))
        grouped=defaultdict(float)
        for k,(vx,vy) in enumerate(samples):
            # Preserve the exact original sum in the receipt; serialization uses 17 significant digits.
            pw=watts/n if k<n-1 else watts-(watts/n)*(n-1)
            gx,gy=min(((max(r[0]+.05,min(r[2]-.05,vx)),max(r[1]+.05,min(r[3]-.05,vy))) for r in gr),key=lambda p:abs(p[0]-vx)+abs(p[1]-vy))
            vx,vy=glob(vx,vy);gx,gy=glob(gx,gy)
            grouped[(vx,vy,gx,gy)]+=pw
        for (vx,vy,gx,gy),pw in grouped.items():
            key=(round(gx-vx,6),round(gy-vy,6))
            master=masters.setdefault(key,f'OT_PG_LOAD_{len(masters)}')
            rows.append(dict(name=f'ot_pgload_{len(rows)}',parent=name,master=master,vdd=[vx,vy],vss=[gx,gy],power_w=pw,net=vnet,ground=gnet))
        totals[name]=dict(original_w=watts,distributed_w=sum(q['power_w'] for q in rows if q['parent']==name),samples=n,loads=len(grouped))
    lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;']
    for (dx,dy),master in masters.items():
        # Pin-only analysis masters: each terminal lies inside its pre-existing M7 PG shape.
        pad=max(abs(dx),abs(dy))+1
        lef += [f'MACRO {master}',' CLASS BLOCK ;',f' SIZE {2*pad:.6f} BY {2*pad:.6f} ;']
        for pin,kind,x,y in [('VDD','POWER',pad,pad),('VSS','GROUND',pad+dx,pad+dy)]:
            lef += [f' PIN {pin}',' DIRECTION INOUT ;',f' USE {kind} ;',' PORT',' LAYER M7 ;',f' RECT {x-.024:.6f} {y-.024:.6f} {x+.024:.6f} {y+.024:.6f} ;',' END',f' END {pin}']
        lef += [f'END {master}']
    lef+=['END LIBRARY'];lp=out/'loads.lef';lp.write_text('\n'.join(lef)+'\n');odb.read_lef(db,str(lp))
    for r in rows:
        m=db.findMaster(r['master']);pad=m.getWidth()/u/2
        i=odb.dbInst.create(b,m,r['name']);i.setLocation(round((r['vdd'][0]-pad)*u),round((r['vdd'][1]-pad)*u));i.setPlacementStatus('FIRM')
        i.findITerm('VDD').connect(b.findNet(r['net']));i.findITerm('VSS').connect(b.findNet(r['ground']))
    odb.write_db(db,str(out/'distributed.odb'))
    t=[f'set_pdnsim_inst_power -inst {{{n}}} -power 0' for n,w in orig]
    t += [f"set_pdnsim_inst_power -inst {r['name']} -power {r['power_w']:.17g}" for r in rows]
    (out/'power.tcl').write_text('\n'.join(t)+'\n')
    receipt=dict(schema='opentallas.distributed-pg-load.v1',scope='analysis-only surrogate; PG geometry and bumps unchanged',source_odb_sha256=hashlib.sha256(Path(a.odb).read_bytes()).hexdigest(),pitch_um=a.pitch,original_total_w=sum(power.values()),distributed_total_w=sum(r['power_w'] for r in rows),parents=totals,loads=rows)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('parents','loads')},indent=1))

if __name__=='__main__':main()
