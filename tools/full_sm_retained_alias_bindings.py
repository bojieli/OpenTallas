#!/usr/bin/env python3
"""Resolve mapped-source aliases against retained ODB FF/macro interface pins.
Reads committed library metadata and copied mapped Verilog, no HDL execution.
"""
import argparse,gzip,hashlib,json,re,resource,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/full_sm_actual_parent_route_20261002'
def norm(s):return s.strip().replace('\\','').replace(' ','')
def main():
 resource.setrlimit(resource.RLIMIT_AS,(16*1024**3,16*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(1200,1200))
 ap=argparse.ArgumentParser();ap.add_argument('--source-dir',type=Path,required=True);ap.add_argument('--geometry-dir',type=Path,required=True);a=ap.parse_args()
 models={}
 for label in ['DS','Qwen']:
  d=json.loads(gzip.decompress(subprocess.check_output(['git','show','d215c4bf4:results/uarch/hbm_tc_parent_capacity_20261002/'+label+'_retained.json.gz'],cwd=ROOT)))
  b=gzip.decompress((a.source_dir/(label+'_mapped.v.gz')).read_bytes());sha=hashlib.sha256(b).hexdigest();pinned=next(v for k,v in d['files'].items() if '1_2_yosys.v' in k);assert sha==pinned['sha256'];text=b.decode();del b
  widths={norm(n):(int(x),int(y)) for x,y,n in re.findall(r'^  (?:wire|input|output) \[(\d+):(\d+)\] (\S+)\s*;',text,re.M)}
  def split(s):
   result=[];start=depth=0
   for i,c in enumerate(s):
    if c=='{':depth+=1
    elif c=='}':depth-=1
    elif c==',' and depth==0:result.append(s[start:i]);start=i+1
   return result+[s[start:]]
  def bits(s):
   s=norm(s)
   if s.startswith('{'):
    inner=s[1:-1];m=re.fullmatch(r'(\d+)\{(.*)\}',inner)
    if m:return bits(m[2])*int(m[1])
    return [v for t in split(inner) for v in bits(t)]
   m=re.fullmatch(r"(\d+)'([bhd])([0-9a-fxz]+)",s,re.I)
   if m:return ['CONST']*int(m[1])
   m=re.fullmatch(r'(.*)\[(\d+):(\d+)\]',s)
   if m:return [m[1]+f'[{i}]' for i in range(int(m[2]),int(m[3])-1,-1)]
   if s in widths:
    x,y=widths[s];return [s+f'[{i}]' for i in range(x,y-1,-1)]
   return [s]
  aliases={}
  for x,y in re.findall(r'^  assign (.*?) = (.*?);$',text,re.M):
   xx,yy=bits(x),bits(y);assert len(xx)==len(yy),(x,y)
   aliases.update(zip(xx,yy))
  def resolve(s):
   s=norm(s);seen=set()
   while s in aliases and s not in seen:seen.add(s);s=aliases[s]
   return s
  # Mapped connectivity, including combinational fan-in, is essential:
  # source nets are often behind decode/mux logic ratherthan direct FF Q.
  lib=d['library_area_and_output_ports'];drivers={};cells=[];instance_ports={}
  for m in re.finditer(r'^  (\S+) (\S+)\s+\(\n(.*?)^  \);',text,re.M|re.S):
   master,name,body=m.groups();name=norm(name);ports={p:e for p,e in re.findall(r'\.(\w+)\((.*?)\)(?:,|\s*$)',body,re.M|re.S)}
   assert master in lib,master
   instance_ports[name]=ports
   outputs=lib[master]['outputs'];ins=[resolve(n) for p,e in ports.items() if p not in outputs for n in bits(e)]
   cid=len(cells);cells.append((master,name,ins))
   for p in outputs:
    if p not in ports:continue
    for n in bits(ports[p]):
     n=resolve(n)
     if n!='CONST':assert n not in drivers,n;drivers[n]=cid
  cache={};active=set()
  def frontier(n):
   if n in cache:return cache[n]
   if n=='CONST':return frozenset()
   cid=drivers.get(n)
   if cid is None:return frozenset(['INPUT:'+n])
   master,name,ins=cells[cid]
   if master.startswith('DFF'):return frozenset(['FF:'+name])
   if not master.endswith('_ASAP7_75t_R'):return frozenset(['MACRO:'+name])
   if n in active:raise ValueError('combinational cycle '+n)
   active.add(n);r=frozenset().union(*(frontier(i) for i in ins));active.remove(n);cache[n]=r;return r
  geom=json.load(gzip.open(a.geometry_dir/(label+'_geometry.json.gz'),'rt'));macro={};source_macro_pins=[];constant_pin_count=0
  for m in geom['macro_instances']:
   for p in m['pins']:
    if p['sig']=='SIGNAL' and p['net'] and norm(p['net']) not in ['rst_n','clk']:
     name=norm(m['name']);port=p['pin'];idx=re.fullmatch(r'(.*)\[(\d+)\]',port);base=idx[1] if idx else port
     assert name in instance_ports,(name,port)
     assert base in instance_ports[name],(name,port)
     expr=instance_ports[name][base];bb=bits(expr);bit=int(idx[2]) if idx else 0
     assert bit<len(bb),(name,port,expr,len(bb))
     n=resolve(bb[-1-bit]);constant_pin_count+=n=='CONST'
     source_macro_pins.append({'instance':name,'master':m['master'],'pin':port,'direction':p['io'],'access_DBU':p['avg_access_xy'],'ODB_net':norm(p['net']),'source_resolved_net':n,'source_port_expression':norm(expr)})
     if n!='CONST':macro.setdefault(n,[]).append([name,port,p['avg_access_xy']])
  pp=OUT/('source_macro_pin_binding_'+label+'.json.gz');pb=gzip.compress((json.dumps(source_macro_pins,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)
  if pp.exists():assert pp.read_bytes()==pb
  else:pp.write_bytes(pb)
  cones={};ff_reached=set();root_classes={};unresolved=set()
  for n,ps in macro.items():
   roots=frontier(n);cones[n]={'macro_ports':ps,'actual_driver_frontier':sorted(roots)}
   for root in roots:
    cls=root.split(':',1)[0];root_classes[cls]=root_classes.get(cls,0)+1
    if cls=='FF':ff_reached.add(root[3:])
    elif cls=='INPUT':unresolved.add(root[6:])
  cb=gzip.compress((json.dumps(cones,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0);cp=OUT/('actual_parent_cone_frontiers_'+label+'.json.gz')
  if cp.exists():assert cp.read_bytes()==cb
  else:cp.write_bytes(cb)
  ff={};count=0;linked=set()
  for f in geom['FF_instances']:
   ns={resolve(p['net']) for p in f['pins'] if p.get('net')};ids=sorted(ns&macro.keys());count+=bool(ids);linked.update(ids)
   ff[norm(f['name'])]={'master':f['master'],'macro_interface_net_ids':ids,'source_hierarchy':norm(f['name']).split('.u_')[0],'macro_interface_accesses':[e for n in ids for e in macro[n]]}
  assert len(ff)==d['census']['unique_FF']['count']
  summary={'mapped_source_sha256':sha,'mapped_source_raw_cells':len(cells),'macro_interface_driver_frontier_classes':root_classes,'actual_FF_driver_frontier_count':len(ff_reached),'primary_or_missing_driver_frontier_ids':sorted(unresolved),'parent_cone_frontier_ledger':'actual_parent_cone_frontiers_'+label+'.json.gz','ODB_sha256':geom['ODB_sha256'],'source_alias_scalar_assignments':len(aliases),'resolved_nonconstant_macro_interface_nets':len(macro),'constant_macro_ports_excluded_only_after_source_resolution':constant_pin_count,'source_macro_pin_binding':'source_macro_pin_binding_'+label+'.json.gz','actual_FFs':len(ff),'FFs_directly_bound_to_macro_interfaces':count,'FFs_requiring_combinational_cone_binding':len(ff)-count,'resolved_macro_interface_nets_directly_bound_to_FFs':len(linked),'scope':'One binding per actual FF,source alias resolution,unplaced ODBFFs do not acquire placement or route credit','ledger':'source_resolved_FF_macro_bindings_'+label+'.json.gz'}
  bb=gzip.compress((json.dumps(ff,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0);p=OUT/summary['ledger']
  if p.exists():assert p.read_bytes()==bb
  else:p.write_bytes(bb)
  models[label]=summary
  print(label,json.dumps({k:summary[k] for k in ['actual_FFs','actual_FF_driver_frontier_count','resolved_nonconstant_macro_interface_nets','constant_macro_ports_excluded_only_after_source_resolution']}),flush=True)
  del geom,macro,ff,aliases,text,d,cells,drivers,cache,cones
 p=OUT/'mapped_source_binding.json';b=(json.dumps(models,indent=2,sort_keys=True)+'\n').encode()
 if p.exists():assert p.read_bytes()==b
 else:p.write_bytes(b)
if __name__=='__main__':main()
