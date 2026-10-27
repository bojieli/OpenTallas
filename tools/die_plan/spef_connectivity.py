#!/usr/bin/env python3
"""Audit extracted resistor connectivity; a positive total R/C and a CONN record
for each pin do not establish a connected network. Flags each input pin without a
resistor path to its output driver. Streaming parser handles large die SPEFs.
"""
import argparse,json,re
from collections import defaultdict
from pathlib import Path

def audit(path):
    names={};mode=None;net=None;rows=[];conns=[];edges=[]
    def name(k):
        return re.sub(r'\*(\d+)',lambda m:names.get(m.group(1),m.group(0)),k)
    def finish():
        if net is None:return
        g=defaultdict(list)
        for a,b in edges:g[a].append(b);g[b].append(a)
        drivers=[n for kind,n,d in conns if (kind,d) in (('*I','O'),('*P','I'))];sinks=[n for kind,n,d in conns if (kind,d) in (('*I','I'),('*P','O'))]
        seen=set(drivers);todo=list(drivers)
        while todo:
            for b in g[todo.pop()]:
                if b not in seen:seen.add(b);todo.append(b)
        bad=[name(n) for n in sinks if n not in seen]
        rows.append(dict(net=name(net),drivers=len(drivers),sinks=len(sinks),resistors=len(edges),unreachable=bad))
    with open(path) as stream:
        for line in stream:
            f=line.split()
            if not f:continue
            if f[0]=='*NAME_MAP':mode='map';continue
            if f[0]=='*D_NET':
                finish();net=f[1];conns=[];edges=[];mode=None;continue
            if mode=='map' and f[0].startswith('*') and f[0][1:].isdigit() and len(f)>1:names[f[0][1:]]=f[1];continue
            if f[0] in ('*CONN','*CAP','*RES'):mode=f[0];continue
            if f[0]=='*END':finish();net=None;mode=None;continue
            if mode=='*CONN' and f[0] in ('*I','*P') and len(f)>=3:conns.append((f[0],f[1],f[2]))
            if mode=='*RES' and len(f)>=4:edges.append((f[1],f[2]))
    finish()
    bad=[r for r in rows if r['drivers'] and r['unreachable']]
    return dict(nets=len(rows),nets_with_drivers=sum(bool(r['drivers']) for r in rows),nets_disconnected=len(bad),unreachable_pins=sum(len(r['unreachable']) for r in bad),failures=bad)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('spef');p.add_argument('out');a=p.parse_args();r=audit(a.spef);Path(a.out).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='failures'}))
