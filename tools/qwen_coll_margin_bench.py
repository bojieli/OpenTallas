#!/usr/bin/env python3
"""Transaction bench of the MARGIN collective engine (rtl/rom/ot_rom_oneshot_die_m.sv) in the 4-die package model:
the ten unit cases of tools/rtl_hdc_package_tp_campaign.py (all-reduce against tools/hdc_golden.fold, all-gather,
gaps / skew, NaN / Inf / overflow / tag-mismatch fault cases), the same vectors for MARGIN 0 and MARGIN 1.
--mutant builds MARGIN 1 with OT_ONESHOT_M_MUTANT (ranks 1 and 2 swapped in the fold): the exact cases must FAIL.
Prints one line per case and 'COLL_MARGIN PASS cases=N' / 'COLL_MARGIN FAIL ...'; exit 0 iff every case passed."""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_package_tp_campaign as C  # noqa: E402

SRC = [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/hdc/ot_hdc_prefix.sv", ROOT / "rtl/hdc/ot_hdc_fastfp.sv", ROOT / "rtl/hdc/ot_hdc_fp32_add_lat.sv",
       ROOT / "rtl/rom/ot_rom_oneshot_die_m.sv", ROOT / "rtl/rom/ot_coll_fold_slice.sv", ROOT / "rtl/rom/ot_coll_rst_leaf.sv", ROOT / "rtl/rom/ot_coll_col_tile.sv", ROOT / "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v", ROOT / "rtl/lib/ot_hdly.sv", ROOT / "physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v", ROOT / "rtl/rom/ot_rom_oneshot_allreduce.sv",
       ROOT / "rtl/test/tb_rom_oneshot_allreduce.sv"]


PRODUCTION_CASES = [
    # name, depth, msgs, words, gap %, skew, modes, inject, inject value, big  (same tuple as C.UNIT_CASES)
    ("qwen_ar_256w", 32, 1, 256, 0, 0, "r", -1, None, False),
    ("qwen_layer_2x256w", 32, 2, 256, 0, 0, "r", -1, None, False),
    ("qwen_argmax_1w", 32, 1, 1, 0, 0, "g", -1, None, False),
]


def build(scratch: Path, depth: int, margin: int, mutant: bool, mutant_define: str = "OT_ONESHOT_M_MUTANT") -> Path:
    obj = scratch / f"obj_m{margin}_d{depth}{('_' + mutant_define) if mutant else ''}"
    cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD",
           "--top-module", "tb_rom_oneshot_allreduce", f"-GDEPTH={depth}", "-GLAT=12", "-GBPC=3600",
           f"-GMARGIN={margin}", "-Mdir", str(obj)] + ([f"+define+{mutant_define}"] if mutant else []) + \
          [str(s) for s in SRC] + [str(C.unit_harness(scratch)), "-CFLAGS", "-O1", "-j", "8"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"build failed:\n{r.stdout[-3000:]}{r.stderr[-3000:]}")
    return obj / "Vtb_rom_oneshot_allreduce"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--margin", type=int, default=1)
    ap.add_argument("--mutant", action="store_true")
    ap.add_argument("--mutant-define", default="OT_ONESHOT_M_MUTANT",
                    help="negative-control define (OT_ONESHOT_M_OPQ_MUTANT: MARGIN 4 operand queue read one word ahead)")
    ap.add_argument("--production", action="store_true",
                    help="throughput shape (owner 10-10 gate): Qwen3-8B TP4 all-reduce = 256 words of 16-lane FP32, 2 per "
                         "layer, argmax all-gather 1 word, DEPTH 32, no gaps/skew; priced against the engine-alone "
                         "reference in results/arch/qwen_coll_native_20261009/coll_cost.json (AR256 296 / 2x256 552 / argmax 24)")
    ap.add_argument("--depth32", action="store_true",
                    help="run every case at DEPTH 32 (the MEMM / CT production FIFO depth; MARGIN >= 6 datapath is "
                         "only elaborated at DEPTH 32)")
    a = ap.parse_args()
    cases = PRODUCTION_CASES if a.production else C.UNIT_CASES
    if a.depth32:
        cases = [(c[0] + ("" if c[1] == 32 else "_d32"), 32) + tuple(c[2:]) for c in cases]
    a.out.mkdir(parents=True, exist_ok=True)
    exes = {d: build(a.out, d, a.margin, a.mutant, a.mutant_define) for d in sorted({c[1] for c in cases})}
    bad = []
    for i, (name, depth, nmsg, words, gap, skew, mk, inj, ival, big) in enumerate(cases):
        rng = np.random.default_rng(100 + i)
        modes = {"r": [0] * nmsg, "g": [1] * nmsg, "m": list(rng.integers(0, 2, nmsg))}[mk]
        vec = a.out / f"unit_{name}"
        C.unit_vectors(vec, nmsg, words, modes, 1000 + i, big)
        args = [str(exes[depth]), f"+VEC={vec}", f"+NMSG={nmsg}", f"+WORDS={words}", f"+GAP={gap}", f"+SKEW={skew}",
                f"+SEED={7 + i}", f"+INJECT={inj}"] + ([f"+IVAL={ival}"] if ival else []) + \
               (["+TAGBAD=2"] if name == "fault_tag_mismatch" else [])
        txt = subprocess.run(args, capture_output=True, text=True).stdout
        m = C.UNIT.search(txt)
        ok = bool(m) and any(l.strip() == "PASS" for l in txt.splitlines())
        g = m.groups() if m else None
        print(f"case {name} margin={a.margin} mutant={int(a.mutant)} {'PASS' if ok else 'FAIL'} "
              + (f"mismatches={g[8]} words_out={g[12]} cycles={int(g[14]) - int(g[13])}" if g else "no result"))
        if not ok:
            bad.append(name)
    if bad:
        print(f"COLL_MARGIN FAIL margin={a.margin} mutant={int(a.mutant)} failed={','.join(bad)}")
        sys.exit(1)
    print(f"COLL_MARGIN PASS margin={a.margin} cases={len(cases)}")


if __name__ == "__main__":
    main()
