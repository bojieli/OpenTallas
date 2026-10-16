#!/usr/bin/env python3
"""Actual source graph: every retained primitive and physical-boundary bit/clock."""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('netlist',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--top',default='qfd_sp_vector_memory_par_partitioned_ro6');a=p.parse_args();raw=a.netlist.read_bytes();mods=json.loads(raw)['modules'];top=a.top;net_ids={};net_labels=[];nodes=[];memories=[];candidates=[];counts=collections.Counter()
def basename(n):return n.split('\\')[1]if n.startswith('$paramod\\')else n.split('\\')[-1]
def intern(label):
 if label not in net_ids:net_ids[label]=len(net_labels);net_labels.append(label)
 return net_ids[label]
def bit(b,mp,path):
 if not isinstance(b,int):return intern(f'constant:{b}')
 return mp[b]if b in mp else intern(f'{path}::bit{b}')
def walk(name,mp,path):
 m=mods[name]
 for n,v in m.get('memories',{}).items():memories.append(dict(instance=path+'.'+n,description=v))
 for n,c in m.get('cells',{}).items():
  t=c['type'];cp=path+'.'+n;cc={k:[bit(b,mp,path)for b in v]for k,v in c['connections'].items()}
  physical=t in mods and bool(mods[t].get('attributes',{}).get('blackbox'))
  if t in mods and not physical:
   if basename(t)in ['qvm_return_plane_pin_native','ot_qfd_vm_su_return_plane','ot_qfd_vm_su_read_control','ot_qfd_vm_write_control_t'] and not path.endswith('.u_core') and not (basename(t)=='ot_qfd_vm_su_return_plane' and '.g_pin_input.' in path):
    candidates.append(dict(instance=cp,master=t,ports=cc,directions=c.get('port_directions',{}),status='SOURCE_ONLY_NO_PHYSICAL_VIEW'))
   cm={b:label for pn,pv in mods[t]['ports'].items()for b,label in zip(pv['bits'],cc.get(pn,[]))};walk(t,cm,cp)
  else:
   directions=c.get('port_directions',{})or({n:v['direction']for n,v in mods[t]['ports'].items()}if t in mods else {})
   nodes.append(dict(instance=cp,kind='physical_boundary'if physical else 'source_primitive',master=t,ports=cc,directions=directions,source=c.get('attributes',{}).get('src'),parameters=c.get('parameters',{})));counts['physical_boundaries'if physical else 'source_primitives']+=1
root_map={b:intern(f'{top}::bit{b}')for v in mods[top]['ports'].values()for b in v['bits']if isinstance(b,int)};root_ports={n:dict(direction=v['direction'],bits=[bit(b,root_map,top)for b in v['bits']])for n,v in mods[top]['ports'].items()};walk(top,root_map,top)
report=dict(schema='opentallas.qwen.vm-source-graph.v1',top=top,netlist_sha256=hashlib.sha256(raw).hexdigest(),scope='Exact elaborated source primitive + hard-boundary logical net identities. Includes every remaining soft FF and combinational operator, memory objects and all actual hard pin/clock ports. No missing operations inferred away; no placement, physical path, programme coverage or qualified native token claim.',root_ports=root_ports,net_labels=net_labels,nodes=nodes,unhardened_source_memories=memories,unhardened_memory_bits=sum(m['description']['width']*m['description']['size']for m in memories),unhardened_leaf_boundaries=candidates,counts=dict(counts))
a.out.write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0));print(json.dumps(dict(counts,canonical_nets=len(net_labels),unhardened_memory_objects=len(memories),graph_bytes=a.out.stat().st_size)))
