#!/usr/bin/env python3
"""Matched reduced Qwen TP-2 INT8 ROM/HBM supply arms on one program/images."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HDC_SU_WIDTH", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_qwen_int8_ref as REF  # noqa: E402
import rtl_hdc_decode_campaign as C  # noqa: E402

SRC = [*C.HDC, *C.PIPES,
       *(ROOT / f"rtl/hdc/{x}.sv" for x in
         ("ot_hdc_dyn_ttiles", "ot_hdc_qwen_int8_arith", "ot_hdc_qwen_int8_embed_decode",
          "ot_hdc_core_vector_weight")),
       *(ROOT / f"rtl/rom/{x}.sv" for x in
         ("ot_rom_pkg_link", "ot_rom_pkg_ctrl", "ot_rom_oneshot_allreduce", "ot_rom_tp_seq")),
       ROOT / "rtl/hdc/hbm/ot_hdc_qwen_int8_pc_window.sv",
       ROOT / "rtl/hdc/hbm/ot_hdc_qwen_embed_row_hbm.sv",
       ROOT / "rtl/test/tb_hdc_package_tp_int8.sv"]
HARNESS = ROOT / "rtl/test/hdc_package_tp_int8_harness.cpp"
INPUTS = sorted(set([*SRC, HARNESS, Path(__file__), Path(REF.__file__),
                     ROOT / "tools/hdc_qwen_int8_image.py", ROOT / "tools/hdc_program.py",
                     ROOT / "tools/hdc_golden.py", ROOT / "rtl/hdc/ot_hdc_isa.svh"]))
SUMMARY = re.compile(r"PKG_TP nodes=(\d+) dies=(\d+) users=(\d+) generated=(\d+) steps_checked=(\d+) "
                     r"mismatches=(\d+) kv_mismatches=(\d+) vm_mismatches=(\d+) total_cycles=(\d+)")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_command(arm: int, obj: Path, jobs: int):
    return ["verilator", "--cc", "--exe", "--build", "-O0", "-Wno-fatal", "-Wno-WIDTH",
            "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD",
            "--top-module", "tb_hdc_package_tp_int8", "-GD=2", "-GNODES=1", "-GUSERS=1",
            "-GWROM_WORDS=16384", f"-GWEIGHT_HBM={arm}", "-Mdir", str(obj),
            f"-I{C.ISA_SVH.parent}", *map(str, SRC), str(HARNESS), "-CFLAGS", "-O0", "-j", str(jobs)]


def run_arm(work: Path, arm: int, jobs: int, ngen: int, skip_build: bool):
    img = work / "images"
    if not (img / "int8_tp2_reference.json").exists():
        REF.build(img, ngen)
    arm_name = "rom" if arm == 0 else "hbm"
    obj = work / f"obj_{arm_name}"
    binary = obj / "Vtb_hdc_package_tp_int8"
    cmd = build_command(arm, obj, jobs)
    if not skip_build:
        cp = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        (work / f"build_{arm_name}.log").write_text(cp.stdout + cp.stderr)
        if cp.returncode:
            raise RuntimeError(f"{arm_name} build failed: {(cp.stdout+cp.stderr)[-5000:]}")
    sim = subprocess.run([str(binary), f"+DIR={img}", f"+NGEN={ngen}", "+NUSERS=1"],
                         cwd=ROOT, capture_output=True, text=True, timeout=3600)
    (work / f"sim_{arm_name}.log").write_text(sim.stdout + sim.stderr)
    m = SUMMARY.search(sim.stdout)
    names = ("nodes", "dies", "users", "generated", "steps_checked", "mismatches",
             "kv_mismatches", "vm_mismatches", "total_cycles")
    obs = dict(zip(names, map(int, m.groups()))) if m else {}
    ok = (sim.returncode == 0 and "PASS" in sim.stdout and obs.get("nodes") == 1 and
          obs.get("dies") == 2 and obs.get("generated") == ngen and
          obs.get("steps_checked") == 16+ngen-1 and
          all(obs.get(k) == 0 for k in ("mismatches", "kv_mismatches", "vm_mismatches")))
    rec = {"status": "pass" if ok else "fail", "arm": arm_name, "W_HBM": arm,
           "rtl": obs, "build_command": cmd, "binary_sha256": sha(binary),
           "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in INPUTS},
           "image_sha256": {str(p.relative_to(img)): sha(p) for p in img.rglob("*.hex")},
           "stdout_tail": sim.stdout[-2000:], "stderr_tail": sim.stderr[-2000:]}
    (work / f"arm_{arm_name}.json").write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(arm_name, rec["status"], obs)
    if not ok:
        raise RuntimeError(f"{arm_name} exact gate failed: {sim.stdout[-3000:]}")


def combine(work: Path, output: Path):
    rom, hbm = [json.loads((work / f"arm_{name}.json").read_text()) for name in ("rom", "hbm")]
    assert rom["source_sha256"] == hbm["source_sha256"]
    assert rom["image_sha256"] == hbm["image_sha256"]
    def common_build(cmd):
        clean = []
        omit_next = False
        for item in cmd:
            if omit_next:
                omit_next = False
                continue
            if item == "-Mdir":
                omit_next = True
                continue
            if item.startswith("-GWEIGHT_HBM="):
                continue
            clean.append(item)
        return clean
    assert common_build(rom["build_command"]) == common_build(hbm["build_command"])
    assert all(x["status"] == "pass" for x in (rom, hbm))
    assert rom["rtl"]["generated"] == hbm["rtl"]["generated"]
    data = {"schema": "opentallas.qwen-int8-hbm-matched.v1", "status": "pass",
            "claim_boundary": "Reduced TP-2 scalar signed-INT8 two-die package, same ISA/images/core, matrix code, matrix scales, embedding row and embedding scale supplied by ROM or a PC-local behavioural 32-byte-sector HBM model. Preload is serial per op/token. Not full O4 shape, HBM3E measured bandwidth, controller arbitration with KV, or P&R.",
            "rom_cycles": rom["rtl"]["total_cycles"], "hbm_cycles": hbm["rtl"]["total_cycles"],
            "delta_cycles": hbm["rtl"]["total_cycles"]-rom["rtl"]["total_cycles"],
            "rom": rom["rtl"], "hbm": hbm["rtl"],
            "source_sha256": rom["source_sha256"], "image_sha256": rom["image_sha256"],
            "binary_sha256": {"rom": rom["binary_sha256"], "hbm": hbm["binary_sha256"]}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(output, data["status"], data["delta_cycles"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--arm", choices=("rom", "hbm"))
    ap.add_argument("--combine", action="store_true")
    ap.add_argument("--ngen", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/qwen_int8_hbm_matched.json")
    args = ap.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    if args.combine:
        combine(args.workdir, args.output)
    else:
        if args.arm is None:
            ap.error("--arm is required unless --combine")
        run_arm(args.workdir, 0 if args.arm == "rom" else 1, args.jobs, args.ngen, args.skip_build)
