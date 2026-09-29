#!/usr/bin/env python3
"""Exactness gate of the partitioned matrix engine (rtl/test/tb_qwen_me_partition.sv).

Builds the bench with Verilator (--binary --timing) against a renamed copy of the
ORIGINAL ot_hdc_matvec (main 0e8df511, read with git show), runs it, runs the
MUTANT = 1 negative control (tile ROM slices swapped) which must fail, and
writes a source-pinned record.  What the bench checks is in its header:
unpruned new engine == original on every port every cycle; pruned engine ==
original on every request/write/progress; the tile array == the pruned engine
(every port every cycle with zero wire stages, as event streams plus the exact
added latency otherwise).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIG_COMMIT = "0e8df511"
TB = ROOT / "rtl/test/tb_qwen_me_partition.sv"
RTL = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_qwen_me_array", "ot_qwen_rom_tile", "ot_hdc_matvec", "ot_hdc_fpu",
                                         "ot_hdc_fp32_mul_pipe", "ot_hdc_fastfp", "ot_hdc_delay", "ot_hdc_sfu")] \
    + [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"]


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--param", action="append", default=[], help="NAME=VALUE bench parameter")
    ap.add_argument("--verilator", default=os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--ref-file", type=Path, help="the original ot_hdc_matvec.sv (when this tree has no git)")
    ap.add_argument("--cflags", default="-O0", help="C++ optimisation of the bench (compile time dominates)")
    ap.add_argument("--result", type=Path, required=True)
    a = ap.parse_args()
    out = a.workdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    orig = a.ref_file.read_text() if a.ref_file else subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{ORIG_COMMIT}:rtl/hdc/ot_hdc_matvec.sv"], text=True)
    ref = out / "ot_hdc_matvec_ref.sv"
    ref.write_text(orig.replace("module ot_hdc_matvec #(", "module ot_hdc_matvec_ref #(", 1))
    pins = {str(p.relative_to(ROOT)): sha(p) for p in [TB, *RTL, Path(__file__)]}
    params = [f"-G{p}" for p in a.param]
    steps = []

    def build(tag, extra):
        mdir = out / tag
        t0 = time.monotonic()
        p = subprocess.run([a.verilator, "--binary", "--timing", "-j", str(a.jobs), "-O2", "-Wno-fatal", "-Wno-lint",
                            "-Wno-style", "-Wno-TIMESCALEMOD", "-CFLAGS", a.cflags, "--output-split", "20000",
                            "--output-split-cfuncs", "2000", "--x-assign", "fast", "--x-initial", "fast",
                            "--top-module", "tb_qwen_me_partition",
                            *params, *extra,
                            "--Mdir", str(mdir), str(TB), *map(str, RTL), str(ref)], capture_output=True, text=True)
        (out / f"build_{tag}.log").write_text(p.stdout + p.stderr)
        steps.append({"step": f"build_{tag}", "seconds": round(time.monotonic() - t0, 1), "rc": p.returncode})
        if p.returncode:
            raise SystemExit(f"build {tag} failed; see {out}/build_{tag}.log")
        t0 = time.monotonic()
        s = subprocess.run([str(mdir / "Vtb_qwen_me_partition")], capture_output=True, text=True)
        (out / f"sim_{tag}.log").write_text(s.stdout + s.stderr)
        steps.append({"step": f"sim_{tag}", "seconds": round(time.monotonic() - t0, 1), "rc": s.returncode})
        return s.stdout
    text = build("dut", [])
    mut = build("mutant", ["-GMUTANT=1"])
    verdict = next((l for l in text.splitlines() if l.startswith(("PASS", "FAIL"))), "")
    mverdict = next((l for l in mut.splitlines() if l.startswith(("PASS", "FAIL"))), "")
    passed = verdict.startswith("PASS")
    rejected = mverdict.startswith("FAIL")
    stable = pins == {str(p.relative_to(ROOT)): sha(p) for p in [TB, *RTL, Path(__file__)]}
    rec = {"schema": "opentallas.qwen-me-partition-gate.v1",
           "status": "pass" if passed and rejected and stable else "fail",
           "params": dict(x.split("=", 1) for x in a.param), "verdict": verdict,
           "negative_control": mverdict, "negative_control_rejected": rejected,
           "reference": f"rtl/hdc/ot_hdc_matvec.sv at {ORIG_COMMIT} (renamed ot_hdc_matvec_ref)",
           "reference_sha256": sha(ref), "source_sha256": pins, "source_stable": stable, "steps": steps,
           "verilator": subprocess.check_output([a.verilator, "--version"], text=True).strip(),
           "claim_boundary": ("Random back-to-back dense and KV-sourced ops on hash-image memories at the listed "
                              "small group count; exactness of the partition, pruning and wire stages against the "
                              "original engine. Not a checkpoint, token, timing or physical result.")}
    a.result.parent.mkdir(parents=True, exist_ok=True)
    a.result.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rec[k] for k in ("status", "verdict", "negative_control")}, indent=1))
    if rec["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
