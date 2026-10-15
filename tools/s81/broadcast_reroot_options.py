#!/usr/bin/env python3
"""Reroot actual exported broadcast tree at existing corridor nodes.
Metrics use actual tree topology with ideal roadmap Manhattan weights, not
native routed pins. Reversing edge flow needs generator/physical clock proof.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
from collections import defaultdict,deque

def key(p):return tuple(round(v,5) for v in p)
def l1(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def poly(p):return sum(l1(a,b) for a,b in zip(p,p[1:]))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();p=json.loads(gzip.decompress(a.plan.read_bytes()));t=p['broadcast_trees']['E'];g=defaultdict(list)
 for e in t['edges']:
  n,par=key(e['node']),key(e['parent']);d=l1(n,par);g[n].append((par,d));g[par].append((n,d))
 source=t['prefix'][0];cross=t['prefix'][-2];old=key(t['entry']);candidates=[old]+sorted([n for n in g if abs(n[0]-cross[0])<.001 and abs(n[1]-cross[1])<4500]);targets={int(r):key(v) for r,v in t['root_targets'].items()};out=[]
 for entry in candidates:
  dist={entry:0};q=deque([entry])
  while q:
   n=q.popleft()
   for nxt,d in g[n]:
    if nxt not in dist:dist[nxt]=dist[n]+d;q.append(nxt)
  assert all(v in dist for v in targets.values())
  pref=t['prefix'][:-1]+[list(entry)];pd=poly(pref);rootpaths={r:pd+dist[v] for r,v in targets.items()};worst=max(rootpaths,key=rootpaths.get)
  out.append(dict(entry_um=entry,prefix_path_um=pref,prefix_um=pd,worst_root=worst,worst_prefix_plus_tree_um=rootpaths[worst],root2_prefix_plus_tree_um=rootpaths[2],sum_root_prefix_plus_tree_um=sum(rootpaths.values()),shared_prefix_bit_um=pd*566,roots=len(targets)))
 r=dict(scope='ACTUAL_TREE_REROOT_TOPOLOGY_SCREEN_NOT_NATIVE',source_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),half='E',baseline=out[0],candidates=sorted(out[1:],key=lambda x:x['worst_prefix_plus_tree_um']),objective='First reduce worst registered flight path; unique shared tree wire unchanged under edge reversal, actual prefix wire changes',unproven=['New prefix segment from actual HC passage to existing corridor node must pass occupied station allocation','Reverse-flow station masters/orientations/pins/clock delivery need regeneration','Final root tap/CFIFO exact pins and all fixed stage calendars must be repriced','Activity and all upstream/downstream transfer paths missing; no final system selection'])
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(dict(baseline=r['baseline'],best=r['candidates'][0]),indent=1))
if __name__=='__main__':main()
