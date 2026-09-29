#!/usr/bin/env python3
"""Exactness gate of the hardened V4.1 ME ROM/MAC neighborhood (ot_chip_v41x_me_romac).

Seeded synthetic operand words (fmt 0 BF16 weights and fmt 1 FP8 E4M3 + UE8M0 weights mixed per lane,
BF16 activations) are loaded into the DUT's behavioural ot_rom_8192x274_m8 via masks / MP1 SRAMs and
into the reference's ideal RL = 2 arrays; three back-to-back ops of different segment widths
(plg 3, 1, 2) must give identical results in order.  Not checkpoint data: the ME bank-to-checkpoint
map is a separate (W1) gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.rtl_v41x_qe_romac import viamap, VERILATOR  # noqa: E402

RTL = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_bdot.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_red.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_tops.sv",
    "physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v",
    "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
    "rtl/chip/physical/ot_chip_v41x_me_romac.sv")]
TB = ROOT / "rtl/test/tb_chip_v41x_me_romac.sv"
OUT = ROOT / "results/physical_abi3/asap7/chip/v41_w2_rommac/me_romac_exactness.json"
SEED = 20260930


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bf16(rng) -> int:
    return (int(rng.integers(0, 2)) << 15) | (int(rng.integers(118, 136)) << 7) | int(rng.integers(0, 128))


def lane_word(rng) -> int:
    if rng.integers(0, 2):
        code = int(rng.integers(0, 256))
        if code & 0x7F == 0x7F:
            code ^= 1
        return (1 << 32) | (int(rng.integers(120, 135)) << 8) | code
    return bf16(rng) << 16


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-record", action="store_true")
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)
    with tempfile.TemporaryDirectory(prefix="v41mer_") as td:
        work = Path(td)
        words = [[0] * 8192 for _ in range(8)]
        with (work / "wmem.hex").open("w") as out:
            for c in range(8):
                for a in range(2048):
                    v = 0
                    for u in range(8):
                        v |= lane_word(rng) << (34 * u)
                    words[c][a] = v
                    out.write(f"{v:069x}\n")
        for c in range(8):
            viamap(words[c], work / f"via{c}.hex")
        with (work / "xmem.hex").open("w") as out:
            for _ in range(8 * 128):
                v = 0
                for u in range(8):
                    v |= bf16(rng) << (16 * u)
                out.write(f"{v:032x}\n")
        obj = work / "obj"
        comp = subprocess.run([str(VERILATOR), "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH",
                               "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD", "--top-module",
                               "tb_chip_v41x_me_romac", "-Mdir", str(obj), *map(str, RTL), str(TB),
                               "-CFLAGS", "-O1", "-j", "16"], cwd=ROOT, capture_output=True, text=True, timeout=3600)
        if comp.returncode:
            raise RuntimeError("compile failed:\n" + comp.stderr[-3000:])
        run = subprocess.run([str(obj / "Vtb_chip_v41x_me_romac"), f"+DIR={work}"], cwd=ROOT, capture_output=True,
                             text=True, timeout=6 * 3600)
        print(run.stdout[-2000:])
        m = re.search(r"ME_ROMAC_PASS results=(\d+) fault_results=(\d+)", run.stdout)
        if run.returncode or not m:
            raise RuntimeError("simulation failed:\n" + run.stdout[-3000:] + run.stderr[-800:])
        lat = dict(zip(("dut_accept", "dut_first", "ref_accept", "ref_first", "dut_last", "ref_last"),
                       map(int, re.search(r"ME_ROMAC_LAT dut_accept=(\d+) dut_first=(\d+) ref_accept=(\d+) "
                                          r"ref_first=(\d+) dut_last=(\d+) ref_last=(\d+)", run.stdout).groups())))
    lat["dut_accept_to_first"] = lat["dut_first"] - lat["dut_accept"]
    lat["ref_accept_to_first"] = lat["ref_first"] - lat["ref_accept"]
    record = {
        "schema": "opentallas.rtl.v41x_me_romac_exactness.v1", "status": "pass",
        "claim_scope": ("ot_chip_v41x_me_romac (macro-side capture of 8 ot_rom_8192x274_m8 and 8 MP1 activation "
                        "macros, combinational lane words into the ME lane P0, NP=2 spine pipes) gives every result "
                        "of three back-to-back ops (plg 3/1/2) identical and in order to the mtile over ideal RL=2 "
                        "arrays. Seeded synthetic mixed BF16/FP8 weights and BF16 activations, not checkpoint data."),
        "results": int(m.group(1)), "fault_results": int(m.group(2)), "seed": SEED, "latency_cycles": lat,
        "latency_note": "+5 cycles are the spine-edge registers (2 in + 1 queue + 2 out); tile RL=2 unchanged.",
        "simulator": subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip(),
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in [*RTL, TB, Path(__file__),
                                                                         ROOT / "tools/rtl_v41x_qe_romac.py"]},
    }
    if not args.no_record:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(lat))


if __name__ == "__main__":
    main()
