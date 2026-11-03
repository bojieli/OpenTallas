#!/usr/bin/env python3
"""Plan-first portable M5 entry class for unsigned E2 and IDX hard cores.
Creates NEW pin/LEF artifacts and changes only those refs on the current plan.
Existing source contracts are preserved byte-for-byte. No RTL/outline/latency change.
"""
import argparse,copy,hashlib,json,re
from pathlib import Path

def apply(root,plan_path):
 root=Path(root);pp=Path(plan_path);pp=pp if pp.is_absolute() else root/pp
 plan=json.loads(pp.read_text());base=pp.parent;report=[]
 cfg={"dsdv_eng_rr_e":("ck",[172.908,.24]),"dsdv_idx_tx_n32":("ck",[.06,140.892])}
 for mod,(name,xy) in cfg.items():
  cores=[c for t in plan["partition_types"].values() for c in t.get("hard_cores",[]) if c["module"]==mod]
  assert cores,mod
  first=cores[0];oldpins=base/first["pins_file"];d=json.loads(oldpins.read_text())
  pins=d["pins"];q=next(p for p in pins if p["name"]==name);old=copy.deepcopy(q)
  q.update(layer="M5",x=xy[0],y=xy[1])
  for key in ["rects","rect","native_rects","shapes"]:q.pop(key,None)
  newpf="inputs/core_pins/"+mod+"_clkm5_1101.json"
  d["lef"]="physical/die_plan/s81/cores/legacy/lef/"+mod+"_clkm5_1101.lef"
  d["source"]=d.get("source","")+"; CODEX1101 portable M5 clock-entry class, same unsigned core outline/data pins/latency"
  d["pinhash"]=hashlib.sha256(json.dumps(pins,sort_keys=True).encode()).hexdigest()[:12]
  (base/newpf).write_text(json.dumps(d,indent=1)+"\n")
  src=root/first["lef"];text=src.read_text()
  pat=r"(?ms)^  PIN "+re.escape(name)+r"\n.*?^  END "+re.escape(name)+r"[ \t]*$"
  x,y=xy
  hx=.06 if mod=="dsdv_idx_tx_n32" else .024
  new=("  PIN "+name+"\n    DIRECTION INPUT ;\n    USE CLOCK ;\n    PORT\n      LAYER M5 ;\n"
       +f"        RECT {x-hx:.6f} {y-.24:.6f} {x+hx:.6f} {y+.24:.6f} ;\n    END\n  END "+name)
  text,n=re.subn(pat,new,text);assert n==1,(mod,n)
  newlef="physical/die_plan/s81/cores/legacy/lef/"+mod+"_clkm5_1101.lef"
  (root/newlef).write_text(text)
  for c in cores:
   assert c["pins_file"]==first["pins_file"] or c is first
  for c in cores:c["pins_file"]=newpf;c["lef"]=newlef
  report.append({"module":mod,"old_clock":old,"new_clock":q,"pins_file":newpf,"lef":newlef,"affected_core_entries":len(cores),"rtl_changed":False,"outline_changed":False,"added_cycles":0})
 pp.write_text(json.dumps(plan,indent=1)+"\n")
 return report

if __name__=="__main__":
 a=argparse.ArgumentParser(description=__doc__);a.add_argument("--root",type=Path,required=True);a.add_argument("--plan",type=Path,default=Path("physical/die_plan/s81/plan_h2_2249.json"));a.add_argument("--report",type=Path,required=True);args=a.parse_args()
 args.report.write_text(json.dumps(apply(args.root,args.plan),indent=1)+"\n")
