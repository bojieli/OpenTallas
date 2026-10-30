#!/usr/bin/env python3
"""Keep typed raw producers exact; assign distinct nearby on-track physical M7 export pins."""
import argparse,json,sys
from pathlib import Path

def allocate(raw, stages, S, LC):
    P=S.Plan(raw); users={}
    for st in stages['stages']:
        rs=st.get('reset_source')
        if rs:users.setdefault((rs['type'],rs['port']),[]).append((rs['part'],st['clock_pin_xy_um']))
    report=[]
    for tn,t in raw['partition_types'].items():
        rows=[r for r in t.get('reset_start_raw_exports',[]) if not r.get('existing_port')]
        if not rows:continue
        pins=t['clock']['landing_contract']['pins']; selected={r['port'] for r in rows}
        occupied=[]
        for p in pins:
            if p['name'] not in selected:
                x,y=LC.on_track(P,p['layer'],*p['xy_um']);occupied.append((p['layer'],x,y,p['name']))
        pitch=P.layers['M7']['pitch_um'];w,h=t['outline_um']
        for row in sorted(rows,key=lambda r:r['port']):
            p=next(p for p in pins if p['name']==row['port']);ox,oy=p['xy_um'];sx,sy=LC.on_track(P,'M7',ox,oy)
            cand=[]
            for k,dy in ((k,dy) for k in range(-32,33) for dy in (0.,-.512,.512,-1.024,1.024)):
                x=round(sx+2*k*pitch,4);y=round(oy+dy,4)
                if not .08<=x<=w-.08 or not .216<=y<=h-.216:continue
                if any(S.pg_blocked('M7',x-origin) for origin in (0.,4.32)):continue
                if any(S.pg_blocked('M6',y-origin) for origin in (0.,4.32)):continue
                if any(layer=='M7' and abs(x-a)<.080-1e-6 and abs(y-b)<.432-1e-6 for layer,a,b,_ in occupied):continue
                # A small metal site offset never changes the recorded source flop coordinates/depth.
                source_hop=abs(x-row['xy_um'][0])+abs(y-row['xy_um'][1])
                if source_hop>30:continue
                us=users.get((tn,row['port']),[])
                hops=[abs(P.to_die(pn,(x,y))[0]-xy[0])+abs(P.to_die(pn,(x,y))[1]-xy[1]) for pn,xy in us]
                worst=max(hops,default=0)
                if worst+source_hop>405+1e-6:continue
                cand.append((source_hop,worst,abs(k),x,y))
            if not cand:raise ValueError(f'{tn}.{row["port"]}: no nearby distinct legal pin retaining405um provider reach')
            _,worst,_,x,y=min(cand);p['xy_um']=[x,y];occupied.append(('M7',x,y,p['name']))
            if abs(x-ox)>1e-6 or abs(y-oy)>1e-6:report.append(dict(type=tn,port=p['name'],old=[ox,oy],new=[x,y],source_um=row['xy_um'],max_provider_hop_um=worst,added_cycles=0))
    return report

def main():
    a=argparse.ArgumentParser();a.add_argument('root',type=Path);a.add_argument('plan',type=Path);a.add_argument('stages',type=Path);a.add_argument('--out',type=Path,required=True);a=a.parse_args()
    sys.path.insert(0,str(a.root/'tools/die_plan'));import schema as S,landing_contract as LC
    raw=json.loads(a.plan.read_text());r=allocate(raw,json.loads(a.stages.read_text()),S,LC)
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'source_plan.json').write_text(json.dumps(raw,indent=1)+'\n');(a.out/'pin_site_changes.json').write_text(json.dumps(r,indent=1)+'\n');print('RAW_PIN_SITES',len(r))
if __name__=='__main__':main()
