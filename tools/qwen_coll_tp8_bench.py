#!/usr/bin/env python3
"""qwen-tp8 (2026-10-12) bit-exact bench of the TP8 collective cluster rtl/rom/ot_coll_tp8_die.sv in the 8-die model
rtl/test/tb_coll_tp8.sv (4 packages x 2 dies; UCIe pair links of --latu cycles, SerDes links of --lats cycles).
Golden: the two-level fold of results/arch/qwen_tp8_1012/SPEC.md section 3 with tools/hdc_golden.add / fold:
  Pp = part(p, die 0) + part(p, die 1);  sum = ((P0 + P1) + P2) + P3;
all-gather (LM-head argmax (max, index) words): output word k = TP8 rank k mod 8 (= 4 * die + package), index k / 8.
Cases: unit (gaps, skew, mixed modes, argmax 1-word gather, NaN / Inf / overflow / tag-mismatch fault cases) plus the
Qwen3-8B production shape (4,096 FP32 = 256 words of 16 lanes, 2 all-reduces per layer, 1-word argmax gather).
--mutant-define D builds with a negative control (OT_TP8_MUT_OWNER, OT_TP8_MUT_GATHER, OT_ONESHOT_M_MUTANT): some
case must FAIL.  Prints one line per case and 'COLL_TP8 PASS cases=N' / 'COLL_TP8 FAIL ...'; exit 0 iff all pass."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402

ND, LANES = 8, 16


def rand_f32(rng, n):
    """Binary32 values with spread exponents, zeros, subnormals and signs (tools/rtl_hdc_package_tp_campaign.py)."""
    e = rng.integers(90, 160, n)
    e[rng.random(n) < 0.03] = 0                    # subnormal
    m = rng.integers(0, 1 << 23, n)
    s = rng.integers(0, 2, n)
    b = (s << 31) | (e << 23) | m
    b[rng.random(n) < 0.02] = 0
    return b.astype(np.uint32)
SRC = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
    "rtl/rom/ot_rom_oneshot_die_m.sv", "rtl/rom/ot_coll_fold_slice.sv", "rtl/rom/ot_coll_rst_leaf.sv", "rtl/rom/ot_coll_col_tile.sv", "rtl/rom/ot_coll_col_tile_d64.sv", "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v", "rtl/lib/ot_hdly.sv",
    "physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v",
    "rtl/physical/ot_qfd_io_collective.sv", "rtl/rom/ot_rom_oneshot_allreduce.sv", "rtl/rom/ot_coll_tp8_die.sv", "rtl/rom/ot_coll_tp8_col_tile.sv",
    "rtl/rom/ot_coll_tp8_col_tile_r.sv", "rtl/rom/ot_coll_tp8_col3.sv", "rtl/rom/ot_coll_link_end.sv", "rtl/test/tb_coll_tp8.sv")]
RES = re.compile(r"TP8COLL dies=8 latu=(\d+) lats=(\d+) msgs=(\d+) words=(\d+) gap=(\d+) skew=(\d+) inject=(-?\d+) "
                 r"mismatches=(\d+) out_err=(\d+) fault=(\d+) code=(\d+) words_out=(\d+) first=(-?\d+) last=(\d+)")

UNIT_CASES = [
    # name, msgs, words, gap %, skew, modes ('r' reduce / 'g' gather / 'm' mixed), inject, inject value, big, tagbad
    ("reduce_8w", 64, 8, 0, 0, "r", -1, None, False, -1),
    ("reduce_8w_gaps_skew", 64, 8, 30, 7, "r", -1, None, False, -1),
    ("mixed_gather_gaps_skew", 64, 8, 30, 3, "m", -1, None, False, -1),
    ("argmax_gather_1w_gaps_skew", 64, 1, 10, 5, "g", -1, None, False, -1),
    ("reduce_2w", 32, 2, 20, 2, "r", -1, None, False, -1),
    ("fault_nan", 4, 8, 0, 0, "r", 1, "7fc00000", False, -1),
    ("fault_inf", 4, 8, 0, 0, "r", 2, "ff800000", False, -1),
    ("fault_overflow", 4, 8, 0, 0, "r", 0, "7f000000", True, -1),
    ("fault_tag_mismatch", 4, 8, 0, 0, "r", -1, None, False, 2),
]
PRODUCTION_CASES = [
    ("qwen_ar_256w", 1, 256, 0, 0, "r", -1, None, False, -1),
    ("qwen_layer_2x256w", 2, 256, 0, 0, "r", -1, None, False, -1),
    ("qwen_argmax_1w", 1, 1, 0, 0, "g", -1, None, False, -1),
]


def vectors(path: Path, nmsg, words, modes, seed, big=False):
    rng = np.random.default_rng(seed)
    part = rand_f32(rng, nmsg * ND * words * LANES).reshape(nmsg, ND, words, LANES)   # die r = 2 * package + die
    # cancellations: in-package (die 1 = -die 0) and cross-package (package 1 die d = -package 0 die d)
    c1 = rng.random((nmsg, words, LANES)) < 0.1
    part[:, 1][c1] = part[:, 0][c1] ^ np.uint32(0x80000000)
    c2 = rng.random((nmsg, words, LANES)) < 0.1
    part[:, 2][c2] = part[:, 0][c2] ^ np.uint32(0x80000000)
    rep = rng.random((nmsg, words, LANES)) < 0.1
    part[:, 7][rep] = part[:, 6][rep]
    if big:
        part[0, :, 0, 3] = np.uint32(0x7F000000)   # 2^127 on every die: the in-package sum overflows
    f = G.from_bits(part)
    pk = [G.add(f[:, 2 * p], f[:, 2 * p + 1]) for p in range(4)]     # level 1: in-package, die 0 + die 1
    sums = G.fold(pk)                                                # level 2: ((P0 + P1) + P2) + P3
    path.mkdir(parents=True, exist_ok=True)

    def hexw(arr):
        return "".join("".join(f"{int(x):08x}" for x in row[::-1]) + "\n" for row in arr.reshape(-1, LANES))
    (path / "part.hex").write_text(hexw(part))
    (path / "sum.hex").write_text(hexw(G.bits(sums)))
    (path / "mode.hex").write_text("".join(f"{m}\n" for m in modes))


def harness(scratch: Path) -> Path:
    h = scratch / "harness.cpp"
    h.write_text('#include "Vtb_coll_tp8.h"\n#include "verilated.h"\n'
                 "int main(int argc, char** argv) { Verilated::commandArgs(argc, argv);\n"
                 "  auto* t = new Vtb_coll_tp8; t->clk = 0;\n"
                 "  while (!Verilated::gotFinish()) { t->clk = !t->clk; t->eval(); }\n"
                 "  t->final(); delete t; return 0; }\n")
    return h


def build(scratch: Path, latu: int, lats: int, define: str | None, wrapper_columns: int = 0, leb: int = 0,
          lc: int = 128, eng: str = "", qfd: bool = False) -> Path:
    obj = scratch / f"obj_u{latu}_s{lats}_w{wrapper_columns}_e{leb}_{lc}{('_' + eng) if eng else ''}{('_' + define) if define else ''}"
    cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-TIMESCALEMOD", "--top-module", "tb_coll_tp8", f"-GWT={int(wrapper_columns)}", f"-GLEB={leb}", f"-GLC={lc}"] + [f"-G{kv}" for kv in eng.split(",") if kv] + [ f"-GLATU={latu}", f"-GLATS={lats}", "-GBPC=3600", "-GICR=32",
           "-Mdir", str(obj)] + ([f"+define+{define}"] if define else []) + [str(s) for s in SRC] + \
          [str(harness(scratch)), "-CFLAGS", "-O1", "-j", "16"]
    if qfd: cmd += ["-DOT_TP8_QFD"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"build failed:\n{r.stdout[-3000:]}{r.stderr[-3000:]}")
    return obj / "Vtb_coll_tp8"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qfd", action="store_true", help="actual die-name collective, independent child clock pins at the reference edge")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--latu", type=int, default=14, help="UCIe hop, cycles (SPEC 3: ~14)")
    ap.add_argument("--lats", type=int, default=40, help="SerDes board link, cycles")
    ap.add_argument("--production", action="store_true", help="Qwen3-8B TP8 shapes (256-word all-reduce, argmax)")
    ap.add_argument("--wrapper-columns", nargs="?", type=int, const=1, default=0,
                    help="WT: 1 = closed column leaves, 2 = registered-return column leaves (qwen-coll-io 10-14), "
                         "3 = pin-registered data leaves + flat metadata column (qwen-coll-io r2 10-14)")
    ap.add_argument("--leb", type=int, default=0, help="1: ot_coll_link_end on every SerDes port (link-level credits)")
    ap.add_argument("--lc", type=int, default=128, help="link credits = receive buffer words with --leb 1")
    ap.add_argument("--eng", default="", help="depth sweep, WT 0 only: comma list of EDEPTH=,EPR=,EMEMM=,ECT=,QLQD=,QTQD=")
    ap.add_argument("--strap", action="store_true",
                    help="WT 3: every die is ONE master (PKG 0 / DIE 0) ranked by the pkg_s / die_ps straps (STRAP 1)")
    ap.add_argument("--mutant-define", default=None)
    ap.add_argument("--only", default=None, help="regex on case names")
    a = ap.parse_args()
    a.out = a.out.resolve()
    if a.wrapper_columns in (2, 3) and not a.eng:
        a.eng = "EDEPTH=64,QLQD=128,QTQD=128"   # the WT 2 / 3 production shape (DEPTH 64 engine leaves, 128-word result queues)
    if a.strap:
        if a.wrapper_columns != 3:
            ap.error("--strap needs --wrapper-columns 3")
        a.eng = ",".join(x for x in (a.eng, "STRAP=1") if x)
    cases = PRODUCTION_CASES if a.production else UNIT_CASES
    if a.only:
        cases = [c for c in cases if re.search(a.only, c[0])]
    a.out.mkdir(parents=True, exist_ok=True)
    exe = build(a.out, a.latu, a.lats, a.mutant_define, a.wrapper_columns, a.leb, a.lc, a.eng, a.qfd)
    bad = []
    records = []
    for i, (name, nmsg, words, gap, skew, mk, inj, ival, big, tagbad) in enumerate(cases):
        rng = np.random.default_rng(100 + i)
        modes = {"r": [0] * nmsg, "g": [1] * nmsg, "m": list(rng.integers(0, 2, nmsg))}[mk]
        vec = a.out / f"vec_{name}"
        vectors(vec, nmsg, words, modes, 1000 + i, big)
        args = [str(exe), f"+VEC={vec}", f"+NMSG={nmsg}", f"+WORDS={words}", f"+GAP={gap}", f"+SKEW={skew}",
                f"+SEED={7 + i}", f"+INJECT={inj}", f"+TAGBAD={tagbad}"] + ([f"+IVAL={ival}"] if ival else [])
        run = subprocess.run(args, capture_output=True, text=True)
        txt = run.stdout
        (a.out / f"{name}.log").write_text(txt + run.stderr)
        m = RES.search(txt)
        ok = run.returncode == 0 and bool(m) and any(l.strip() == "PASS" for l in txt.splitlines())
        g = m.groups() if m else None
        print(f"case {name} lats={a.lats} mutant={a.mutant_define or '-'} {'PASS' if ok else 'FAIL'} "
              + (f"mismatches={g[7]} out_err={g[8]} fault={g[9]} code={g[10]} words_out={g[11]} cycles={int(g[13]) - int(g[12])}"
                 if g else "no result: " + txt.strip()[-300:]), flush=True)
        records.append(dict(name=name, exact=ok, returncode=run.returncode, messages=nmsg, words_per_message=words,
                            mismatches=int(g[7]) if g else None, words_out=int(g[11]) if g else None,
                            first_input_cycle=int(g[12]) if g else None, last_output_cycle=int(g[13]) if g else None,
                            cycles=int(g[13]) - int(g[12]) if g else None))
        if not ok:
            bad.append(name)
    (a.out / "record.json").write_text(json.dumps(dict(schema="opentallas.qwen.tp8.collective.v1", ranks=ND, lanes=LANES,
        latu=a.latu, lats=a.lats, wrapper_columns=a.wrapper_columns, link_end=a.leb, link_credits=a.lc, engine_sweep=a.eng, mutant=a.mutant_define, production=a.production,
        cycle_span="first accepted input on any rank to last output on all ranks, excludes reset",
        cases=records, source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC},
        executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), native_layer_qualified=False), indent=2) + "\n")
    if bad:
        print(f"COLL_TP8 FAIL mutant={a.mutant_define or '-'} failed={','.join(bad)}")
        sys.exit(1)
    print(f"COLL_TP8 PASS cases={len(cases)} lats={a.lats} wt={a.wrapper_columns} leb={a.leb} lc={a.lc}")


if __name__ == "__main__":
    main()
