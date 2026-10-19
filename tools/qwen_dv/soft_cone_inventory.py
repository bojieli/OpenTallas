#!/usr/bin/env python3
"""Generic flattened-netlist fanout/depth inventory; no mapped timing claim."""
import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path


def inventory(design, top):
    m=design['modules'][top]
    aliases=defaultdict(list);loads=Counter();drivers={};regbits=set()
    depth={};comb=[];endpoints=[];issues=[]
    for name,net in m['netnames'].items():
        for i,b in enumerate(net['bits']):
            if isinstance(b,int):aliases[b].append(name+(f'[{i}]' if len(net['bits'])>1 else ''))
    def brief(b):
        return sorted(aliases[b],key=lambda s:(s.startswith('$'),len(s),s))[:5]
    for p in m['ports'].values():
        if p['direction']=='input':
            for b in p['bits']:depth[b]=0
    for name,c in m['cells'].items():
        con=c['connections'];dirs=c.get('port_directions',{})
        if set(con)!=set(dirs):raise ValueError('missing port directions: '+name)
        ins=[b for p,bs in con.items() if dirs[p]=='input' for b in bs]
        outs=[b for p,bs in con.items() if dirs[p]=='output' for b in bs]
        loads.update(b for b in ins if isinstance(b,int))
        for b in outs:
            if not isinstance(b,int):continue
            if b in drivers and drivers[b]['cell']!=name:issues.append('multiple drivers '+str(brief(b)))
            drivers[b]=dict(cell=name,type=c['type'])
        sequential=c['type'].startswith(('$_DFF','$_SDFF'))
        module=design['modules'].get(c['type'],{})
        blackbox=int(module.get('attributes',{}).get('blackbox','0'),2)
        if sequential or blackbox:
            for b in outs:
                depth[b]=0
                if sequential:regbits.add(b)
            for p,bs in con.items():
                if dirs[p]=='input' and p not in ('C','clk','ck','CLK'):
                    endpoints.extend((name,p,b) for b in bs)
        else:comb.append((name,ins,outs))
    readers=defaultdict(list);remaining=[]
    for i,(_,ins,_) in enumerate(comb):
        need={b for b in ins if isinstance(b,int) and b not in depth};remaining.append(need)
        for b in need:readers[b].append(i)
    q=deque(i for i,need in enumerate(remaining) if not need);seen=set()
    while q:
        i=q.popleft()
        if i in seen:continue
        seen.add(i);_,ins,outs=comb[i]
        level=1+max((depth.get(b,0) for b in ins),default=0)
        for b in outs:
            if not isinstance(b,int):continue
            depth[b]=level
            for j in readers[b]:
                remaining[j].discard(b)
                if not remaining[j]:q.append(j)
    if len(seen)!=len(comb):issues.append(f'{len(comb)-len(seen)} unresolved combinational cells (cycle/unknown input/hierarchy)')
    rows=[dict(bit=b,loads=n,names=brief(b),driver=drivers.get(b),register_output=b in regbits)
          for b,n in loads.most_common() if n>32]
    stages=sorted([dict(cell=n,pin=p,bit=b,generic_levels=depth.get(b),names=brief(b))
                   for n,p,b in endpoints if isinstance(b,int)],
                  key=lambda r:-(r['generic_levels'] if r['generic_levels'] is not None else -1))
    return dict(status='GENERIC_DIAGNOSTIC_NOT_MAPPED_TIMING_OR_FANOUT_QUALIFICATION',
        top=top,cells=len(m['cells']),issues=issues,
        register_outputs_over32=[r for r in rows if r['register_output']],
        driven_nets_over32_count=sum(bool(r['driver']) for r in rows),
        highest_fanout_nets=rows[:40],highest_generic_stage_depth=stages[:30],
        scope='Generic synthesis before ABC/physical buffers. Primitive levels are not TT ps; native macro clk-to-Q/setup, mapped logic, placement/route and retained replicas require separate proof. Clock/reset boundary loads retained and labeled, not counted as data-fanout failures.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('netlist');ap.add_argument('--top',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    raw=Path(a.netlist).read_bytes();d=inventory(json.loads(raw),a.top)
    d['netlist_sha256']=hashlib.sha256(raw).hexdigest()
    Path(a.out).write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps({k:d[k] for k in ('top','cells','issues','register_outputs_over32','driven_nets_over32_count','highest_generic_stage_depth')},indent=2)[:4000])


if __name__=='__main__':main()
