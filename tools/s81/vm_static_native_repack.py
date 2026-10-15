#!/usr/bin/env python3
"""Pack actual static VM core hard children on native43.2um origins,20um streets.
Geometry candidate only: source/pin/calendar and view qualification remain separate.
"""
import json, math, random, importlib.util, sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tools/ref_tile'))
spec=importlib.util.spec_from_file_location('rt',R/'tools/ref_tile/ref_tile.py');rt=importlib.util.module_from_spec(spec);spec.loader.exec_module(rt)
P=43.2

def pack(nodes, seed):
    rng=random.Random(seed)
    order=sorted(nodes,key=lambda n:-(math.ceil((n['outline_um'][0]+20)/P)*math.ceil((n['outline_um'][1]+20)/P))*(1+rng.random()*.15))
    free=[(0,0,34,89)]; placed=[]
    for n in order:
        w,h=[math.ceil((v+20-1e-8)/P) for v in n['outline_um']]
        options=[(min(fw-w,fh-h),max(fw-w,fh-h),y,x,j) for j,(x,y,fw,fh) in enumerate(free) if fw>=w and fh>=h]
        if not options:return None
        _,_,y,x,j=min(options); new=[]
        for fx,fy,fw,fh in free:
            if x>=fx+fw or x+w<=fx or y>=fy+fh or y+h<=fy:new.append((fx,fy,fw,fh));continue
            if x>fx:new.append((fx,fy,x-fx,fh))
            if x+w<fx+fw:new.append((x+w,fy,fx+fw-x-w,fh))
            if y>fy:new.append((fx,fy,fw,y-fy))
            if y+h<fy+fh:new.append((fx,y+h,fw,fy+fh-y-h))
        free=[a for i,a in enumerate(new) if not any(i!=j and b[0]<=a[0] and b[1]<=a[1] and b[0]+b[2]>=a[0]+a[2] and b[1]+b[3]>=a[1]+a[3] and (a!=b or j<i) for j,b in enumerate(new))]
        placed.append(dict(n,xy_um=[round((x+1)*P,3),round((y+1)*P,3)]))
    return placed

def main():
    old=R/'physical/s81_die_pins/v20_vm_static_standard/layout_candidate.json';d=json.loads(old.read_text());result=None
    for seed in range(100):
        result=pack(d['nodes'],seed)
        if result:break
    assert result,'no native-lattice fit found'
    nodes=[dict(name=n['name'],master=n['master'],idx=i,kind='child',x=n['xy_um'][0],y=n['xy_um'][1],w=n['outline_um'][0],h=n['outline_um'][1],offtrack=None) for i,n in enumerate(result)]
    checks=rt.floorplan_checks(dict(kind='cluster',pins={f:['pending'] for f in 'NSEW'}),*d['parent_outline_um'],nodes,None)
    assert not any(c[0]=='FAIL' for c in checks),checks
    report=dict(schema='opentallas.s81.static-vm-native-repack.v1',scope='actual164core hard-child geometry only; capture/edge/producer service packing and actual pin/cut/clock/calendar not proved',parent_outline_um=d['parent_outline_um'],nodes=sorted(result,key=lambda n:n['name']),packing_seed=seed,lattice_um=P,channel_min_um=20,hard_children=len(nodes),bank_count=sum(n['master']=='dsfd_vm_static_bank128' for n in result),checks=checks,status='CORE_GEOMETRY_PASS',qualification='UNQUALIFIED pins, real views, clock, crossings, endpoint rate and full parent including edges')
    out=R/'physical/s81_die_pins/v20_vm_static_native';out.mkdir(exist_ok=True);(out/'layout_candidate.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:report[k] for k in ['status','hard_children','bank_count','packing_seed','checks']}))
if __name__=='__main__':main()
