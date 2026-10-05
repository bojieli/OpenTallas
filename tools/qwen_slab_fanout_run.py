#!/usr/bin/env python3
"""One fixed fanout recipe, invoked through unchanged EPYC admit.sh; never resume/restart."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import qwen_slab_fanout as model

SOURCES=["rtl/common/ot_meso_fifo.sv","rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/ot_hdc_fp32_mul_lat.sv","rtl/hdc/ot_hdc_fp32_add_lat.sv",
    "rtl/hdc/ot_hdc_fastfp.sv","rtl/hdc/ot_hdc_prefix.sv",
    "physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v"]


def command(r,out):
    args=[sys.executable,"tools/run_abi3_physical_persistent.py",
        "--persistent-workdir",str(out/"work"),"--launch-receipt",str(out/"launch.json"),
        "--view","asap7","--top",r["source_top"]]
    for source in [r["rtl"],*SOURCES]:args.extend(["--source",source])
    for name,value in r["selection"].items():args.extend(["--param",f"{name}={value}"])
    args.extend(["--macro-view","ot_rom_4096x266_m8=physical/asap7_memory_macros/ot_rom_4096x266_m8",
        "--macro-place-halo","2.16","2.16",*r["physical_args"],"--routing-layers","M2","M7",
        "--clock-port","clk","--clock-period-ns","0.833333","--clock-uncertainty-ns","0.06",
        "--clock-uncertainty-hold-ns","0.025","--orfs-corner","WC","--hold-corners","WC,BC",
        "--io-delay-fraction","0.2","--stages","pnr","--hold-margin-ns","0.01",
        "--synth-timeout-seconds","unlimited","--flow-timeout-seconds","unlimited",
        "--orfs-var","ADDER_MAP_FILE=","--orfs-var","NUM_CORES=16",
        "--orfs-var","SDC_FILE=/src/physical/qwen_slab_fanout/finite_boundary.sdc",
        "--orfs-var","PDN_TCL=/src/physical/qwen_slab_m5/pdn_m5.tcl",
        "--orfs-var",f"MACRO_PLACEMENT_TCL=/src/{r['macro_placement_tcl']}",
        "--nickname-tag",r["variant"],"--purpose","signoff_target","--output",str(out/"physical.json")])
    return args


def main():
    p=argparse.ArgumentParser();p.add_argument("--kind",choices=model.KINDS,required=True)
    p.add_argument("--height",type=int,choices=model.HEIGHTS,required=True)
    p.add_argument("--root",type=Path,required=True);p.add_argument("--source-commit",required=True)
    a=p.parse_args();os.chdir(model.ROOT)
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if head!=a.source_commit or subprocess.check_output(["git","status","--porcelain"],text=True):
        p.error("exact clean pinned source required")
    r=model.recipe(a.kind,a.height);out=a.root/r["variant"]
    out.mkdir(parents=False,exist_ok=False)
    argv=command(r,out)
    (out/"recipe.json").write_text(json.dumps(dict(recipe=r,source_commit=head,argv=argv),indent=2)+"\n")
    env=os.environ.copy();env.update(OT_ORFS_NUM_CORES="16",NUM_CORES="16",
        OT_SYNTH_TIMEOUT_SECONDS="unlimited",OT_FLOW_TIMEOUT_SECONDS="unlimited")
    with (out/"driver.log").open("w") as log:
        result=subprocess.run(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
    (out/"driver.exit").write_text(str(result.returncode)+"\n")
    final=list((out/"work/orfs/results/asap7").glob("*/base/6_final.odb"))
    if final:
        with (out/"corner.log").open("w") as log:
            corner=subprocess.run([sys.executable,"tools/w18/corner_sta.py","--orfs-dir",str(out/"work/orfs"),
                "--macro","physical/asap7_memory_macros/ot_rom_4096x266_m8","--output",str(out/"corner_sta.json")],
                env=env,stdout=log,stderr=subprocess.STDOUT)
        (out/"corner.exit").write_text(str(corner.returncode)+"\n")
    return result.returncode
if __name__=="__main__":sys.exit(main())
