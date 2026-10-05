"""Emit actual64 collector+one retained RF route from frozen real interfaces.

Parent joins physical profile/controller/RF/quiescence ports. No input defaults,
source key fromcmd, grant, fakeQclean or extra clock. No compile in generator.
"""
import re,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
COLLECTOR='rtl/experimental/canonical_qwen_native_apertures_20261003/ot_gpu_qwen_native_aperture_collector.sv'
ROUTE='rtl/model/qwen_native_rf_route_20261003/ot_gpu_qwen_native_rf_route_r2.sv'
SHARED={'clk','query_valid','query_retained','query_write','query_workspace','bank_fault','query_tuple','query_slot','query_owner','query_version','query_first','query_end','bank_scope_valid','bank_scope_writable','bank_scope_workspace','bank_scope_tuple','bank_scope_owner','ack_accept','ack_slot','ack_owner'}
WIRED={'controller_idle','selected_routes_drained','read_operand','read_page','write_page'}
def ports(path):
 header=re.sub(r'//[^\n]*','',path.read_text()).split(');',1)[0]+');';out={}
 for m in re.finditer(r'\b(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*([\w,\s]+?)(?=,\s*(?:input|output)\b|\s*\);)',header):
  w=1
  if m[2]:
   hi,lo=m[2][1:-1].split(':')
   if re.search(r'[^0-9*+\- ]',hi+lo):raise ValueError('unsupported actual port extent')
   w=eval(hi,{'__builtins__':{}})-eval(lo,{'__builtins__':{}})+1
  for n in m[3].split(','):out[n.strip()]=dict(direction=m[1],bits=w)
 return out

def generate(out):
 out=Path(out).resolve()
 if out.exists():raise ValueError('fresh output required')
 spec=ports(ROOT/COLLECTOR);route=ports(ROOT/ROUTE);decl=[];book={};connections=[]
 for n,p in spec.items():
  if n in WIRED:continue
  w=p['bits'];total=w if n in SHARED else 64*w
  decl.append(f" {p['direction']} wire [{total-1}:0] {n}")
  book[n]=dict(p,bits=total,leaf_bits=w,count=1 if n in SHARED else 64,block='native_aperture',leaf=n)
  target=n if n in SHARED else (n+'[i]' if w==1 else n+f'[i*{w}+:{w}]')
  connections.append('.'+n+'('+target+')')
 # Exact route ABI; inputs from actual Pauli counters and RF pin book.
 colmap={'authority_valid':'authority_valid','authority_tuple':'authority_tuple','authority_owner':'authority_owner','read_route_valid':'read_route_valid','write_route_valid':'write_route_valid','read_bank':'read_bank','write_bank':'write_bank','read_slot':'read_slot','write_slot':'write_slot','read_owner':'read_owner','write_owner':'write_owner','clk':'clk','por_n':'por_n','warm_reset':'warm_reset'}
 links=[]
 for n,p in route.items():
  if n in colmap:links.append('.'+n+'('+colmap[n]+')');continue
  target='rfroute_'+n;links.append('.'+n+'('+target+')')
  decl.append(f" {p['direction']} wire [{p['bits']-1}:0] {target}")
  book[target]=dict(p,leaf_bits=p['bits'],count=1,block='native_rf_route',leaf=n)
 decl.append(' input wire [63:0] query_empty');book['query_empty']=dict(direction='input',bits=64,leaf_bits=1,count=64,block='source_bank_physical_observation',leaf='query_empty',host_writable=False)
 for n,w in [('read_operand',128),('read_page',64),('write_page',64),('private_RF_quiescent',64)]:
  decl.append(f' input wire [{w-1}:0] controller_{n}')
  book['controller_'+n]=dict(direction='input',bits=w,leaf_bits=w//64,count=64,block='native_controller_observation',leaf=n,host_writable=False)
 connections+=['.read_operand(controller_read_operand[i*2+:2])','.read_page(controller_read_page[i])','.write_page(controller_write_page[i])',
 '.controller_idle(!rfroute_actor_busy[i] && !rfroute_actor_fault[i] && controller_private_RF_quiescent[i])',
 '.selected_routes_drained(rfroute_actor_routes_drained[i] && (&query_empty))']
 text='`timescale 1ps/1ps\n// Source-only installed hierarchy: physical producer ports must be joined.\nmodule ot_gpu_qwen_native_aperture_cluster #(parameter bit ENABLE=0)(\n'+',\n'.join(decl)+'\n);\n'
 text+='wire [63:0] actor_Q_pending[0:63];\nfor(genvar i=0;i<64;i=i+1)begin:actual_collectors\n'
 text+=' for(genvar b=0;b<64;b=b+1)begin:actual_Q_debt\n  assign actor_Q_pending[i][b]=query_valid[b] && query_tuple[b*239+:239]==issuer_held_tuple[i*239+:239];\n end\n'
 text+='ot_gpu_qwen_native_aperture_collector #(.ENABLE(ENABLE),.ACTOR_INDEX(i)) u_collector(\n '+',\n '.join(connections)+'\n);\nend\n'
 text+='ot_gpu_qwen_native_rf_route_r2 #(.ENABLE(ENABLE)) u_actual_RF_route(\n '+',\n '.join(links)+'\n);\nendmodule\n'
 out.mkdir(parents=True);f=out/'ot_gpu_qwen_native_aperture_cluster.sv';f.write_text(text)
 artifact=str(f.relative_to(ROOT))
 pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [COLLECTOR,ROUTE,artifact]}
 (out/'ports.json').write_text(json.dumps(dict(top='ot_gpu_qwen_native_aperture_cluster',default_enabled=False,inventory={'actual_collectors':64,'actual_RF_routes':1,'private_RF_banks':64},pins=book,source_sha256=pins,full_build_ready=False,physical_bindings_required=['independent Pauli profile outputs from heldsource keys','actual Pauli busy/fault/protectedoperand/page/RF requests','existing guardedRF/W4 real ready/response/ACK ports','native bank_port_owned and private_RF_quiescent from TC/privateRF reservation, never tied1','existing issuer hold/frame and actual sourcebank Q/B views/ACKs','actual visibility and matched terminal/reverse; not ACKcount callbacks'],scope='actual installed collector/router hierarchy, enclosing source assembly pending physical profile/controller bindings; no fake input defaults or host grants'),indent=2)+'\n')
 return out
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();print(generate(a.out))
