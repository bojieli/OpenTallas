#!/usr/bin/env python3
"""Exactness gate of the hardened V4.1 QE ROM/MAC neighborhood (ot_chip_v41x_qe_romac).

Loads the 16 source-pinned QE local-tile checkpoint bank images
(results/rtl/v41x_qe_local_tile_bank_l0.json) into the DUT's behavioural
ot_rom_8192x274_m8 via masks and into the reference's ideal bank array, then runs
wq_a (FP8), exp110.w1 (paired FP4) and wq_a again through both the DUT (RL = 2,
per-macro capture, activation SRAMs, spine-edge pipes) and the reference
(routed qtile RL = 2 + ot_chip_v41x_qtile_pair_bank).  Every result must match.
Activations are deterministic pseudo-random finite E4M3 blocks (seeded).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/v41x_qe_local_tile_bank_l0.json"
RTL = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_bdot.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_red.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_tops.sv",
    "rtl/chip/ot_chip_v41x_qtile_pair_bank.sv",
    "physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v",
    "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
    "rtl/chip/physical/ot_chip_v41x_qe_romac.sv")]
TB = ROOT / "rtl/test/tb_chip_v41x_qe_romac.sv"
OUT = ROOT / "results/physical_abi3/asap7/chip/v41_w2_rommac/qe_romac_exactness.json"
SEED = 20260929
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def viamap(words: list[int], path: Path) -> None:
    """Word a, bit b -> physical row a // 8, column b * 8 + a % 8 (the model's word_read)."""
    rows = [0] * 1024
    for a, w in enumerate(words):
        r, s = divmod(a, 8)
        v = rows[r]
        b = 0
        while w:
            if w & 1:
                v |= 1 << (b * 8 + s)
            w >>= 1
            b += 1
        rows[r] = v
    with path.open("w") as out:
        for v in rows:
            out.write(f"{v:0548x}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tile-images", type=Path, required=True)
    ap.add_argument("--no-record", action="store_true")
    args = ap.parse_args()
    local = json.loads(RECORD.read_text())
    if local["macro_type"] != "ot_rom_8192x274_m8" or len(local["macros"]) != 16:
        raise ValueError("unexpected local qtile bank manifest")
    with tempfile.TemporaryDirectory(prefix="v41qer_") as td:
        work = Path(td)
        with (work / "banks.hex").open("w") as out:
            for m in local["macros"]:
                p = args.tile_images / m["image_file"]
                if digest(p) != m["image_sha256"]:
                    raise ValueError(f"stale macro image {p}")
                raw = np.frombuffer(p.read_bytes(), dtype=np.uint8).reshape(8192, 35)
                words = []
                for row in raw:
                    v = int.from_bytes(row.tobytes(), "little")
                    if v >> 274:
                        raise ValueError("nonzero macro image padding")
                    words.append(v)
                    out.write(f"{v:069x}\n")
                viamap(words, work / f"via{m['macro_id']:02d}.hex")
        rng = np.random.default_rng(SEED)
        with (work / "act.hex").open("w") as out:
            for _ in range(160):
                codes = rng.integers(0, 256, size=32, dtype=np.int64)
                codes[(codes & 0x7F) == 0x7F] ^= 1          # no E4M3 NaN
                xe = int(rng.integers(124, 131))
                v = xe << 256
                for i, cb in enumerate(codes):
                    v |= int(cb) << (8 * i)
                out.write(f"{v:066x}\n")
        obj = work / "obj"
        comp = subprocess.run([str(VERILATOR), "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH",
                               "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD", "--top-module",
                               "tb_chip_v41x_qe_romac", "-Mdir", str(obj), *map(str, RTL), str(TB),
                               "-CFLAGS", "-O1", "-j", "16"], cwd=ROOT, capture_output=True, text=True, timeout=3600)
        if comp.returncode:
            raise RuntimeError("compile failed:\n" + comp.stderr[-3000:])
        run = subprocess.run([str(obj / "Vtb_chip_v41x_qe_romac"), f"+DIR={work}"], cwd=ROOT, capture_output=True,
                             text=True, timeout=6 * 3600)
        print(run.stdout[-3000:])
        m = re.search(r"QE_ROMAC_PASS rows=(\d+) faults=(\d+)", run.stdout)
        if run.returncode or not m:
            raise RuntimeError("simulation failed:\n" + run.stdout[-3000:] + run.stderr[-800:])
        lat = [dict(zip(("op", "fp4", "dut_accept", "dut_first", "ref_accept", "ref_first"), map(int, g)))
               for g in re.findall(r"QE_ROMAC_LAT op=(\d+) fp4=(\d+) dut_accept=(-?\d+) dut_first=(-?\d+) "
                                   r"ref_accept=(-?\d+) ref_first=(-?\d+)", run.stdout)]
        end = re.search(r"QE_ROMAC_END dut_last=(\d+) ref_last=(\d+)", run.stdout)
    for x in lat:
        x["dut_accept_to_first_result"] = x["dut_first"] - x["dut_accept"]
        x["ref_accept_to_first_result"] = x["ref_first"] - x["ref_accept"]
    record = {
        "schema": "opentallas.rtl.v41x_qe_romac_exactness.v1", "status": "pass",
        "claim_scope": ("Hardening candidate ot_chip_v41x_qe_romac (RL=2 kept: unconditional per-macro capture feeding the lane P0 register, "
                        "per-tag format, activation SRAMs, NP=2 spine pipes) produces every result of three "
                        "back-to-back checkpoint ops (wq_a FP8, exp110.w1 paired FP4, wq_a) bit-identical and in "
                        "order to the routed qtile RL=2 + pinned pair bank over the same bank images. "
                        "Activations are seeded synthetic finite E4M3 blocks, not checkpoint activations."),
        "rows": int(m.group(1)), "fault_rows": int(m.group(2)), "activation_seed": SEED,
        "latency_cycles": lat,
        "latency_note": ("dut_accept is the spine-edge handshake (NP=2 input stages + 1 queue cycle) and DUT "
                         "results are counted after NP=2 output stages: +5 cycles, all spine-edge registers. The "
                         "tile-internal read latency is unchanged (RL=2): the macro-side capture replaces the pair "
                         "bank's rd_w register, the lane's P0 register takes the combinational lane select."),
        "last_result_cycle": {"dut": int(end.group(1)), "ref_with_format_drains": int(end.group(2))},
        "simulator": subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip(),
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in [*RTL, TB, RECORD, Path(__file__)]},
    }
    if not args.no_record:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record["latency_cycles"], indent=1))


if __name__ == "__main__":
    main()
