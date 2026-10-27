#!/usr/bin/env python3
"""Read-only census of the existing METHODOLOGY5.2 60-pins/10um face limit.

PLAN --tools-dir CURRENT_WT/tools/die_plan --out NEW_RECEIPT.json
No builds, routes, plan edits or new rule. Each referenced core table is read once;
partition pins come from the caller's current generator, never a stale directory.
"""
import argparse,collections,hashlib,json,sys
from pathlib import Path

def measure(pins,wh):
    w,h=map(float,wh);pos=collections.defaultdict(list);layers=collections.defaultdict(collections.Counter);names=collections.Counter();duplicates=[]
    for p in pins:
        nm=str(p.get('name',''));sig=str(p.get('sig',p.get('signal_type',''))).upper()
        if sig in ('POWER','GROUND') or nm.upper() in ('VDD','VSS','VCC','GND'):continue
        x,y=float(p['x']),float(p['y']);f='W' if x<2 else 'E' if x>w-2 else 'S' if y<2 else 'N' if y>h-2 else 'area'
        names[nm]+=1;pos[f].append((y if f in ('E','W') else x,nm));layers[f][p.get('layer','?')]+=1
    peaks={}
    for f,arr in pos.items():
        if f=='area':continue
        a=sorted(arr);j=0;best=(0,0,0)
        for i in range(len(a)):
            while a[i][0]-a[j][0]>10.0:j+=1
            if i-j+1>best[0]:best=(i-j+1,j,i)
        count,lo,hi=best;peaks[f]=dict(pins_per_um=count/10,window_pins=count,interval_um=[a[lo][0],a[hi][0]],first_names=[nm for _,nm in a[lo:min(hi+1,lo+5)]])
    return dict(pins=len(names),pin_entries=sum(names.values()),duplicate_names={n:c for n,c in names.items() if c>1},counts_by_face={f:len(a) for f,a in pos.items()},layers_by_face={f:dict(a) for f,a in layers.items()},peaks=peaks,max_pins_per_um=max([a['pins_per_um'] for a in peaks.values()] or [0]),verdict='FAIL' if any(a['window_pins']>60 for a in peaks.values()) else 'PASS')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan');ap.add_argument('--tools-dir');ap.add_argument('--out',required=True);args=ap.parse_args();plan=Path(args.plan).resolve();raw=json.loads(plan.read_text());types=raw['partition_types'];records=[];errors=[];seen={}
    for tn,t in types.items():
        for c in t.get('hard_cores',[]):
            pf=c.get('pins_file');wh=c.get('outline_um')
            if not pf or not wh:
                errors.append(dict(type=tn,inst=c.get('inst'),error='missing pins_file/outline'));continue
            path=(plan.parent/pf).resolve();key=(str(path),tuple(wh))
            if key in seen:
                records[seen[key]]['instances']+=1;continue
            try:
                data=path.read_bytes();pins=json.loads(data)
                if isinstance(pins,dict):pins=pins['pins']
                rec=dict(kind='core',type=c.get('module',path.stem),pins_file=pf,pins_sha256=hashlib.sha256(data).hexdigest(),outline_um=wh,instances=1,**measure(pins,wh));seen[key]=len(records);records.append(rec)
            except Exception as e:errors.append(dict(type=tn,pins_file=pf,error=str(e)))
    if args.tools_dir:
        sys.path.insert(0,str(Path(args.tools_dir).resolve()))
        import schema as S,gen_phys as GP
        p=S.Plan(raw,plan)
        for tn,t in p.types.items():
            try:
                pins=[dict(name=f'{n}[{b}]',layer=layer,x=x,y=y) for n,b,layer,x,y,face in GP.type_pins(p,tn)]
                records.append(dict(kind='partition',type=tn,outline_um=t['outline_um'],**measure(pins,t['outline_um'])))
            except Exception as e:errors.append(dict(kind='partition',type=tn,error=str(e)))
    result=dict(schema='opentallas.pin_window_census.v1',plan=str(plan),plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),rule='METHODOLOGY5.2 <=6pins/um in sliding10um face window; existing rule, report only',method='non-PG pins, combined layers, face tolerance2um; canonical pin centres; duplicated names reported, not discarded',partition_source=args.tools_dir,records=records,errors=errors)
    result['summary']=dict(records=len(records),violations=sum(r['verdict']=='FAIL' for r in records),errors=len(errors));Path(args.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['summary']))
    for r in sorted(records,key=lambda r:-r['max_pins_per_um'])[:20]:print(r['kind'],r['type'],r['verdict'],r['max_pins_per_um'])
    for e in errors[:10]:print('ERROR',json.dumps(e))
if __name__=='__main__':main()
