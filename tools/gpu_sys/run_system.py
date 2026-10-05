#!/usr/bin/env python3
"""End-to-end functional simulation of a GPU-organised HBM comparator system top (rtl/gpu_sys/ot_gpu_hbm_system.sv)
under Verilator 5.050: the host driver (rtl/test/gpu_sys/tb_gpu_hbm_system.sv) loads the kernels and the per-die
command graphs, submits one GENERATE request through the NVMe-style host interface, and every decode step the
chip runs is checked against the golden's next token; the completion ring's token stream against the golden
generation.

    python3 tools/gpu_sys/run_system.py --model qwen [--work DIR] [--out results/rtl/hbm_system_rtl_20261003/qwen_e2e.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import mem_image  # noqa: E402

VERILATOR = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
NS = 2
MODEL_PARAMS = {"qwen": dict(MEM_WORDS=65536, HAS_DIV=0, HAS_BD=0), "v41": dict(MEM_WORDS=1 << 21, HAS_DIV=1, HAS_BD=1)}
SYS_SRC = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "rtl/gpu_sys").glob("*.sv"))
DEP_SRC = ["rtl/gpu/ot_gpu_sm.sv", "rtl/gpu/ot_gpu_bulk_copy.sv", "rtl/gpu/ot_gpu_fadd.sv", "rtl/gpu/ot_gpu_barrier_node.sv",
           "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fastfp.sv",
           "rtl/gpu/ot_gpu_tree.sv", "rtl/gpu/ot_gpu_issue.sv", "rtl/gpu/ot_gpu_stack.sv", "rtl/gpu/ot_gpu_tc_col.sv",
           "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
           "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_prefix.sv",
           "rtl/abi3/ot_a3_fp32_div_rne_pipe.sv", "rtl/abi3/ot_a3_fp32_sqrt_rne.sv",
           "rtl/gpu/ot_gpu_sm_bd.sv", "rtl/gpu/ot_gpu_bd_col.sv", "rtl/hdc/v41/ot_hdc_blockdot.sv",
           "rtl/v41rom/ot_v41_bterm.sv", "rtl/v41rom/ot_v41_bterm2.sv",
           "rtl/link/ot_link_afifo.sv", "rtl/link/ot_link_nvls_switch.sv", "rtl/hdc/kv/ot_hdc_hbm_model.sv",
           "rtl/host/ot_host_if.sv", "rtl/experimental/w2_nc6_completion_20261003/ot_hdc_qwen_pc_exact_completion.sv"]
TB = "rtl/test/gpu_sys/tb_gpu_hbm_system.sv"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def build(work, model="qwen"):
    obj = Path(work) / (("obj_sys_w2" if os.environ.get("GPU_SYS_USE_W2") == "1" else "obj_sys") + "_" + model +
                        ("_trace" if os.environ.get("GPU_SYS_TRACE") == "1" else ""))
    exe = obj / "Vtb_gpu_hbm_system"
    if exe.exists():
        return exe
    cmd = [str(VERILATOR), "--binary", "--timing", "-O2", "-j", os.environ.get("GPU_SYS_JOBS", "4"), "-Wno-fatal",
           "-Wno-lint", "-Wno-style", "-Wno-WIDTH", "--x-assign", "0", "--x-initial", "0",
           "--top-module", "tb_gpu_hbm_system", "--Mdir", str(obj)] + \
          [f"-G{k}={v}" for k, v in MODEL_PARAMS[model].items()] + \
          (["--threads", os.environ["GPU_SYS_THREADS"]] if os.environ.get("GPU_SYS_THREADS") else []) + \
          (["-DGPU_SYS_USE_W2"] if os.environ.get("GPU_SYS_USE_W2") == "1" else []) + \
          (["-DGPU_SYS_TRACE"] if os.environ.get("GPU_SYS_TRACE") == "1" else []) + [str(ROOT / s) for s in SYS_SRC + DEP_SRC + [TB]]
    t0 = time.time()
    with open(obj.parent / (obj.name + "_build.log"), "w") as blog:   # keep Verilator's warnings (UNOPTFLAT, ...)
        subprocess.run(cmd, check=True, cwd=ROOT, stdout=blog, stderr=subprocess.STDOUT)
    print(f"build {time.time() - t0:.0f} s", flush=True)
    return exe


def prepare(model, case, ngen, nprompt=None):
    case = Path(case)
    if model == "qwen":
        import qwen_hbm
        meta = qwen_hbm.emit(case, ngen)
    else:
        import v41_hbm
        meta = v41_hbm.emit(case, ngen, nprompt)
    for d in range(meta["tp"]):
        blob = np.fromfile(case / f"die{d}.bin", dtype=np.uint8)
        mem_image.write_images({0: blob}, NS, MODEL_PARAMS[model]["MEM_WORDS"], case, prefix=f"die{d}")
    steps = meta["steps"]
    lines = [f"{len(steps)} {len(meta['prompt'])} {ngen} {meta['imem_words']} {len(meta['entries']) + 1}"]
    lines += [f"{s['input']} {s['next']}" for s in steps]
    lines += [str(t) for t in meta["prompt"]]
    (case / "tb_cfg.txt").write_text("\n".join(lines) + "\n")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen", choices=["qwen", "v41"])
    ap.add_argument("--work", default=None)
    ap.add_argument("--ngen", type=int, default=3)
    ap.add_argument("--nprompt", type=int, default=None, help="v41: teacher-forced prompt prefix length")
    ap.add_argument("--maxcyc", type=int, default=None, help="optional diagnostic cycle bound; omitted means run until completion")
    ap.add_argument("--out", default=None)
    ap.add_argument("--prepared", action="store_true", help="reuse WORK/case written by an earlier prepare()")
    a = ap.parse_args()
    if a.maxcyc is not None and a.maxcyc <= 0:
        ap.error("--maxcyc must be positive when explicitly supplied")
    work = Path(a.work or f"/tmp/gpu_sys_{a.model}")
    work.mkdir(parents=True, exist_ok=True)
    case = work / "case"
    hashes = {p: sha(p) for p in SYS_SRC + DEP_SRC + [TB] + [str(p.relative_to(ROOT)) for p in sorted(HERE.glob("*.py"))]}
    if a.prepared:
        meta = json.loads((case / "expected.json").read_text())   # case written earlier by prepare() (e.g. on another host)
    else:
        meta = prepare(a.model, case, a.ngen, a.nprompt)
    exe = build(work, a.model)
    t0 = time.time()
    log = case / "sim.log"
    with log.open("w") as f:
        r = subprocess.run([str(exe), "+DIR=."] + ([f"+MAXCYC={a.maxcyc}"] if a.maxcyc is not None else []), cwd=case, stdout=f, stderr=subprocess.STDOUT)
    wall = time.time() - t0
    text = log.read_text()
    steps = [dict(zip(("step", "pos", "input", "next"), map(int, m.groups()[:4])), status=m.group(5),
                  step_cycles=int(m.group(6)) if m.group(6) else None)
             for m in re.finditer(r"STEP (\d+) pos (\d+) in (\d+) next (\d+) (OK|MISMATCH)?(?:\s+\(step (\d+))?", text)]
    cq = [dict(zip(("kind", "status", "slot", "tag", "pos", "token", "cycles", "generated"), map(int, m.groups())))
          for m in re.finditer(r"CQ kind (\d+) status (\d+) slot (\d+) tag (\d+) pos (\d+) token (\d+) step_cycles (\d+) generated (\d+)", text)]
    final = re.search(r"TB_GPU_HBM_SYSTEM (PASS|FAIL) steps=(\d+) cq_tokens=(\d+) clk_sm_cycles=(\d+) fails=(\d+)", text)
    ok = bool(final and final.group(1) == "PASS" and r.returncode == 0)
    rec = dict(schema="opentallas.gpu_sys.e2e.v1", model=a.model, tool="tools/gpu_sys/run_system.py",
               simulator=subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip(),
               golden=meta.get("golden"), prompt=meta["prompt"], expected_steps=meta["steps"],
               steps=steps, completions=cq, clk_sm_cycles=int(final.group(4)) if final else None,
               wall_seconds=round(wall, 1), status="pass" if ok else "fail",
               shape=dict(dies=meta["tp"], sms_per_die=meta["nsm"], simt_lanes=meta["nl"], tc_lanes=16,
                          l2_slices_per_die=NS, hbm_partitions_per_die=NS, rtl_params=MODEL_PARAMS[a.model],
                          use_w2=os.environ.get("GPU_SYS_USE_W2") == "1", pseudo_channels_per_partition=2,
                          clocks_ps=dict(host=4000, sm=833, mem=1000, link=900)),
               source_sha256=hashes)
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(text[-3000:])
    print("RUN_SYSTEM", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
