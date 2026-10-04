#!/usr/bin/env python3
"""HA3 system runs: the HBM-accelerator system top rtl/hbm_accel/collective/ot_hbm_accel_hbm_system.sv under
Verilator 5.050 with the bench rtl/test/hbm_accel/tb_hbm_accel_ha3_system.sv, one program per run
(tools/hbm_accel_ha3.py --mode base | cut | fuse), every decode step checked against the golden's next token and the
completion ring's token stream against the golden generation (the checks of tools/gpu_sys/run_system.py).

    python3 tools/hbm_accel_ha3_run.py --model qwen --mode fuse --ha3 1 --work DIR [--trace] [--out rec.json]
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
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "gpu_sys"))
sys.path.insert(0, str(HERE))
import mem_image  # noqa: E402
import run_system as RS  # noqa: E402

HA3_SRC = ["rtl/hbm_accel/collective/ot_hbm_accel_simt_sm.sv", "rtl/hbm_accel/collective/ot_hbm_accel_coll_port.sv",
           "rtl/hbm_accel/collective/ot_hbm_accel_hbm_system.sv"]
TB = "rtl/test/hbm_accel/tb_hbm_accel_ha3_system.sv"


def sources():
    return RS.SYS_SRC + RS.DEP_SRC + HA3_SRC + [TB]


def build(work, model, ha3, flat=5, epi=1):
    obj = Path(work) / f"obj_ha3_{model}_h{ha3}" if flat == 5 else Path(work) / f"obj_ha3_{model}_h{ha3}_f{flat}"
    if epi != 1:
        obj = obj.with_name(obj.name + f"_e{epi}")
    exe = obj / "Vtb_hbm_accel_ha3_system"
    if exe.exists():
        return exe
    cmd = [str(RS.VERILATOR), "--binary", "--timing", "-O2", "-j", os.environ.get("GPU_SYS_JOBS", "8"), "-Wno-fatal",
           "-Wno-lint", "-Wno-style", "-Wno-WIDTH", "--x-assign", "0", "--x-initial", "0",
           "--top-module", "tb_hbm_accel_ha3_system", "--Mdir", str(obj), f"-GHA3={ha3}", f"-GFLAT={flat}", f"-GEPI={epi}"] + \
          [f"-G{k}={v}" for k, v in RS.MODEL_PARAMS[model].items()] + \
          (["--threads", os.environ["GPU_SYS_THREADS"]] if os.environ.get("GPU_SYS_THREADS") else []) + \
          [str(ROOT / s) for s in sources()]
    t0 = time.time()
    subprocess.run(cmd, check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    print(f"build {time.time() - t0:.0f} s", flush=True)
    return exe


def prepare(model, mode, case, ngen, nprompt=None):
    case = Path(case)
    if model == "qwen":
        import hbm_accel_ha3 as H
        import qwen_hbm as Q
        H.use(mode)
        meta = Q.emit(case, ngen)
    else:
        import hbm_accel_ha3_v41 as HV
        meta = HV.emit(case, mode, ngen, nprompt)
    meta["ha3_mode"] = mode
    (case / "expected.json").write_text(json.dumps(meta, indent=1) + "\n")
    for d in range(meta["tp"]):
        blob = np.fromfile(case / f"die{d}.bin", dtype=np.uint8)
        mem_image.write_images({0: blob}, RS.NS, RS.MODEL_PARAMS[model]["MEM_WORDS"], case, prefix=f"die{d}")
    steps = meta["steps"]
    lines = [f"{len(steps)} {len(meta['prompt'])} {ngen} {meta['imem_words']} {len(meta['entries']) + 1}"]
    lines += [f"{s['input']} {s['next']}" for s in steps]
    lines += [str(t) for t in meta["prompt"]]
    (case / "tb_cfg.txt").write_text("\n".join(lines) + "\n")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen", choices=["qwen", "v41"])
    ap.add_argument("--mode", default="base", choices=["base", "cut", "fuse", "fuseo"])
    ap.add_argument("--ha3", type=int, default=1)
    ap.add_argument("--work", required=True)
    ap.add_argument("--ngen", type=int, default=3)
    ap.add_argument("--nprompt", type=int, default=None)
    ap.add_argument("--trace", action="store_true")
    ap.add_argument("--flat", type=int, default=5)
    ap.add_argument("--epi", type=int, default=1, help="HA3 port epilogue (0: cut-through only, fused requests fault)")
    ap.add_argument("--prepared", action="store_true")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    case = work / f"case_{a.model}_{a.mode}"
    case.mkdir(exist_ok=True)
    srcs = sources() + ["tools/hbm_accel_ha3.py", "tools/hbm_accel_ha3_run.py"] + \
        [str(p.relative_to(ROOT)) for p in sorted((HERE / "gpu_sys").glob("*.py")) if p.name in
         ("asm.py", "isa.py", "machine.py", "mem_image.py", "qwen_hbm.py", "v41_hbm.py", "run_system.py")]
    if (HERE / "hbm_accel_ha3_v41.py").exists():
        srcs.append("tools/hbm_accel_ha3_v41.py")
    hashes = {p: RS.sha(p) for p in srcs}
    exe = build(work, a.model, a.ha3, a.flat, a.epi)
    if a.build_only:
        return
    meta = json.loads((case / "expected.json").read_text()) if a.prepared else prepare(a.model, a.mode, case, a.ngen, a.nprompt)
    t0 = time.time()
    stem = f"sim_h{a.ha3}" if a.flat == 5 else f"sim_h{a.ha3}_f{a.flat}"
    log = case / (stem + ("" if a.epi == 1 else f"_e{a.epi}") + ".log")
    with log.open("w") as f:
        r = subprocess.run([str(exe), "+DIR=."] + (["+TRACE=1"] if a.trace else []), cwd=case, stdout=f,
                           stderr=subprocess.STDOUT)
    wall = time.time() - t0
    text = log.read_text()
    steps = [dict(zip(("step", "pos", "input", "next"), map(int, m.groups()[:4])), status=m.group(5),
                  step_cycles=int(m.group(6)) if m.group(6) else None)
             for m in re.finditer(r"STEP (\d+) pos (\d+) in (\d+) next (\d+) (OK|MISMATCH)?(?:\s+\(step (\d+))?", text)]
    final = re.search(r"TB_GPU_HBM_SYSTEM (PASS|FAIL) steps=(\d+) cq_tokens=(\d+) clk_sm_cycles=(\d+) fails=(\d+)", text)
    ok = bool(final and final.group(1) == "PASS" and r.returncode == 0)
    rec = dict(schema="opentallas.hbm_accel.ha3_system_run.v1", model=a.model, mode=a.mode, ha3=a.ha3, flat=a.flat, epi=a.epi,
               tool="tools/hbm_accel_ha3_run.py", top="ot_hbm_accel_hbm_system", bench=TB,
               simulator=subprocess.run([str(RS.VERILATOR), "--version"], capture_output=True, text=True).stdout.strip(),
               golden=meta.get("golden"), prompt=meta["prompt"], expected_steps=meta["steps"], steps=steps,
               kernel_words=meta.get("kernel_words"),
               clk_sm_cycles=int(final.group(4)) if final else None, wall_seconds=round(wall, 1),
               status="pass" if ok else "fail", trace=a.trace, source_sha256=hashes)
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(text[-2500:])
    print("HA3_RUN", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
