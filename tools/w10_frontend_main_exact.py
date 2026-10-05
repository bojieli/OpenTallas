#!/usr/bin/env python3
"""Full W10 RTL equivalence, cycle protocol, and an address-error negative control."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = [f"rtl/v41rom/{n}.sv" for n in (
    "ot_v41_rom_elem_w10", "ot_v41_bterm", "ot_v41_chain", "ot_v41_segtree", "ot_v41_bf16_lanes",
    "ot_v41_fadd", "ot_v41_bmul2", "ot_v41_bterm2_w10", "ot_v41_chain2", "ot_v41_segtree2", "ot_v41_bf16_lanes2")]
RTL += [f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_delay", "ot_hdc_cg")]
RTL += ["rtl/common/ot_prefix.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/test/tb_w10_frontend_main_exact.sv"]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--verilator", default=str(Path.home()/".local/opentallas-tools/verilator-5.050/bin/verilator"))
    ap.add_argument("--fast", type=int, choices=(0,1), default=1)
    ap.add_argument("--pp", type=int, choices=(0,1), default=1)
    a = ap.parse_args()
    status = subprocess.check_output(["git", "status", "--porcelain"],cwd=ROOT,text=True)
    if status.strip():
        raise SystemExit("exact gate requires a pinned clean worktree")
    a.work.mkdir(parents=True,exist_ok=True)
    record = dict(schema="opentallas.w10.frontend.exact.v1", verdict="FAIL", adopted=False,
                  git_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                  clean_worktree=True, parameters=dict(FAST=a.fast,PP=a.pp,NB=2,BF16=1,MTP=1,EARLY=1,XF=8),
                  source_sha256={p:sha(ROOT/p) for p in RTL+["tools/w10_frontend_main_exact.py"]},
                  golden="unchanged baseline FRONT_PAR=0, same complete arithmetic modules, same-cycle full RTL",
                  baseline_commit="66b0bee616464920080aa2c44189c4287a6ec1b4",
                  comparison="public controls every cycle, valid partial data+metadata, walker/facts/FIFO/capture/issue",
                  model_prerequisite="results/uarch/w10_frontend_main_prebuild.json PASS_SIZING_ONLY",
                  cases=["sparse classes 0/3/7 with 9/3/2 units", "8-bit wrap base 252", "all eight FP8 classes",
                         "q advance", "three MTP positions", "wrong pair/b/position and invalid beat",
                         "bubbles", "empty Q family", "sequential reconfiguration", "mid-operation reset"],
                  tool_version=subprocess.check_output([a.verilator,"--version"],text=True).strip(), runs=[])
    model=json.loads((ROOT/record["model_prerequisite"].split()[0]).read_text())
    if model["verdict"]!="PASS_SIZING_ONLY":
        raise SystemExit("model sizing must pass before exact gate")
    try:
        for name, mutant in (("positive",False),("negative",True)):
            build=a.work/name
            cmd=[a.verilator,"--binary","--timing","-Wno-fatal","-Wno-lint","-Wno-style",
                 "--top-module","tb_w10_frontend_main_exact","--Mdir",str(build),"-j",str(a.jobs),
                 "-CFLAGS","-O0",f"-GFAST={a.fast}",f"-GPP={a.pp}"]
            if mutant: cmd.append("+define+W10_MUTANT_FRONT_PAIR")
            cmd += [str(ROOT/p) for p in RTL]
            with (a.work/f"{name}.build.log").open("w") as f:
                p=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
            if p.returncode:
                raise RuntimeError(f"{name} build failed: {a.work/name}.build.log")
            p=subprocess.run([str(build/"Vtb_w10_frontend_main_exact")],cwd=a.work,capture_output=True,text=True)
            log=p.stdout+p.stderr
            (a.work/f"{name}.run.log").write_text(log)
            coverage=re.search(r"PASS cycles=(\d+) hits=(\d+) issues=(\d+) rows=(\d+) nonzero=(\d+) classes=(\d+) wraps=(\d+) qadv=(\d+) restarts=(\d+) rejected=(\d+)",log)
            run=dict(name=name,returncode=p.returncode,build_command=cmd,log_sha256=sha(a.work/f"{name}.run.log"))
            if not mutant:
                if p.returncode or not coverage: raise RuntimeError(f"positive failed: {log[-2000:]}")
                run["coverage"]=dict(zip(("cycles","hits","issues","rows","nonzero","classes_mask","wraps","q_advances","mtp_restarts","rejected"),map(int,coverage.groups())))
                run["frontend_latency_delta_cycles"]=0
            else:
                if p.returncode==0 or "frontend divergence" not in log:
                    raise RuntimeError("negative control failed to detect wrong pair-address addition")
                run["caught"]=True
                run["mutation"]="FRONT_PAR expected_pair + 1, baseline unaffected"
                run["failure_excerpt"]=log[:800]
            record["runs"].append(run)
        record["verdict"]="PASS"
    except Exception as e:
        record["error"]=str(e)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.exists(): raise SystemExit("refusing to overwrite an existing verdict")
    a.output.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:record[k] for k in ("verdict","git_commit","runs")},indent=2))
    return 0 if record["verdict"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
