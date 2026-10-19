#!/usr/bin/env python3
"""Extract the actual MUT0 CB16 data graph, with A0 pin coordinates and aliases.
No synthesis. The graph feeds fleet floorplan/schedule exploration; never a view.
"""
import json,re,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN_Y0={'n_a':61.644,'n_b':162.252,'t_out':262.764,'n_y':363.276}

def extract(root=ROOT):
 a=root/'results/arch/qwen_cluster_1017';c=json.loads((a/'cluster_contract_dv.json').read_text())
 sites={s['inst'].split('.',1)[1]:s for s in json.loads((a/'relay_sites_dv.json').read_text())['sites']}
 fab=(root/'rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv').read_text();nodes={};ports={};alias={}
 for m in re.finditer(r'(?:assign|wire) (\w+) = (\w+);',fab):alias[m[1]]=m[2]
 for m in re.finditer(r'assign (\w+) = \(MUT == \d+ \? \w+ : (\w+)\);',fab):alias[m[1]]=m[2]
 for m in re.finditer(r'wire \[\d+:0\] (\w+) = \(MUT == \d\) \? \{[^}]*\} : (\w+);',fab):alias[m[1]]=m[2]
 parsed=0
 for line in fab.splitlines():
  m=re.search(r'\b(qfd_c_stn\d+|qfd_c_xstnw?|qfd_c_land_[wr]|qfd_q3h_stn|qfd_q3h_run)(?: #\(.*\))? (\w+) \(\.ck\(ck_(\w+)\)',line)
  if not m:continue
  parsed+=1;kind,name,reg=m.groups();ps=dict(re.findall(r'\.(\w+)\(([^()]*)\)',line))
  if kind=='qfd_q3h_run':alias[ps['q']]=ps['d'];continue
  ss=sites.get(name);assert ss is not None,name
  ins=[];outs=[]
  if kind in ('qfd_c_xstn','qfd_c_xstnw'):ins=[ps['b_d']];outs=[ps['a_d'],ps['tap_d']]
  elif kind=='qfd_c_land_w':ins=[ps['i']];outs=[ps['bank']]
  elif kind=='qfd_c_land_r':ins=[ps['bank']];outs=[ps['o']]
  else:ins=[ps['d']];outs=[ps['q']]
  nodes[name]=dict(kind=kind,region=reg,at=ss['at'],bits=ss['bits'],inputs=ins,outputs=outs,ports=ps)
 assert parsed==len(re.findall(r'\.ck\(ck_',fab)),(parsed,'clock parse mismatch')
 def res(n):
  seen=set()
  while n in alias:
   assert n not in seen,('alias cycle',n);seen.add(n);n=alias[n]
  return n
 tilexy={t['inst']:t for t in c['tiles']}
 for tname,t in tilexy.items():
  col,row=[int(v)for v in tname[4:].split('_')];x,y=t['at'];face=x+457.92 if t['orient']=='MY'else x
  for name in ['t_out','n_y','n_a','n_b','tap']:
   if [col,row]==c['tree']['nl_slot'] and name in ['n_a','n_b','n_y']:continue
   net=f'{name}_{col}_{row}';pt=[face,y+PIN_Y0[name]+.192*256.5]if name!='tap'else [x if t['orient']=='MY'else x+457.92,y+(437.196+485.868)/2]
   ports[net]=dict(kind='tile_port',tile=tname,region=f'c{col}r{row}',at=pt,bits=508 if name=='tap'else 514,role='source'if name in ['t_out','n_y']else'sink')
 for p in c['ports']:
  n=p['port']
  if n.startswith(('bc','rs')):
   mid=sum(p['range_um'])/2;face=p['face'];pt=[mid,0 if face=='S'else c['outline_um']['h']]if face in ['S','N']else [0 if face=='W'else c['outline_um']['w'],mid]
   ports[n]=dict(kind='boundary_port',at=pt,bits=p['bits'],role='sink'if n.startswith('bco')or n in ['rs','rs_o']else'source')
 prod={}
 for n,v in nodes.items():
  if v['bits']>1:
   for q in v['outputs']:prod[q]=n
 for n,p in ports.items():
  if p['role']=='source':prod[n]=n
 edges=[];unresolved=[]
 def edge(net,dst,bits=None):
  net=res(net)
  if net not in prod:unresolved.append(dict(net=net,dst=dst));return
  src=prod[net];kind='bank'if nodes.get(src,{}).get('kind')=='qfd_c_land_w'else'data'
  sn=nodes.get(src,ports.get(src));dn=nodes.get(dst,ports.get(dst));assert sn and dn,(src,dst)
  edges.append(dict(net=net,src=src,dst=dst,kind=kind,bits=bits or min(sn['bits'],dn['bits']),src_at=sn['at'],dst_at=dn['at'],src_region=sn.get('region'),dst_region=dn.get('region'),base_capture_edges=2 if kind=='bank'else 1))
 for n,v in nodes.items():
  if v['bits']>1:
   for d in v['inputs']:edge(d,n)
 for n,p in ports.items():
  if p['role']=='sink':edge(n,n,p['bits'])
 reset={n:v for n,v in nodes.items()if v['bits']==1}
 return dict(schema='opentallas.cb16.data_graph.v1',source='ac8e4c483',parsed_clocked_instances=parsed,nodes=nodes,ports=ports,aliases=alias,edges=edges,unresolved=unresolved,reset_nodes=reset,contract=c)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();g=extract();out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(g,indent=1)+'\n');print('SAFE_GRAPH nodes',len(g['nodes']),'edges',len(g['edges']),'bank',sum(e['kind']=='bank'for e in g['edges']),'unresolved',g['unresolved'])
 if g['unresolved']:raise SystemExit(1)
if __name__=='__main__':main()
