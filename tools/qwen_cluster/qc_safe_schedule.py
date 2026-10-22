#!/usr/bin/env python3
"""Compose actual fabric graph and price candidate edge relays/pad alignment.
No dynamic stalls/credits. Baseline must reproduce source-pinned compiler cycles.
Geometry is unqualified unless separately routed/clocked and all added hardware fits.
"""
import argparse,json,collections,math
from pathlib import Path
from qc_safe_graph import ROOT,extract

def compose(g,extra=None,align=False):
 extra=dict(extra or {});pad=collections.defaultdict(int);nodes=g['nodes'];ports=g['ports'];edges=g['edges'];incoming=collections.defaultdict(list)
 for e in edges:incoming[e['dst']].append(e)
 def propagate():
  t={n:0 for n,p in ports.items()if p['kind']=='boundary_port'and p['role']=='source'}
  for _ in range(len(nodes)+len(ports)):
   before=len(t)
   for n,v in nodes.items():
    if v['bits']<=1 or n in t:continue
    ins=incoming[n]
    if ins and all(e['src']in t for e in ins):
     add=2 if v['kind']=='qfd_c_land_r'else 1
     t[n]=max(t[e['src']]+extra.get((e['src'],n),0)+pad[e['src'],n]+add for e in ins)
   for n,p in ports.items():
    if n in t:continue
    if p['role']=='sink':
     ins=incoming[n]
     if ins and all(e['src']in t for e in ins):t[n]=max(t[e['src']]+extra.get((e['src'],n),0)+pad[e['src'],n]for e in ins)
    elif p['kind']=='tile_port':
     col,row=p['tile'][4:].split('_')
     if n.startswith('t_out')and f'tap_{col}_{row}'in t:t[n]=t[f'tap_{col}_{row}']
     elif n.startswith('n_y')and all(f'n_{ab}_{col}_{row}'in t for ab in 'ab'):t[n]=max(t[f'n_a_{col}_{row}'],t[f'n_b_{col}_{row}'])+1
   if len(t)==before:break
  return t
 t=propagate()
 if align:
  # Preserve one static row calendar across all4 columns; add fixed pad stages
  # at the next column station. Recompute downstream times after every row.
  for row in range(4):
   common=max(t[f'tap_{col}_{row}']for col in range(4))
   for col in range(4):
    n=f'u_x_{col}_{row}';e=incoming[n][0];pad[e['src'],n]+=common-t[f'tap_{col}_{row}']
   t=propagate()
  # Reduction nodes in golden tree order. Parent has one node adder per host.
  for lv in range(1,5):
   for ni in range(2**(4-lv)):
    col,row=g['contract']['tree']['hosts'][f'{lv}_{ni}'];aa=f'n_a_{col}_{row}';bb=f'n_b_{col}_{row}';common=max(t[aa],t[bb])
    for n in [aa,bb]:
     e=incoming[n][0];pad[e['src'],n]+=common-t[n]
    t=propagate()
  # Equal output calendar for the4 column stream exits.
  common=max(t[f'bco{col}']for col in range(4))
  for col in range(4):
   n=f'bco{col}';e=incoming[n][0];pad[e['src'],n]+=common-t[n]
  t=propagate()
 return dict(timing=t,extra_relays=[dict(src=k[0],dst=k[1],edges=v)for k,v in extra.items()if v],alignment_pads=[dict(src=k[0],dst=k[1],edges=v,implementation='ring/SRAM required'if v>=3 else'hardened register(s)')for k,v in pad.items()if v])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--placement');ap.add_argument('--out',required=True);a=ap.parse_args();g=extract();base=compose(g);C=g['contract']['latency_edges'];expected=dict(tap={str(r):C['tap'][str(r)]for r in range(4)},bco=C['bco'],rs_fabric=C['rs_fabric'],rs_i_to_rs_o=C['rs_i_to_rs_o'])
 observed=dict(tap={str(r):base['timing'][f'tap_0_{r}']for r in range(4)},bco=base['timing']['bco0'],rs_fabric=base['timing']['rs'],rs_i_to_rs_o=base['timing']['rs_o']);print('SCHEDULE_BASELINE',expected,observed,flush=True);assert expected==observed,(expected,observed)
 result=dict(schema='opentallas.cb16.schedule_price.v1',source=g['source'],baseline_pass=True,baseline=observed,release_ready=False)
 if a.placement:
  p=json.loads(Path(a.placement).read_text());extra={}
  for e in p['edges']:
   if not e.get('reach405_pass',True):
    src=e['src'].rsplit('_p',1)[0]if e['src'].endswith(('_p0','_p1'))else e['src'];dst=e['dst'].rsplit('_p',1)[0]if e['dst'].endswith(('_p0','_p1'))else e['dst']
    # Ordinary full-cycle relays are a conservative price, not an implementation.
    # Bank forwarding must have separate proven phase/slot age accounting.
    extra[src,dst]=max(extra.get((src,dst),0),e['relay_edges_needed'])
  price=compose(g,extra,align=True);t=price['timing'];new=dict(tap={str(r):max(t[f'tap_{col}_{r}']for col in range(4))for r in range(4)},bco=max(t[f'bco{col}']for col in range(4)),rs_fabric=t['rs'],rs_i_to_rs_o=t['rs_o'])
  result.update(candidate=new,extra_relays=price['extra_relays'],alignment_pads=price['alignment_pads'],candidate_complete_geometry=p.get('unplaced')==[],placement_area_mm2=p['area_mm2'],note='Conservative ordinary-relay price only; bank edges cannot be adopted this way without age/overwrite proof and extra relay geometry. Incomplete geometry does not qualify an architecture.')
  print('SCHEDULE_CANDIDATE',new,'relays',sum(r['edges']for r in price['extra_relays']),'pads',sum(r['edges']for r in price['alignment_pads']),flush=True)
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=1)+'\n')
if __name__=='__main__':main()
