#!/usr/bin/env python3
"""Lint and run a reduced adopted-core SU/all-reduce/SU RTL integration stage."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_decode_campaign as core
from rtl_v41x_real_core_stage_images import build as build_images

TOP = "tb_v41x_real_core_collective"
TB = ROOT / "rtl/test/tb_v41x_real_core_collective.sv"
LINK = ROOT / "rtl/test/tb_v41_stage_collective.sv"
ENGINE = ROOT / "rtl/rom/ot_rom_oneshot_allreduce.sv"
DRIVER = ROOT / "rtl/test/hdc_v41x_real_core_collective_harness.cpp"
FLAGS = ["-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
         "-Wno-MULTIDRIVEN", "-Wno-PINMISSING", "-Wno-MODDUP", "-Wno-UNOPTFLAT",
         "-Wno-TIMESCALEMOD"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], log: Path) -> None:
    with log.open("w") as fh:
        p = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    if p.returncode:
        raise RuntimeError(f"{cmd[0]} failed ({p.returncode}): {log.read_text()[-3000:]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--lint-only", action="store_true")
    ap.add_argument("--lat", type=int, default=142)
    ap.add_argument("--fp", choices=("rtl", "dpi"), default="dpi")
    ap.add_argument("--replay-binary", type=Path,
                    help="reuse an already pinned executable built from the same RTL and testbench")
    ap.add_argument("--replay-origin", type=Path,
                    help="original build result, required with --replay-binary")
    args = ap.parse_args()
    if bool(args.replay_binary) != bool(args.replay_origin):
        ap.error("--replay-binary and --replay-origin must be given together")
    scratch = args.scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    core.PARAMS["fp"] = args.fp
    src = [core.VLT, *core.rtl_sources(True), ENGINE, LINK, TB, DRIVER,
           ROOT / "rtl/hdc/v41/ot_hdc_isa_v41.svh",
           ROOT / "tools/hdc_isa_v41.py",
           ROOT / "tools/rtl_hdc_v41x_decode_campaign.py",
           ROOT / "tools/rtl_v41x_real_core_stage_images.py", Path(__file__)]
    manifest = {str(p.relative_to(ROOT)): sha(p) for p in src}
    (scratch / "source_sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    rtl = [str(p) for p in core.rtl_sources(True) if p.suffix == ".sv"]
    defines = ["+define+HDC_SW=8", "+define+HDC_HHW=8", "+define+HDC_MG=8",
               "+define+HDC_SUN=16", "+define+HDC_SUM=8"]
    lint = ["verilator", "--lint-only", *FLAGS, "--top-module", TOP,
            f"-I{ROOT / 'rtl/hdc/v41'}", *defines, str(core.VLT), *rtl,
            str(ENGINE), str(LINK), str(TB)]
    run(lint, scratch / "lint.log")
    if args.lint_only:
        print(json.dumps({"status": "lint_pass", "source_sha256": sha(scratch / "source_sha256.json")}))
        return
    images = scratch / "images"
    image_manifest = build_images(images)
    obj = scratch / "obj"
    obj.mkdir(exist_ok=True)
    build = ["verilator", "--cc", "--exe", "--build", "-O2", *FLAGS,
             "--top-module", TOP, f"-GLAT_X={args.lat}", "-Mdir", str(obj),
             f"-I{ROOT / 'rtl/hdc/v41'}", *defines, str(core.VLT),
             *[str(p) for p in core.rtl_sources(True)], str(ENGINE), str(LINK),
             str(TB), str(DRIVER), "-CFLAGS", "-O1", "-j", "16"]
    if args.replay_binary is None:
        run(build, scratch / "build.log")
        exe = obj / f"V{TOP}"
    else:
        exe = args.replay_binary.resolve()
        origin = json.loads(args.replay_origin.read_text())
        if origin["lat_cycles"] != args.lat or origin["binary_sha256"] != sha(exe):
            raise RuntimeError("replay executable or link latency differs from original build")
        generated = {"tools/rtl_v41x_real_core_stage_campaign.py",
                     "tools/rtl_v41x_real_core_stage_images.py"}
        for name, digest in origin["source_sha256"].items():
            if name not in generated and manifest[name] != digest:
                raise RuntimeError(f"replay RTL/build source changed: {name}")
        build = None
    sim = [str(exe), f"+VEC={images}"]
    run(sim, scratch / "sim.log")
    log = (scratch / "sim.log").read_text()
    pins = {"status": "pass" if "REAL_STAGE PASS" in log else "fail",
            "lat_cycles": args.lat, "fp_simulation": args.fp,
            "source_sha256": manifest, "image_sha256": image_manifest["files"],
            "binary_sha256": sha(exe), "sim_log_sha256": sha(scratch / "sim.log"),
            "build_command": build, "replay_binary": str(exe) if args.replay_binary else None,
            "replay_origin_sha256": sha(args.replay_origin) if args.replay_origin else None,
            "sim_command": sim}
    (scratch / "result.json").write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": pins["status"], "result": str(scratch / "result.json")}))
    if pins["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
