#!/usr/bin/env python3
"""Build and compare shipped-shape Qwen layer-0 TP2 RTL against ISA oracle."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_decode_campaign as C  # noqa: E402

RTL = [
    *C.HDC, *C.PIPES,
    *(ROOT / f"rtl/hdc/{name}.sv" for name in (
        "ot_hdc_dyn_ttiles", "ot_hdc_qwen_int8_arith",
        "ot_hdc_qwen_int8_embed_decode", "ot_hdc_core_vector_weight")),
    *(ROOT / f"rtl/rom/{name}.sv" for name in (
        "ot_rom_pkg_link", "ot_rom_pkg_ctrl", "ot_rom_oneshot_allreduce", "ot_rom_tp_seq")),
    ROOT / "rtl/test/tb_hdc_qwen_layer0_tp2.sv",
]
HARNESS = ROOT / "rtl/test/hdc_qwen_layer0_tp2_harness.cpp"
SOURCES = sorted(set([*RTL, HARNESS, Path(__file__), C.ISA_SVH,
                      *(ROOT / f"tools/{name}.py" for name in (
                          "hdc_qwen_layer0_rom", "hdc_qwen_fullshape_program",
                          "hdc_qwen_fullshape_placement", "hdc_qwen_fullshape_isa",
                          "hdc_qwen_int8_image", "hdc_program", "qwen_o4_layer0_oracle"))]))
GOLD = ROOT / "results/rtl/qwen_o4_layer0_oracle"
VECTORS = ("x_final", "t1_after_o_scale", "t1_after_down_scale", "k_pos0", "v_pos0")
IMAGE_FILES = ("program.hex", "segments.hex", "matrix_int8.hex", "matrix_scale_bf16.hex", "crom.hex")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vector(path: Path) -> list[int]:
    return [int(line, 16) for line in path.read_text().splitlines() if line and not line.startswith("@")]


def prepare(work: Path, emitter_prefix: Path, preload: Path, oracle: dict) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    pins = {}
    for die in range(2):
        d = work / f"die{die}"
        d.mkdir(exist_ok=True)
        for name in IMAGE_FILES:
            target = Path(f"{emitter_prefix}-d{die}") / name
            expected = oracle["input_image_sha256"][f"die{die}"][name]
            actual = sha(target)
            if actual != expected:
                raise ValueError(f"oracle input mismatch: die{die}/{name}")
            link = d / name
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(target)
            pins[f"die{die}/{name}"] = actual
    target = preload / "vm_x_fp32.hex"
    if sha(target) != oracle["x_preload_sha256"]:
        raise ValueError("oracle X preload mismatch")
    link = work / "vm_x_fp32.hex"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target)
    pins["vm_x_fp32.hex"] = sha(target)
    return pins


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--emitter-prefix", type=Path, default=Path("/tmp/qwen-real-layer0"))
    ap.add_argument("--preload-dir", type=Path, default=Path("/tmp/qwen-vocab-embed-token0"))
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()
    work = args.workdir.resolve()
    oracle_path = GOLD / "oracle.json"
    oracle = json.loads(oracle_path.read_text())
    image_pins = prepare(work, args.emitter_prefix, args.preload_dir, oracle)
    source_pins = {str(path.relative_to(ROOT)): sha(path) for path in SOURCES}
    (work / "start_pins.json").write_text(json.dumps(source_pins, indent=2, sort_keys=True) + "\n")
    binary = work / "obj" / "Vtb_hdc_qwen_layer0_tp2"
    if not args.skip_build:
        cmd = ["verilator", "--cc", "--exe", "--build", "-O1",
               "--unroll-count", "131072", "-Wno-fatal", "-Wno-WIDTH",
               "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD", "-Wno-PINMISSING",
               "--top-module", "tb_hdc_qwen_layer0_tp2", "-GG=6144", "-Mdir", str(work / "obj"),
               f"-I{C.ISA_SVH.parent}", *map(str, RTL), str(HARNESS),
               "-CFLAGS", "-O0", "-j", str(args.jobs)]
        cp = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (work / "build.log").write_text(cp.stdout)
        if cp.returncode:
            raise RuntimeError(f"Verilator build failed: {cp.stdout[-4000:]}")
    cp = subprocess.run([str(binary), f"+DIR={work}"], cwd=ROOT,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (work / "sim.log").write_text(cp.stdout)
    match = re.search(r"QWEN_LAYER0_TP2 PASS dies=2 token=0 pos=0 cycles=(\d+) ", cp.stdout)
    checks = {}
    for die in range(2):
        for name in VECTORS:
            got = vector(work / f"die{die}" / f"{name}.hex") if (work / f"die{die}" / f"{name}.hex").exists() else []
            want = vector(GOLD / f"die{die}_{name}.hex")
            first = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), None)
            mismatches = sum(a != b for a, b in zip(got, want)) + abs(len(got) - len(want))
            checks[f"die{die}_{name}"] = {"expected_words": len(want), "actual_words": len(got),
                                          "mismatches": mismatches, "first_mismatch": first,
                                          "actual_sha256": sha(work / f"die{die}" / f"{name}.hex") if got else None,
                                          "expected_sha256": sha(GOLD / f"die{die}_{name}.hex")}
    current_pins = {str(path.relative_to(ROOT)): sha(path) for path in SOURCES}
    source_stable = current_pins == source_pins
    image_stable = all(sha(work / path) == digest for path, digest in image_pins.items())
    good = cp.returncode == 0 and bool(match) and source_stable and image_stable and \
        all(x["mismatches"] == 0 for x in checks.values())
    result = {"schema": "opentallas.qwen-layer0-tp2-rtl.v1", "status": "pass" if good else "fail",
              "rtl_cycles": int(match.group(1)) if match else None,
              "source_sha256": source_pins, "source_stable": source_stable,
              "image_sha256": image_pins, "image_stable": image_stable,
              "oracle_sha256": sha(oracle_path), "checks": checks,
              "binary_sha256": sha(binary) if binary.exists() else None,
              "claim_boundary": "Real Qwen3-8B layer0 token0/pos0 TP2 RTL versus an independently checked ISA oracle; "
                                "behavioural memories, no full token, physical timing, or P&R."}
    (work / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "rtl_cycles": result["rtl_cycles"],
                      "mismatch_counts": {k: v["mismatches"] for k, v in checks.items()}}, indent=2))
    if not good:
        print(cp.stdout[-4000:])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
