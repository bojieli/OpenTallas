#!/usr/bin/env python3
"""PATH-S81-PD4 copy of place_phyfit_slots_1026.py (+ lk PHY keepout boxes). Allocate only real new FT stations on legal rows; independent chunks.
Preserve old explicit site arrays. Existing unspecified slots are allocated in the
same wrapper before new slots. A failing type is reported and does not stop peers.
"""
import argparse
import copy
import json
import sys
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan',type=Path);ap.add_argument('--report',type=Path,required=True)
    ap.add_argument('--chunk',type=int,default=0);ap.add_argument('--chunks',type=int,default=1);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--types',help='Allocate only these comma-separated failed types; preserve successful chunks')
    ap.add_argument('--jog',action='append',default=[],help='type/slot=coordinate, reviewed structural path override')
    a=ap.parse_args();jogs={k:float(v) for k,v in (s.split('=') for s in a.jog)}
    root=Path(__file__).resolve().parents[3];sys.path[:0]=[str(root),str(root/'tools/die_plan')]
    import ft_corridor as F
    import numpy as np
    raw=json.loads(a.plan.read_text());rep=json.loads(a.report.read_text());model=F.S.Plan(raw,a.plan);names=sorted(rep['new_slots'])[a.chunk::a.chunks]
    if a.types:names=[tn for tn in names if tn in a.types.split(',')]
    results=[]
    for tn in names:
        t=raw['partition_types'][tn];w,h=t['outline_um'];before=copy.deepcopy(t['ft_slots']);newnames=set(rep['new_slots'][tn]);pins={(b,i):(x,y) for b,i,ln,x,y,d in F.type_pins(model,tn)}
        boxes=[]
        for c in t.get('hard_cores',[]):
            x,y=c['origin_um'];cw,ch=c['outline_um'];dx,dy=c.get('track_offset_um',[0,0]);boxes.append((x+dx-F.KEEPOFF,y+dy-F.KEEPOFF,x+dx+cw+F.KEEPOFF,y+dy+ch+F.KEEPOFF))
        # PD4: published PHY macro keepout (lk_* types) is a hard box for FT stations, same as a hard core
        for k in (t.get("clock") or {}).get("keepouts_um",[]):boxes.append((k[0]-F.KEEPOFF,k[1]-F.KEEPOFF,k[2]+F.KEEPOFF,k[3]+F.KEEPOFF))
        alloc=F.RowAllocator((4.32,4.32,w-4.32,h-4.32),blocked=boxes,cell_size=F.CELL,column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
        # Immutable old explicit sites already have independent reach evidence.
        keep=[s for s in t.get('ft_slots',[]) if s['name'] not in newnames and s.get('bit_sites_um')]
        for slot in keep:
            cw,ch=slot.get('bit_site_cell_um',F.CELL)
            for station in slot['bit_sites_um']:
                for x,y in station:alloc.reserve_rectangle((x,y,x+cw,y+ch))
        toplace=[s for s in t.get('ft_slots',[]) if s not in keep]
        rows=[];failed=None
        for slot in sorted(toplace,key=lambda s:(s['name'] in newnames,-s['width'])):
            width=slot['width']+1;aa=np.array([pins[(slot['name']+'_i',i)] for i in range(width)]);bb=np.array([pins[(slot['name']+'_o',i)] for i in range(width)])
            start=slot['stations'];used=set(alloc.used);last=None
            for extra in range(13):
                slot['stations']=start+extra;alloc.used=set(used)
                try:
                    sites,cents,path,ledger=F.place_slot(slot,aa,bb,slot['in_face'],slot['out_face'],w,h,boxes,alloc,405*.98-2,jog=jogs.get(tn+'/'+slot['name']))
                except (ValueError,F.NoChain) as exc:last=str(exc);continue
                slot['regs_um']=[aa.mean(axis=0).round(4).tolist()]+[c.round(4).tolist() for c in cents]
                slot['bit_site_cell_um']=list(F.CELL);slot['bit_sites_um']=[(points-np.array([F.CELL[0]/2,F.CELL[1]/2])).round(6).tolist() for points in sites]
                ledger.update(slot=slot['name'],type=tn,old_stations=start,final_stations=slot['stations'],new_slot=slot['name'] in newnames);rows.append(ledger);break
            else:failed=dict(slot=slot['name'],reason=last,first_stations=start,last_stations=start+12);break
        if failed:
            t['ft_slots']=before;results.append(dict(type=tn,verdict='FAIL',failure=failed));print(json.dumps(results[-1]),flush=True)
        else:results.append(dict(type=tn,verdict='PASS',slots=rows));print(tn,'PASS',len(rows),'allocated slots',flush=True)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    # A chunk emits only its changed type bodies; merge consumers cannot overwrite
    # another chunk's work or the source plan accidentally.
    result=dict(chunk=a.chunk,chunks=a.chunks,types={tn:raw['partition_types'][tn] for tn in names},results=results)
    a.out.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('RESULT',a.chunk,'PASS',sum(r['verdict']=='PASS' for r in results),'FAIL',sum(r['verdict']=='FAIL' for r in results),flush=True)


if __name__=='__main__':main()
