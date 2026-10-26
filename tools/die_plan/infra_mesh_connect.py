#!/usr/bin/env python3
"""Land actual vias and transformed cell/port pin access on existing M8/M9 mesh straps.

Run with OpenROAD Python. Existing placed mesh ODB must contain the intended
regional straps and legal driver/stub islands. No placement or netlist changes
are made. A disconnected/shorted result is retained as FAIL and must not route.
  openroad -python infra_mesh_connect.py --source mesh_placed.odb --out connected.odb

Mesh names default to ck_mesh and ck_mesh_r*. All native via definitions must
exist in the source tech. The next step is visual review then infra_clock_route.py.
"""
import argparse
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))


def connect(source,output,mesh_names=None,width_um=None):
    import odb
    from infra_replay import load_db
    from infra_connectivity import check_database,check_basic_clearance
    output=Path(output)
    if output.exists():raise ValueError('use a new output file; preserve prior result')
    db,block=load_db(source);tech=db.getTech();dbu=block.getDbUnitsPerMicron()
    mesh_names=mesh_names or sorted(n.getName() for n in block.getNets()
                                   if n.getName()=='ck_mesh' or n.getName().startswith('ck_mesh_r'))
    if not mesh_names:raise ValueError('no explicit or named mesh nets')
    requested=round(width_um*dbu) if width_um is not None else 0
    if width_um is not None and requested<=0:raise ValueError('positive mesh width required')
    stats={}
    for name in mesh_names:
        net=block.findNet(name)
        if not net:raise ValueError('mesh net missing: '+name)
        horizontal=[];vertical=[];seen=set()
        for wire in net.getSWires():
            for shape in wire.getWires():
                if shape.isVia():
                    via=shape.getTechVia() or shape.getBlockVia()
                    seen.add((via.getName(),tuple(shape.getViaXY())))
                elif shape.getTechLayer().getName()=='M8':
                    horizontal.append((shape.xMin(),shape.yMin(),shape.xMax(),shape.yMax()))
                elif shape.getTechLayer().getName()=='M9':
                    vertical.append((shape.xMin(),shape.yMin(),shape.xMax(),shape.yMax()))
        if not horizontal or not vertical:raise ValueError('mesh requires actual M8/M9 straps: '+name)
        width=max(requested,max(h[3]-h[1] for h in horizontal),max(v[2]-v[0] for v in vertical))
        wire=odb.dbSWire.create(net,'FIXED');new_vias=0;access_segments=0;landings=[]
        def via(level,x,y):
            nonlocal new_vias
            name='VIA'+str(level)+str(level+1);key=(name,(x,y))
            if key in seen:return
            v=tech.findVia(name)
            if not v:raise ValueError('native access via missing: '+name)
            odb.dbSBox.create(wire,v,x,y,'IOWIRE');seen.add(key);new_vias+=1
        def segment(level,a,b):
            nonlocal access_segments
            if a==b:return
            layer=tech.findLayer('M'+str(level));lo=width//2;hi=width-lo
            x0,y0=min(a[0],b[0]),min(a[1],b[1]);x1,y1=max(a[0],b[0]),max(a[1],b[1])
            if a[0]!=b[0] and a[1]!=b[1]:raise ValueError('non-Manhattan access segment')
            odb.dbSBox.create(wire,layer,x0-lo,y0-lo,x1+hi,y1+hi,'IOWIRE');access_segments+=1
        for h in horizontal:
            y=(h[1]+h[3])//2
            for v in vertical:
                x=(v[0]+v[2])//2
                if h[0]<=x<=h[2] and v[1]<=y<=v[3]:via(8,x,y)
        terminals=[]
        for term in net.getITerms():
            terminals.append((term.getInst().getName()+'.'+term.getMTerm().getName(),
                              [(layer,(r.xMin(),r.yMin(),r.xMax(),r.yMax())) for layer,r in term.getGeometries()]))
        for term in net.getBTerms():
            terminals.append(('PORT/'+term.getName(),[(r.getTechLayer(),(r.xMin(),r.yMin(),r.xMax(),r.yMax()))
                              for pin in term.getBPins() for r in pin.getBoxes()]))
        for label,shapes in terminals:
            shapes=[(layer,r) for layer,r in shapes if 0<layer.getRoutingLevel()<=9]
            if not shapes:raise ValueError('terminal has no routing-layer access shape: '+label)
            candidates=[]
            grid=max(1,tech.getManufacturingGrid())
            for layer,r in shapes:
                level=layer.getRoutingLevel()
                # The native first-via enclosure must fit *inside* the actual
                # port metal. Choosing the largest-area pin rectangle alone can
                # select a thin horizontal strip and violate adjacent PG spacing.
                boxes=[]
                if level<9:
                    first=tech.findVia('VIA'+str(level)+str(level+1))
                    if not first:continue
                    boxes=[q for q in first.getBoxes() if q.getTechLayer()==layer]
                    if not boxes:continue
                bx0=min((q.xMin() for q in boxes),default=0);by0=min((q.yMin() for q in boxes),default=0)
                bx1=max((q.xMax() for q in boxes),default=0);by1=max((q.yMax() for q in boxes),default=0)
                xl=math.ceil((r[0]-bx0)/grid)*grid;xh=math.floor((r[2]-bx1)/grid)*grid
                yl=math.ceil((r[1]-by0)/grid)*grid;yh=math.floor((r[3]-by1)/grid)*grid
                if xl>xh or yl>yh:continue
                for h in horizontal:
                    ty=(h[1]+h[3])//2
                    y=min(max(round(ty/grid)*grid,yl),yh)
                    vx=[(v[0]+v[2])//2 for v in vertical if xl<=(v[0]+v[2])//2<=xh]
                    x=min(vx,key=lambda v:abs(v-(xl+xh)//2)) if vx else round(((xl+xh)//2)/grid)*grid
                    x=min(max(x,xl),xh)
                    tx=min(max(x,h[0]+width//2),h[2]-width//2)
                    score=(level,abs(y-ty)+abs(x-tx),-(r[2]-r[0])*(r[3]-r[1]))
                    candidates.append((score,layer,x,y,tx,ty))
            if not candidates:raise ValueError('no native via enclosure fits actual pin: '+label)
            _score,layer,x,y,tx,ty=min(candidates,key=lambda c:c[0])
            level=layer.getRoutingLevel()
            # If the pin is already under its strap, stop the real stack at M8.
            # Otherwise rise to M9, run vertically, and land back onto M8.
            top=8 if y==ty and tx==x and level<=8 else 9
            for k in range(level,top):via(k,x,y)
            if top==9:
                segment(9,(x,y),(x,ty));via(8,x,ty);segment(8,(x,ty),(tx,ty))
            landings.append(dict(terminal=label,pin_layer=layer.getName(),pin_rule='native bottom-via enclosure fully inside actual pin',pin_dbu=[x,y],strap_dbu=[tx,ty]))
        net.setWireType('FIXED')
        for old in net.getSWires():old.setWireType('FIXED')
        stats[name]=dict(access_width_um=width/dbu,native_vias_added=new_vias,access_segments_added=access_segments,landings=landings)
    output.parent.mkdir(parents=True,exist_ok=True)
    odb.write_db(db,str(output));odb.write_def(block,str(output.with_suffix('.def')))
    pg=[n.getName() for n in block.getNets() if str(n.getSigType()) in ('POWER','GROUND')]
    census=check_database(output,list(mesh_names)+pg)
    clearance=check_basic_clearance(output,list(mesh_names)+pg,mesh_names)
    report=dict(schema='opentallas.infra_mesh_connect.v1',verdict='CONNECTED' if census['verdict']=='CONNECTED' and clearance['verdict']=='PASS' else 'FAIL',
                source=str(source),output=str(output),mesh=stats,connectivity=census,basic_clearance=clearance,freeze_qualified=False,
                note='Native mesh vias/pin-access only; review before route; DRC/timing/skew/IR remain separate')
    output.with_suffix('.connect.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['verdict']!='CONNECTED':raise ValueError('mesh/PG physical connectivity, overlap or fixed-metal clearance fails')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--out',required=True)
    p.add_argument('--mesh',action='append');p.add_argument('--width-um',type=float,
                    help='Access width lower bound; never narrower than existing actual straps')
    a=p.parse_args();r=connect(a.source,a.out,a.mesh,a.width_um)
    print('INFRA_MESH_CONNECT',r['verdict'],'no freeze qualification')


if __name__=='__main__':main()
