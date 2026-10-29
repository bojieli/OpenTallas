#!/usr/bin/env python3
"""Select one actual measured START capture tap and uniform local pin site per type."""
import argparse,collections,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
import schema as S


def select(plan,proof):
    groups=collections.defaultdict(list)
    for pn,p in plan.parts.items():groups[p['type']].append(pn)
    records=proof['taps'] if 'taps' in proof else proof
    if isinstance(records,list):records={r['port']:r for r in records}
    taps=collections.defaultdict(dict)
    for name,t in records.items():
        if t.get('part') in plan.parts:taps[t['part']][name.split('__')[-1]]=(name,t)
    selected={};sites={};rows=[]
    for tn,parts in sorted(groups.items()):
        common=set.intersection(*(set(taps[p]) for p in parts))
        if not common:raise ValueError(f'{tn}: no type-uniform actual measured tap')
        name=min(common,key=lambda n:(n!='clk',int(n.removeprefix('clk_t')) if n.startswith('clk_t') else 0,n))
        local=[]
        for pn in sorted(parts):
            key,t=taps[pn][name];selected[pn]=key
            xy=t.get('xy_um')
            if xy is None:raise ValueError(f'{pn}: actual tap coordinates missing')
            local.append(plan.to_type(pn,xy))
        if any(max(abs(a-b) for a,b in zip(local[0],q))>0.02 for q in local):
            raise ValueError(f'{tn}.{name}: instance coordinates do not form one type-uniform pin')
        x,y=local[0];w,h=plan.types[tn]['outline_um']
        # Beside the actual clock terminal. Reuse the type's macro-free tap
        # channel; exact mapped origin placement remains a prototype gate.
        sites[tn]=[round(x+(8.64 if x+8.64<w-2.16 else -8.64),4),round(y,4)]
        rows.append(dict(type=tn,tap=name,parts=len(parts),capture_um=sites[tn]))
    raw=copy.deepcopy(plan.raw)
    for tn,xy in sites.items():raw['partition_types'][tn].setdefault('clock',{})['start_capture_um']=xy
    return raw,selected,rows


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan');a.add_argument('proof_taps');a.add_argument('--out',required=True);a=a.parse_args();o=Path(a.out);o.mkdir(parents=True,exist_ok=False)
    p=S.Plan(S.load(a.plan),Path(a.plan));raw,caps,rows=select(p,json.load(open(a.proof_taps)))
    for fn,v in [('plan.json',raw),('capture_taps.json',caps),('sites.json',rows)]: (o/fn).write_text(json.dumps(v,indent=1)+'\n')
    print(json.dumps(rows))
if __name__=='__main__':main()
