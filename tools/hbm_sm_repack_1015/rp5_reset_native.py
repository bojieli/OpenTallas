#!/usr/bin/env python3
"""Fleet-only synth/native receipt for the SMH-local reset repair.
Reuse the exact failed gate configuration/libs, never its mapped netlist.
"""
import argparse,json,os,subprocess
from pathlib import Path
OLD={"s_m":"smh_rp5s_m-20261021-132224","s_f":"smh_rp5s_f-20261021-132225",
     "n_m":"smh_rp5n_m-20261021-132207","n_f":"smh_rp5n_f-20261021-132221"}
PATCH="rtl/hbm_accel/sm/repack/h2a5/ot_rp5_land_reset_split.sv"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("root");ap.add_argument("form",choices=OLD);a=ap.parse_args()
    root=Path(a.root);src=root/"src";work=root/("native_"+a.form);work.mkdir(exist_ok=True)
    old=Path("/srv/opentallas-scratch/claude/ref_gate")/OLD[a.form]/"routes/gate/work/orfs"
    report=json.loads((old/"native_census.json").read_text())
    cfg=(old/"config.mk").read_text().replace("/src/rtl/common/landed_parent/ot_pl_land_reset_forest.sv","/src/"+PATCH)
    (work/"config.mk").write_text(cfg+"\nexport NUM_CORES = 4\n")
    inside=Path(report["netlist"]["path"])
    args=["python3","/src/tools/ref_tile/native_census.py","--netlist",str(inside),"--top",report["top"],
          "--out","/work/native_census.json","--kit","smh_rp5"+a.form]
    for v in report["liberty"]:args += ["--liberty",v["path"]]
    # Original immutable source/config/old failure remain untouched. New work
    # contains no prior mapped netlist, so synthesis must really execute.
    image="openroad/orfs:latest"
    cmd=["docker","run","--rm","--user",f"{os.getuid()}:{os.getgid()}","-v",f"{src}:/src:ro",
         "-v",f"{work}:/work","-w","/OpenROAD-flow-scripts/flow",image,"bash","-lc",
         "make DESIGN_CONFIG=/work/config.mk NUM_CORES=4 synth && "+__import__("shlex").join(args)]
    rc=subprocess.call(cmd)
    print("RESET_NATIVE_EXIT",a.form,rc,flush=True)
    if (work/"native_census.json").exists():
        d=json.loads((work/"native_census.json").read_text())
        print("RESET_NATIVE_RESULT",a.form,d["status"],d["max_dynamic_loads"],len(d["violations"]),len(d["role_errors"]),flush=True)
    raise SystemExit(rc)
if __name__=="__main__":main()
