#!/usr/bin/env python3
"""Transaction bench of the MARGIN collective engine (rtl/rom/ot_rom_oneshot_die_cx.sv) in the 4-die package model:
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
       ROOT / "rtl/rom/ot_rom_oneshot_die_cx.sv", ROOT / "rtl/rom/ot_rom_oneshot_allreduce_cx.sv",
       ROOT / "rtl/test/tb_rom_oneshot_allreduce.sv"]


def build(scratch: Path, depth: int, margin: int, mutant: bool) -> Path:
    obj = scratch / f"obj_m{margin}_d{depth}{'_mut' if mutant else ''}"
    cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD",
           "--top-module", "tb_rom_oneshot_allreduce", f"-GDEPTH={depth}", "-GLAT=12", "-GBPC=3600",
           f"-GMARGIN={margin}", "-Mdir", str(obj)] + (["+define+OT_ONESHOT_M_MUTANT"] if mutant else []) + \
          [str(s) for s in SRC] + [str(C.unit_harness(scratch)), "-CFLAGS", "-O1", "-j", "8"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"build failed:\n{r.stdout[-3000:]}{r.stderr[-3000:]}")
    return obj / "Vtb_rom_oneshot_allreduce"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--margin", type=int, default=3)
    ap.add_argument("--mutant", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    exes = {d: build(a.out, d, a.margin, a.mutant) for d in sorted({c[1] for c in C.UNIT_CASES})}
    bad = []
    for i, (name, depth, nmsg, words, gap, skew, mk, inj, ival, big) in enumerate(C.UNIT_CASES):
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
    print(f"COLL_MARGIN PASS margin={a.margin} cases={len(C.UNIT_CASES)}")


if __name__ == "__main__":
    main()
