"""Revise a failed fixed clock table at its actual uncovered control sites."""
import argparse,json,sys
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('plan',type=Path);ap.add_argument('types_report',type=Path)
ap.add_argument('out',type=Path);ap.add_argument('--tools',type=Path,required=True)
args=ap.parse_args();sys.path.insert(0,str(args.tools))
import schema as S,taps
raw=json.loads(args.plan.read_text());names=json.loads(args.types_report.read_text())['types']
p=S.Plan(raw);changes={}
for name in names:
    ty=p.types[name];ck=ty['clock'];cap=ck['tap_max_sinks'];radius=ck['tap_radius_um']
    local=[v for v in ck['taps'] if v.get('kind')!='core']
    endpoints=[(v['name'],*v['xy']) for v in local]
    sinks=taps.sink_sites(p,name)
    load,far,assignment=taps.assign(endpoints,sinks,cap,radius,max_distance_um=radius)
    if any(n>cap for n in load):raise ValueError(name+': capacity failure requires a distinct repartition')
    uncovered=[s for s,j in zip(sinks,assignment) if abs(s[0]-endpoints[j][1])+abs(s[1]-endpoints[j][2])>radius+1e-6]
    added=[]
    for x,y,_ in uncovered:
        if min(abs(x-a)+abs(y-b) for _,a,b in endpoints)<=radius:
            continue
        x,y=S.tap_clear(ty,x,y,[(a,b) for _,a,b in endpoints],strict=True)
        port='clk_t'+str(len(endpoints))
        ck['taps'].append(dict(name=port,xy=[x,y],kind='leaf',note='actual uncovered control site; fixed endpoint'))
        endpoints.append((port,x,y));added.append(dict(name=port,xy=[x,y]))
    verified=taps.explicit_taps(p,name)
    if added:changes[name]=dict(added=added,old_max_distance_um=max(far),new_max_distance_um=max(t[4] for t in verified))
args.out.parent.mkdir(parents=True,exist_ok=True)
args.out.write_text(json.dumps(raw,indent=1)+'\n')
args.out.with_suffix('.repair.json').write_text(json.dumps(dict(changes=changes,added_taps=sum(len(v['added']) for v in changes.values()),
    scope='revised seed covers retained actual controller inventory; fresh RESET+START topology still required'),indent=1)+'\n')
print(json.dumps(dict(types_changed=list(changes),added_taps=sum(len(v['added']) for v in changes.values()))),flush=True)
