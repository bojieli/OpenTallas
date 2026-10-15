#!/usr/bin/env python3
"""Crossjoin geometry pin-pair promises to the actual bit-mapped RTL graph."""
import argparse,json,gzip,re,functools,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('netlist');p.add_argument('pairs');p.add_argument('out');a=p.parse_args()
m=json.load(open(a.netlist))['modules']['qfd_tile_nk_banked_v1'];cells=m['cells']
def name(n):return n.replace('u_tile.u_tile.u_logic.','u_logic.')
def pin(ep):
 n,port=ep;n=name(n);mt=re.fullmatch(r'(.*)\[(\d+)\]',port)
 port,i=(mt[1],int(mt[2]))if mt else(port,0)
 return cells[n]['connections'][port][i]
deps={}
for n,c in cells.items():
 if 'DFF' in c['type'] or c['type'].startswith(('qkh_','qwen_glue_','ot_qwen_tile_')):continue
 inputs=[b for pn,bs in c['connections'].items()if c['port_directions'][pn]=='input'for b in bs if isinstance(b,int)]
 for pn,bs in c['connections'].items():
  if c['port_directions'][pn]=='output':
   for b in bs:
    if isinstance(b,int):deps[b]=inputs
@functools.lru_cache(None)
def ancestors(b):
 if b not in deps:return frozenset([b])
 return frozenset().union(*(ancestors(x)for x in deps[b]))
pairs=json.load(gzip.open(a.pairs,'rt'));counts=collections.Counter();missing=[];same=0;comb=0
for z in pairs:
 try:
  s,t=pin(z['source']),pin(z['sink']);ok=isinstance(s,int)and(s==t or s in ancestors(t))
 except (KeyError,IndexError)as e:ok=False;missing.append({'pair':z,'error':str(e)});continue
 if not ok:missing.append({'pair':z,'source_bit':s,'sink_bit':t})
 else:
  counts[z['group']]+=1
  if s==t:same+=1
  else:comb+=1
out={'schema':'qwen.compute.actual_parent_dependency_audit.v1','status':'PASS'if not missing else'FAIL','pairs':len(pairs),'direct_net_pairs':same,'combinational_dependency_pairs':comb,'matched_by_group':dict(counts),'unmatched_count':len(missing),'unmatched':missing[:100],'claim_boundary':'Actual source dependency coverage only; no comb delay, clock insertion, route or native physical qualification.'}
Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in ['unmatched','matched_by_group']}));raise SystemExit(bool(missing))
