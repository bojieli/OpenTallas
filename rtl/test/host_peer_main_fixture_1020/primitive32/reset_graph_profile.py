import importlib.util,sys,json,re,collections,hashlib
from pathlib import Path
sp=importlib.util.spec_from_file_location("tl","textbook_lint.py");m=importlib.util.module_from_spec(sp);sys.modules["tl"]=m;sp.loader.exec_module(m)
r=json.loads(Path("qkd_hr_core_peer_n32.json").read_text())
og,_=m.flatten(m.parse_verilog(Path("original.v").read_text()),None)
g,_=m.flatten(m.parse_verilog(Path("resynth.v").read_text()),r["top"]);a=m.build(g,None)
def origin(ci):
 hit=re.fullmatch(r"u(\d+)_c(\d+)\.u_cell",g.cells[ci][1])
 assert hit,g.cells[ci][1]
 oi,k=map(int,hit.groups());return oi,k,og.cells[oi][1]
def resolve(net):
 phase=False;seen=set()
 while net in a["driver"]:
  ci,pn=a["driver"][net]
  if ci<0 or a["kind"][ci]!="buf":break
  assert net not in seen;seen.add(net)
  typ,_,pins=g.cells[ci];ins=[b for p,bs in pins.items()if a["pin_dir"][ci][p]=="in" for b in bs];assert len(ins)==1
  phase^=bool(re.match("INV",typ,re.I));net=ins[0]
 return net,phase
def pin(net):
 root,phase=resolve(net);d=a["driver"].get(root);z=dict(root_net=g.net_name[root],root_bit=root,inverted=phase)
 if root<=3:z["constant"]=["0","1","x","z"][root]
 elif d is None:z["undriven"]=True
 elif d[0]<0:z["top_input"]=d[1]
 else:
  ci,pn=d;oi,k,name=origin(ci);z.update(driver=g.cells[ci][1],driver_type=g.cells[ci][0],driver_pin=pn,original=name,copy=k)
 return z
loads=collections.defaultdict(list)
for ci,(typ,name,pins)in enumerate(g.cells):
 if a["kind"][ci]=="buf":continue
 for pn,bs in pins.items():
  if a["pin_dir"][ci][pn]!="in" or pn in ("CLK","clk"):continue
  for bit in bs:
   root,phase=resolve(bit);oi,k,on=origin(ci)
   loads[root].append(dict(instance=name,type=typ,pin=pn,inverted=phase,original=on,copy=k))
rows=[]
for ci,(typ,name,pins)in enumerate(g.cells):
 if a["kind"][ci]!="ff":continue
 oi,k,on=origin(ci)
 if not any(t in on for t in ("__ot_rl","u_rst_relay_","ot_rrs__")):continue
 stage="unclassified"
 if "__ot_rl0" in on:stage="outer_S1"
 elif "__ot_rl" in on:stage="outer_S2"
 elif "sync_q[0]" in on:stage="regional_S1"
 elif "sync_q[1]" in on:stage="regional_S2"
 elif "ot_rrs__" in on or "relay_q" in on:stage="regional_final"
 out={p:[pin(b)for b in bs]for p,bs in pins.items() if a["pin_dir"][ci][p]=="out"}
 users=[]
 for p,bs in pins.items():
  if a["pin_dir"][ci][p]=="out":
   for b in bs:users+=loads[b]
 rows.append(dict(instance=name,type=typ,original=on,copy=k,stage=stage,inputs={p:[pin(b)for b in bs]for p,bs in pins.items()if a["pin_dir"][ci][p]=="in"},outputs=out,consumers=users,consumer_count=len(users)))
raw={n:{"direct_loads":loads[resolve(bit)[0]],"load_count":len(loads[resolve(bit)[0]])}for n,(direction,bit)in g.ports.items()if direction=="input" and n in ("por_n","host_rst_n")}
result=dict(schema="peer_actual_reset_graph_review_only.v1",source_sha256=r["source_sha256"],mapped_sha256=hashlib.sha256(Path("resynth.v").read_bytes()).hexdigest(),top=r["top"],core_clock="ck_core",raw_reset_inputs=raw,stages=dict(collections.Counter(x["stage"]for x in rows)),conditioners=rows,physical_models={"DFFHQNx1_ASAP7_75t_R":{"clock":"positive CLK","QN":"not D","asynchronous_controls":False},"DFFASRHQNx1_ASAP7_75t_R":{"clock":"positive CLK","QN":"not D","SETN=0":"QN=0","RESETN=0,SETN=1":"QN=1","both=0":"QN=0"}},source_contract="Outer registered2edge assert/release plus regional asynchronous assert and3edge release. Actual pin/root details authoritative; no plain2edge BRP waiver.")
Path("reset_graph_profile.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items()if k not in ("conditioners","raw_reset_inputs")}));print({n:z["load_count"]for n,z in raw.items()})
