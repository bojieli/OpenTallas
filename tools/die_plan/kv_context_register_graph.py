"""Complete C4 mapped-cell site inventory and registered-boundary geometric budget; no P&R credit."""
import json,math,argparse,hashlib
from pathlib import Path
from collections import defaultdict,Counter

def hit(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
def run(mapped,lib,placement,fixed,out):
 d=json.loads(mapped.read_text())['modules']['qkd_kvs_emb_rope'];L=json.loads(lib.read_text());P=json.loads(placement.read_text());F=json.loads(fixed.read_text());cells=d['cells'];region=P['logic_region_um'];pos={r['cell']:r for r in F['rows']};fixedrects=[r['rect_um'] for r in pos.values()];std=[n for n,c in cells.items() if c['type'] in L['cells']];remaining=sorted(set(std)-set(pos));rows=math.floor((region[3]-region[1])/.27);cursor=[region[0]]*rows;used=[0.0]*rows
 # Spread cells uniformly across rows; each row reserves45% length for channels, buffering and clock.
 for n in remaining:
  w,h=L['cells'][cells[n]['type']]['size'];assert abs(h-.27)<1e-6,(n,w,h)
  done=False
  for ri in sorted(range(rows),key=lambda r:used[r]):
   if used[ri]+w>.55*(region[2]-region[0]):continue
   y=round((region[1]+ri*.27)/.27)*.27;x=math.ceil(cursor[ri]/.054)*.054
   while x+w<=region[2]:
    box=[x,y,x+w,y+h];bad=[r for r in fixedrects if hit(box,r)]
    if bad:x=math.ceil(max(r[2] for r in bad)/.054)*.054;continue
    pos[n]=dict(cell=n,master=cells[n]['type'],orientation='R0' if round(y/.27)%2==0 else 'MX',rect_um=box);cursor[ri]=x+w;used[ri]+=w;done=True;break
   if done:break
  assert done,('NO_COMMON_LOGIC_SITE',n)
 ff={n for n in std if cells[n]['type'].startswith('DFF')};drivers={};outs={}
 for n,c in cells.items():
  con=c.get('connections',{});
  if not con:continue
  outp={'rd_out'} if c['type'].startswith('ot_sram_') else {'QN'} if n in ff else {'Y'};outs[n]=outp
  for p in outp:
   for b in con[p]:
    if isinstance(b,int):drivers[b]=n
 memo={}
 def sources(bit,seen=None):
  if bit in memo:return memo[bit]
  n=drivers.get(bit)
  if n is None:return frozenset()
  if n in ff:return frozenset([n])
  if cells[n]['type'].startswith('ot_sram_'):return frozenset()
  seen=set() if seen is None else seen
  if bit in seen:return frozenset()
  seen=seen|{bit};s=set()
  for p,bs in cells[n].get('connections',{}).items():
   if p not in outs[n]:
    for b in bs:
     if isinstance(b,int):s.update(sources(b,seen))
  memo[bit]=frozenset(s);return memo[bit]
 def pin(n,p):
  row=pos[n];x,y=row['rect_um'][:2];h=row['rect_um'][3]-y;out=[]
  for a,b,c,e in L['cells'][cells[n]['type']]['pins'][p]:
   for u in [a,c]:
    for v in [b,e]:out.append((x+u,y+(v if row['orientation']=='R0' else h-v)))
  return out
 edges=[]
 for n in sorted(ff):
  inputs=cells[n]['connections']['D'];src=set()
  for b in inputs:
   if isinstance(b,int):src.update(sources(b))
  ep=pin(n,'D')
  for s in sorted(src):
   sp=pin(s,'QN');length=max(abs(x-u)+abs(y-v) for x,y in sp for u,v in ep)
   edges.append(dict(src=s,dst=n,direct_pin_envelope_um=length))
 fails=sorted((e for e in edges if e['direct_pin_envelope_um']>405),key=lambda e:-e['direct_pin_envelope_um'])
 inventory=Counter(cells[n]['type'] for n in std)
 result=dict(schema='opentallas.qwen-kv-context-register-graph.v1',state='ANALYTICAL_SITES_NO_ROUTE_OR_STA',source_mapped_sha256=hashlib.sha256(mapped.read_bytes()).hexdigest(),std_master_LEF_sha256=L['sha256'],mapped_std_cells=len(std),mapped_FF=len(ff),macro_count=2,common_logic_region_um=region,common_logic_site_util_limit=.55,constrained_macro_FF_sites=len(F['rows']),placed_std_area_um2=sum(math.prod(L['cells'][cells[n]['type']]['size']) for n in std),cell_inventory=dict(inventory),registered_data_edges=len(edges),registered_direct_max_um=max(e['direct_pin_envelope_um'] for e in edges),registered_direct_over405=len(fails),worst_edges=fails[:100],all_cell_sites=list(pos.values()),all_registered_edges=edges,
 claims=dict(route=False,STA=False,RTL_change=False,added_cycles=False,clock_PDN_qualified=False),next='Move the named over405 register pairs within legal macro-pin lenses before adding a cycle; all intermediate combinational paths and joint channels remain unqualified.')
 out.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:result[k] for k in ['state','mapped_std_cells','mapped_FF','registered_data_edges','registered_direct_max_um','registered_direct_over405','placed_std_area_um2']}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--mapped',type=Path,required=True);a.add_argument('--std-lef',type=Path,required=True);a.add_argument('--placement',type=Path,required=True);a.add_argument('--macro-ff-sites',type=Path,required=True);a.add_argument('--out',type=Path,required=True);p=a.parse_args();run(p.mapped,p.std_lef,p.placement,p.macro_ff_sites,p.out)
