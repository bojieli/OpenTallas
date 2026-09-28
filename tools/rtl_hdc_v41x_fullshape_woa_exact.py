#!/usr/bin/env python3
"""Checkpoint-backed TP4 layer-0 grouped wo_a ME exact gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RTL = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/v41/ot_hdc_actquant.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_bdot.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_red.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_me_xbank.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_me_xbank_macro.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_fp32_bf16_preload64.sv",
    "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
    "rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv",
    "rtl/test/tb_hdc_v41x_fullshape_woa_exact.sv")]
PAT = re.compile(r"WOA_PASS rows_per_group=(\d+) exact_rows=(\d+) bank_reads=(\d+) cycles=(\d+)")
PRE_PAT = re.compile(r"PRELOAD_PASS issue_cycles=(\d+) write_cycles=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cap_memory() -> None:
    limit = 24 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def bits(path: Path, n: int) -> np.ndarray:
    if path.suffix == ".bin":
        array = np.fromfile(path, dtype="<u4")
    else:
        array = np.load(path, allow_pickle=False)
    if array.size != n or array.dtype not in (np.dtype("float32"), np.dtype("uint32")):
        raise ValueError(f"{path} must contain {n} float32/uint32 values")
    return np.ascontiguousarray(array.reshape(-1)).view(np.uint32)


def run(acc: Path, za: Path, image: Path, golden_manifest: Path,
        layout_manifest: Path, rows: int, output: Path, banked: bool = False,
        macro: bool = False, rl: int = 2, shared: bool = False,
        preloaded: bool = False, input_registered: bool = False) -> dict:
    if rl not in (2, 3, 4):
        raise ValueError('rl must be 2, 3 or 4')
    if shared and rl not in (3, 4):
        raise ValueError('shared store requires rl=3 or 4')
    if preloaded and (not shared or rl not in (3, 4)):
        raise ValueError('preloaded mode requires shared store and rl=3 or 4')
    if input_registered and (not preloaded or rl != 4):
        raise ValueError('input-registered store requires preloaded rl=4')
    if rows < 16 or rows > 1024 or rows % 16:
        raise ValueError("rows must be a multiple of 16 in 16..1024")
    if image.stat().st_size != 33_554_432:
        raise ValueError("wo_a ME image must contain exactly 131072 x 64 FP32 bank words")
    golden = json.loads(golden_manifest.read_text())
    layout = json.loads(layout_manifest.read_text())
    if (golden.get("schema") != "opentallas.rtl.v41_fullshape_wo_a_vectors.v1"
            or golden.get("rank_groups") != [0, 1]
            or golden.get("context") != 200000 or golden.get("layer") != 0):
        raise ValueError("wrong checkpoint golden manifest")
    if sha(acc) != golden["acc"]["sha256"] or sha(za) != golden["za"]["sha256"]:
        raise ValueError("checkpoint ACC/ZA binary hash mismatch")
    matrix = layout["matrices"]["wo_a"]
    if (matrix["source_weight_sha256"] != golden["weight_image_wo_a_sha256"]
            or matrix["source_scale_sha256"] != golden["weight_image_wo_a_scale_sha256"]
            or matrix["output_image_sha256"] != sha(image)
            or matrix["base_word"] != 7680 or matrix["word_count"] != 131072):
        raise ValueError("packed ME image does not bind to checkpoint wo_a")
    acc_bits, za_bits = bits(acc, 8192), bits(za, 2048)
    with tempfile.TemporaryDirectory(prefix="v41_woa_exact_") as tmp:
        tmp = Path(tmp)
        (tmp / "acc.hex").write_text("".join(f"{int(v):08x}\n" for v in acc_bits))
        (tmp / "za.hex").write_text("".join(f"{int(v):08x}\n" for v in za_bits))
        os.symlink(image.resolve(), tmp / "wo_a.me.bin")
        obj = tmp / "obj"
        verilator = str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator")
        sources = list(RTL)
        if input_registered:
            sources.insert(-2, ROOT / "rtl/hdc/v41x/ot_hdc_v41x_me_xbank_macro_inreg.sv")
        command = [verilator, "--binary", "--timing", "-O0", "-Wno-fatal", "-Wno-WIDTH",
                   "-Wno-UNUSED", "-Wno-TIMESCALEMOD", "--top-module",
                   "tb_hdc_v41x_fullshape_woa_exact", *([f"-GXBANK={2 if macro else 1}"] if banked or macro else []),
                   f"-GRL={rl}", *([f"-GSHARED={3 if input_registered else (2 if preloaded else 1)}"] if shared else []), "-Mdir", str(obj),
                   *map(str, sources), "-CFLAGS", "-O0", "-j", "4"]
        t0 = time.monotonic()
        build = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                               timeout=600, preexec_fn=cap_memory)
        if build.returncode:
            raise RuntimeError("ME bench build failed:\n" + build.stderr[-3000:])
        build_sec = round(time.monotonic() - t0, 2)
        t1 = time.monotonic()
        sim = subprocess.run([str(obj / "Vtb_hdc_v41x_fullshape_woa_exact"),
                              f"+DIR={tmp}", f"+ROWS={rows}"], cwd=ROOT,
                             capture_output=True, text=True, timeout=3600,
                             preexec_fn=cap_memory)
        match = PAT.search(sim.stdout)
        if sim.returncode or not match:
            raise RuntimeError("ME bench failed:\n" + sim.stdout[-3000:] + sim.stderr[-2000:])
        checked_rows, exact, reads, cycles = map(int, match.groups())
        pre_match = PRE_PAT.search(sim.stdout)
        if preloaded and (not pre_match or tuple(map(int,pre_match.groups())) != (128,128)):
            raise RuntimeError('preload coverage mismatch: '+sim.stdout[-1000:])
        if checked_rows != rows or exact != rows * 2 or reads < rows * 128:
            raise RuntimeError("ME bench coverage mismatch: " + match.group(0))
        sim_sec = round(time.monotonic() - t1, 2)
        fixture_sha = {str(p): sha(p) for p in
                       (acc, za, image, golden_manifest, layout_manifest)}
        source_sha = {str(p.relative_to(ROOT)): sha(p) for p in (*sources, Path(__file__))}
        record = {
            "schema": "opentallas.rtl.v41x_fullshape_woa_exact.v1",
            "status": "pass",
            "banked_activation_store": banked,
            "macro_activation_store": macro,
            "claim_scope": f"TP4 rank-0 layer-0 wo_a groups 0 and 1, first {rows} of 1024 rows "
                           "per group, bit-exact raw FP32 ME outputs against checkpoint golden. "
                           "No full-layer or chip-throughput claim.",
            "rows_per_group": rows, "exact_rows": exact, "bank_read_cycles": reads,
            "simulation_cycles": cycles, "build_seconds": build_sec,
            "read_latency_cycles": rl,
            "external_shared_store": shared,
            "preloaded_activation": preloaded,
            "input_registered_activation_store": input_registered,
            "vm_bank_rotation_quarters": 2 if preloaded else 0,
            "preload_issue_cycles": int(pre_match.group(1)) if pre_match else 0,
            "preload_write_cycles": int(pre_match.group(2)) if pre_match else 0,
            "simulation_seconds": sim_sec, "memory_cap_bytes": 24 * 1024**3,
            "descriptor": {"g0": {"weight_base_word": 7680, "xbase": 0, "output_base_word": 0},
                           "g1": {"weight_base_word": 73216, "xbase": 4096, "output_base_word": 64},
                           "k": 4096, "rows_per_full_group": 1024, "splitj": False},
            "fixture_sha256": fixture_sha, "source_sha256": source_sha,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n")
    return record


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--acc", type=Path, required=True)
    ap.add_argument("--za", type=Path, required=True)
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--golden-manifest", type=Path, required=True)
    ap.add_argument("--layout-manifest", type=Path, required=True)
    ap.add_argument("--rows", type=int, default=16)
    ap.add_argument("--banked", action="store_true")
    ap.add_argument("--macro", action="store_true")
    ap.add_argument("--rl", type=int, choices=(2, 3), default=2)
    ap.add_argument("--shared", action="store_true")
    ap.add_argument("--preloaded", action="store_true")
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/hdc_v41x_fullshape_woa_exact.json")
    args = ap.parse_args()
    print(json.dumps(run(args.acc, args.za, args.image, args.golden_manifest,
                         args.layout_manifest, args.rows, args.output, args.banked, args.macro,
                         args.rl, args.shared, args.preloaded), indent=2))


if __name__ == "__main__":
    main()
