import sys,json,hashlib
from pathlib import Path
base=Path.cwd();src=base/"src_e6846a038";sys.path.insert(0,str(src/"tools"));import textbook_lint as T
for q in [3,2]:
 d=base/f"map{q}_e68";p=next((d/"results").rglob("1_2_yosys.v"));g,top=T.flatten(T.parse_verilog(p.read_text()),None);A=T.build(g,None);clk,_=T.clock_nets(g,A);rows=[]
 for x,(ci,pn) in A["driver"].items():
  if x in clk or x<=3 or (ci>=0 and A["kind"][ci] in ["buf","tie"]):continue
  n,f,ex=T.bufinv_fanout(g,A,x,clk)
  rows.append(dict(loads=n,flops=f,driver=T.net_label(g,A,x)))
 rows.sort(key=lambda r:r["loads"],reverse=True)
 leaf=src/"rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_safe_leaves.sv"
 out=dict(schema="opentallas.codex.native_exact.v1",source_commit="e6846a038",top=top,mapped_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),leaf_sha256=hashlib.sha256(leaf.read_bytes()).hexdigest(),drivers_examined=len(rows),max_loads=rows[0]["loads"],over32=[r for r in rows if r["loads"]>32],top_drivers=rows[:12],verdict="PASS" if rows[0]["loads"]<=32 else "FAIL")
 (d/"native_exact.json").write_text(json.dumps(out,indent=1)+"\n");print(q,out["verdict"],out["max_loads"],out["drivers_examined"])
