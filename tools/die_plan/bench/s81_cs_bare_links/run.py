#!/usr/bin/env python3
"""Small actual CS RTL lockstep and missing-stage control; run via ot-run."""
import argparse,json,os,resource,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("out",type=Path);a=p.parse_args()
r=Path(__file__).resolve().parents[4];a.out.mkdir(parents=True,exist_ok=True)
s=(r/"rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv").read_text()
(a.out/"actual_cst.sv").write_text(s[s.index("module ot_s81sl_cst1"):])
shutil.copyfile(Path(__file__).with_name("tb.sv"),a.out/"tb.sv")
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
verilator=shutil.which("verilator") or str(Path.home()/".local/opentallas-tools/bin/verilator")
with (a.out/"build.log").open("w") as log:
 subprocess.run([verilator,"--binary","--timing","-Wno-fatal","--top-module","tb","-j","4","--Mdir","obj","actual_cst.sv","tb.sv"],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True)
rows={}
for name,args in (("nominal",[]),("mutant",["+MUT"])):
 q=subprocess.run([str(a.out.resolve()/"obj/Vtb"),*args],cwd=a.out,capture_output=True,text=True)
 text=q.stdout+q.stderr;(a.out/f"{name}.log").write_text(text)
 rows[name]=dict(rc=q.returncode,pass_marker="CST_LOCKSTEP_PASS" in text,fault_marker="CST_LOCKSTEP_FAIL" in text)
ok=rows["nominal"]["rc"]==0 and rows["nominal"]["pass_marker"] and rows["mutant"]["rc"]!=0 and rows["mutant"]["fault_marker"]
(a.out/"summary.json").write_text(json.dumps(dict(verdict="PASS" if ok else "FAIL",runs=rows),indent=1))
raise SystemExit(0 if ok else 1)
