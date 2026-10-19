#!/usr/bin/env python3
import re,json,hashlib,argparse
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument("die");ap.add_argument("out");a=ap.parse_args()
p=Path(a.die);txt=p.read_text();inst={}
for ln,line in enumerate(txt.splitlines(),1):
 m=re.match(r"  (\w+) (\w+) \((.*)\);",line)
 if m:
  master,name,body=m.groups();ports=dict(re.findall(r"\.(\w+)\(([^()]*)\)",body));inst[name]={"master":master,"ports":ports,"line":ln}
producers={}
for name,i in inst.items():
 if i["master"].startswith(("qkd_rlys_","qkd_rly_")) and "b" in i["ports"]: producers[i["ports"]["b"]]=(name,"relay")
 if i["master"] in ["qkd_kvs_pc","qkd_kvs_pc_h"]:producers[i["ports"]["pc__fo"]]=(name,"pc_controller_export")
constants={re.sub(r"\[0\]$","",m.group(1)):m.group(2) for m in re.finditer(r"assign (\w+(?:\[0\])?) = (1\'b[01]);",txt)}
chains=[]
for stack in ["WS","WN","ES","EN"]:
 kc=inst["kc_"+stack];net=kc["ports"]["fi"];edges=[];seen=set()
 while net!="1'b0":
  if net in constants:
   net=constants[net]; continue
  assert net not in seen,net
  seen.add(net);name,kind=producers[net];i=inst[name];pp=i["ports"]
  edges.append({"instance":name,"master":i["master"],"kind":kind,"line":i["line"],"output":net,"input":pp["a"] if kind=="relay" else pp["pc__fi"],"clock":pp["ck"] if kind=="relay" else pp["hck"],"reset":None if kind=="relay" else pp["hrst_n"],"primitive":False,"stage_semantics":"unconditional no-reset forwarding FF" if kind=="relay" else "HBM sticky OR aggregate of incoming fi and controller local detector exports; fo self-holds until hr_q reset"})
  net=edges[-1]["input"]
 assert sum(x["kind"]=="pc_controller_export" for x in edges)==32
 chains.append({"kc_instance":"kc_"+stack,"kc_ports":kc["ports"],"kf_output_bound":"kf" in kc["ports"],"reverse_from_kc_fi":edges,"terminal":net,"pc_count":32,"relay_count":sum(x["kind"]=="relay" for x in edges),"crossing":"HBM to core via f1/f2 then kf; physical phase/reset capture bound unqualified"})
x={"die":str(p),"die_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"chains":chains,"primitive_templates":[{"id":"kc_{stack}.f_ovf","clock":"ck","reset":"rs_q; sampled rsi","storage":"sticky until asynchronous rs_q low","predicate":"kv_q && !w_rdy","context":"command FIFO write rejection; kv_q is registered kc[0]"}],"aliases":[{"id":"kc_{stack}.f1/f2/kf","equation":"f1<=fi; f2<=f1; kf<=f2|f_ovf","clear":"rs_q asynchronously low","primitive":False}],"new_primitive_count":4,"qualified_tail":None,"retention_constraints":["Selected controller fo self-holds fault history until hr_q reset; capture before source regional reset can erase it. KC fi/f1/f2/kf are forwarding, not independent detector primitives.","KC f_ovf requires source-local sticky capture immune to source reset; kf is unbound in all four actual selected top instances.","No-reset relay startup is unknown until actual clocks have propagated valid source state; never convert historical HOLD128 comment to native readiness proof.","Raw POR/PLL retention implementation and capture under stopped clock remain unimplemented; no quiet window assumed."]}
Path(a.out).write_text(json.dumps(x,indent=2)+"\n")
