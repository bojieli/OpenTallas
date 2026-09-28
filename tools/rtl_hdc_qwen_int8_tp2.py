#!/usr/bin/env python3
"""Run the reduced two-die signed-INT8 Qwen AR package exact gate."""
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
import hdc_program as P  # noqa: E402
import hdc_qwen_int8_ref as R  # noqa: E402
import rtl_hdc_decode_campaign as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--ngen", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()
    work = args.workdir.resolve()
    img = work / "images"
    expect = R.build(img, args.ngen)
    rtl = [*C.HDC, *C.PIPES,
           *(ROOT / f"rtl/hdc/{x}.sv" for x in ("ot_hdc_qwen_int8_arith", "ot_hdc_qwen_int8_embed_decode",
                                                       "ot_hdc_core_vector_weight")),
           *(ROOT / f"rtl/rom/{x}.sv" for x in ("ot_rom_pkg_link", "ot_rom_pkg_ctrl",
                                                       "ot_rom_oneshot_allreduce", "ot_rom_tp_seq")),
           ROOT / "rtl/test/tb_hdc_package_tp_int8.sv"]
    harness = ROOT / "rtl/test/hdc_package_tp_int8_harness.cpp"
    binary = work / "obj" / "Vtb_hdc_package_tp_int8"
    if not args.skip_build:
        cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH",
               "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD", "--top-module", "tb_hdc_package_tp_int8",
               "-GD=2", "-GNODES=1", "-GUSERS=1", "-GWROM_WORDS=16384", "-Mdir", str(work / "obj"),
               f"-I{C.ISA_SVH.parent}", *map(str, rtl), str(harness), "-CFLAGS", "-O1", "-j", str(args.jobs)]
        cp = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (work / "build.log").write_text(cp.stdout)
        if cp.returncode:
            raise RuntimeError(f"Verilator build failed: {cp.stdout[-4000:]}")
    cp = subprocess.run([str(binary), f"+DIR={img}", f"+NGEN={args.ngen}", "+NUSERS=1"],
                        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (work / "sim.log").write_text(cp.stdout)
    m = re.search(r"PKG_TP nodes=(\d+) dies=(\d+) users=(\d+) generated=(\d+) steps_checked=(\d+) "
                  r"mismatches=(\d+) kv_mismatches=(\d+) vm_mismatches=(\d+) total_cycles=(\d+)", cp.stdout)
    data = dict(zip(("nodes", "dies", "users", "generated", "steps_checked", "mismatches",
                     "kv_mismatches", "vm_mismatches", "total_cycles"), map(int, m.groups()))) if m else {}
    good = cp.returncode == 0 and data.get("generated") == args.ngen and data.get("steps_checked") == 16 + args.ngen - 1 \
        and all(data.get(x) == 0 for x in ("mismatches", "kv_mismatches", "vm_mismatches")) and "PASS" in cp.stdout
    pins = sorted(set([*rtl, harness, Path(__file__), Path(R.__file__), Path(P.__file__),
                       ROOT / "tools/hdc_qwen_int8_image.py", ROOT / "tools/hdc_golden.py",
                       ROOT / "tools/qwen3_deployment_quality.py", ROOT / "rtl/hdc/ot_hdc_isa.svh"]))
    record = {"status": "pass" if good else "fail", "reference": expect, "rtl": data,
              "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in pins},
              "image_sha256": {str(p.relative_to(img)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in img.rglob("*.hex")},
              "claim_boundary": "Reduced unfolded-norm two-die INT8 AR package with scalar stream and behavioural ROM; not full O4 throughput or P&R."}
    (work / "result.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": record["status"], "rtl": data, "workdir": str(work)}, indent=2))
    if not good:
        print(cp.stdout[-4000:])
        sys.exit(1)


if __name__ == "__main__":
    main()
