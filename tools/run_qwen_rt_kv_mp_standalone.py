#!/usr/bin/env python3
"""Standalone Verilator bench of the MULTI-POSITION KV service (DSpark verify blocks), against expected data.

  rtl/test/qwen_rom_runtime/realmem/tb_qwen_rt_kv_mp_service.{sv,cpp} over
  rtl/hdc/kv/ot_qwen_rt_kv_mp_service.sv + the HBM model with write-done (rtl/hdc/kv/ot_qwen_hbm_model_ack.sv).

  VPMAX = 1: every single-position case of tools/run_qwen_rt_realmem_standalone.py's KV bench; its PASS and
             STATS lines must equal those of the pinned service (ot_qwen_rt_kv_fill_service, built here too).
  VPMAX = 4, 8: the same single-position cases at np = 1 (must equal the pinned service's lines), then chains
             of speculative steps on one persistent HBM layer region (blocks of np <= 4 positions with
             rejected drafts, an AR step after a rejection, 16-position tile and 512-row crossings, the
             window end), every slice byte and every committed/block HBM row exact after each step, with
             the slices cleared between steps (other layers use them), and seven negative cases.
Writes one JSON record (source-pinned).
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
RM = ROOT / "rtl/test/qwen_rom_runtime/realmem"
HBM = ROOT / "rtl/hdc/kv/ot_qwen_hbm_model_ack.sv"
MP = [ROOT / "rtl/hdc/kv/ot_qwen_rt_kv_mp_service.sv", HBM, RM / "tb_qwen_rt_kv_mp_service.sv", RM / "tb_qwen_rt_kv_mp_service.cpp"]
PIN = [ROOT / "rtl/hdc/kv/ot_qwen_rt_kv_fill_service.sv", HBM, RM / "tb_qwen_rt_kv_service.sv", RM / "tb_qwen_rt_kv_service.cpp"]
FLAGS = ["--cc", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lines(text, n=None):
    out = [ln for ln in text.splitlines() if ln.startswith(("PASS", "FAIL", "STATS"))]
    return out if n is None else out[:n]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--result", type=Path, required=True)
    ap.add_argument("--verilator", default=os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    srcs = sorted(set(MP + PIN + [Path(__file__)]))
    rec = {"schema": "opentallas.qwen-dspark-kv-mp-standalone.v1",
           "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in srcs},
           "verilator": subprocess.check_output([a.verilator, "--version"], text=True).strip(), "benches": {}}

    def sh(cmd, log):
        p = subprocess.run(list(map(str, cmd)), cwd=work, capture_output=True, text=True)
        (work / log).write_text(p.stdout + p.stderr)
        return p

    def build(top, srcs, mdir, gen, cflags):
        p = sh([a.verilator, *FLAGS, "--exe", "--build", "-GLKA=512", *gen, "--top-module", top, "-Mdir", mdir,
                *srcs, "-CFLAGS", cflags, "-j", a.jobs], f"{mdir}_build.log")
        if p.returncode:
            raise SystemExit(f"build {mdir} failed: {p.stdout[-2000:]}{p.stderr[-2000:]}")

    build("tb_qwen_rt_kv_service", PIN, "pinned", [], "-O1")
    ref = sh([work / "pinned/Vtb_qwen_rt_kv_service"], "pinned.log")
    ref_lines = lines(ref.stdout)
    n_pos = sum(1 for ln in ref_lines if not ln.startswith(("STATS NEG", "PASS NEG", "FAIL NEG")))
    ok = ref.returncode == 0
    for vp in (1, 4, 8):
        build("tb_qwen_rt_kv_mp_service", MP, f"vp{vp}", [f"-GVPMAX={vp}"], f"-O1 -DVPMAX_B={vp}")
        t0 = time.monotonic()
        r = sh([work / f"vp{vp}/Vtb_qwen_rt_kv_mp_service"], f"vp{vp}.log")
        js = json.loads(r.stdout.strip().splitlines()[-1])
        got = lines(r.stdout)
        # VPMAX = 1: every line equal (incl. the negatives' post-fault traffic); np = 1 at VPMAX > 1: every positive case
        same = got[:len(ref_lines)] == ref_lines if vp == 1 else got[:n_pos] == ref_lines[:n_pos]
        js["single_position_lines_equal_pinned"] = same
        js["stats"] = [ln for ln in r.stdout.splitlines() if ln.startswith("STATS")]
        js["wall_s"] = round(time.monotonic() - t0, 1)
        rec["benches"][f"vpmax{vp}"] = js
        ok &= r.returncode == 0 and js["status"] == "pass" and same
    rec["status"] = "pass" if ok else "fail"
    a.result.parent.mkdir(parents=True, exist_ok=True)
    a.result.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["status"])
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
