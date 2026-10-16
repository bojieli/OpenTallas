#!/usr/bin/env python3
"""Build a candidate spec tree with explicit SFU relay depth; never alter pinned S.

Owner geometry instruction: H-SU 2026-10-16 02:20 item6 and grant818f005b6.
This emits source geometry only, not cost/native/physical qualification.
"""
import argparse,copy,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',default='a89a10d1f');ap.add_argument('--r',type=int,default=23);ap.add_argument('--out-specs',type=Path,required=True);a=ap.parse_args()
    if a.r<1 or a.r>99:raise ValueError('Explicit relay depth must be1..99')
    out=a.out_specs.resolve();out.mkdir(parents=True,exist_ok=False)
    prefix='tools/hbm_die_v15/v16_specs'
    names=subprocess.check_output(['git','ls-tree','--name-only',a.base+':'+prefix],cwd=ROOT,text=True).splitlines()
    for name in names:
        if name.endswith('.json'):
            (out/name).write_bytes(subprocess.check_output(['git','show',a.base+':'+prefix+'/'+name],cwd=ROOT))
    p=out/'su_sfu.json';s=json.loads(p.read_text());rx=re.compile(r'^(sfr_(?:SW|SE|NW|NE)[0-3]_[fb])(\d{2})$')
    groups={}
    for i in s['instances']:
        m=rx.fullmatch(i['name'])
        if m:groups.setdefault(m[1],[]).append(i)
    if len(groups)!=32:raise ValueError('Source must have16forward/16return SFU chains')
    depth={k:len(v) for k,v in groups.items()}
    if set(depth.values())!={11}:raise ValueError('Source is not the expected pinned R11 baseline')
    oldnames={i['name'] for g in groups.values() for i in g}
    instances=[i for i in s['instances'] if i['name'] not in oldnames]
    for g,old in sorted(groups.items()):
        for n in range(a.r):
            i=copy.deepcopy(min(old,key=lambda x:x['name']));i['name']=g+f'{n:02d}';i['slot']=None
            i['note']=f'UNQUALIFIED explicit R{a.r} SFU relay candidate from {a.base}; LG_PATH={a.r+1}; fixed stream stage; no inherited physical home'
            instances.append(i)
    for i in instances:
        if i['name'].startswith('sfucore_'):i['params']['LG_PATH']=a.r+1
    edges=[]
    for e in s['edges']:
        sm,dm=rx.fullmatch(e['src'][0]),rx.fullmatch(e['dst'][0])
        if sm and dm:
            if sm[1]!=dm[1] or int(dm[2])!=int(sm[2])+1:raise ValueError('Unexpected source relay cross/tap')
            continue
        e=copy.deepcopy(e)
        if sm:
            if int(sm[2])!=10:raise ValueError('Unexpected interior relay output consumer')
            e['src'][0]=sm[1]+f'{a.r-1:02d}'
        if dm and int(dm[2])!=0:raise ValueError('Unexpected interior relay input producer')
        edges.append(e)
    for g in sorted(groups):
        for n in range(a.r-1):
            edges.append(dict(src=[g+f'{n:02d}','o'],dst=[g+f'{n+1:02d}','i'],bits=624,clock='stream',basis=f'Literal registered SFU chain R{a.r}; compiler LG_PATH={a.r+1}; no runtime extension'))
    clocks=[c for c in s['clocks'] if c['inst'] not in oldnames]
    for g,old in sorted(groups.items()):
        proto=[c for c in s['clocks'] if c['inst']==g+'00']
        if not proto:raise ValueError('Missing relay clock/reset metadata')
        for n in range(a.r):
            for c in proto:
                v=copy.deepcopy(c);v['inst']=g+f'{n:02d}';clocks.append(v)
    s.update(instances=instances,edges=edges,clocks=clocks)
    s['candidate']=dict(base_source=a.base,R=a.r,LG_PATH=a.r+1,adopted=False,native=False,physical=False,cycle_cost_measured=False)
    p.write_text(json.dumps(s,indent=1)+'\n')
    summary=dict(base=a.base,R=a.r,LG_PATH=a.r+1,relay_cells=32*a.r,added_relay_cells=32*(a.r-11),payload_FF=32*a.r*624,added_payload_FF=32*(a.r-11)*624,status='CANDIDATE; real scheduled bench, measured cost, actual pins/reach/cuts and TT/FF/DRC required')
    (out.parent/'relay_candidate.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
