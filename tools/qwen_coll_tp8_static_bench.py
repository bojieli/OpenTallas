#!/usr/bin/env python3
"""qwen-coll-io 2026-10-14 (OWNER 0ah: static cycle schedule, no credits/backpressure): bit-exact, cycle-exact bench of
the static TP8 collective rtl/rom/ot_coll_tp8_static.sv in the 8-die model rtl/test/tb_coll_tp8_static.sv.

The script is also the collective's STATIC SCHEDULER (compiler model): every message gets a command cycle c chosen so
that its resources never collide with earlier messages (input slots, S-ring/SerDes write slots, output slots, gather
hold window), using the implemented latencies (LU, LS, SL); the expected output cycle of every word follows from c.
The RTL checks availability and conflicts as faults only; the bench requires every word at exactly its compiled cycle.

Golden: results/arch/qwen_tp8_1012/SPEC.md section 3 via tools/hdc_golden (same as tools/qwen_coll_tp8_bench.py):
  Pp = part(p, die 0) + part(p, die 1);  sum = ((P0 + P1) + P2) + P3;  all-gather word k = TP8 rank k mod 8, index k / 8.
--mutant-define D (OT_TP8S_MUT_OWNER / _GATHER / _RANK / _RLAT): some positive case must FAIL.
Exit 0 iff every case passes (positive cases exact; fault cases raise their fault class)."""
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
from qwen_coll_tp8_bench import rand_f32  # noqa: E402

ND, LANES, SL, GC = 8, 16, 23, 8
SRC = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
    "rtl/rom/ot_coll_fold_slice.sv", "rtl/rom/ot_coll_rst_leaf.sv",
    "physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v",
    "physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v",
    "rtl/rom/ot_coll_tp8_static.sv", "rtl/physical/ot_qfd_io_collective_static.sv", "rtl/test/tb_coll_tp8_static.sv")]
RES = re.compile(r"TP8S dies=8 .* mismatches=(\d+) extra=(\d+) out_err=(\d+) fault=([01]+) code=([01]+) "
                 r"words_out=(\d+) first=(-?\d+) last=(\d+)")

# name, msgs, words, modes, kind, extra plusargs
UNIT_CASES = [
    ("reduce_8w_x16", 16, 8, "r", "pos", {}),
    ("reduce_1w_x9_odd", 9, 1, "r", "pos", {}),
    ("reduce_3w_x8_odd", 8, 3, "r", "pos", {}),
    ("gather_1w_x6", 6, 1, "g", "pos", {}),
    ("gather_4w_x4", 4, 4, "g", "pos", {}),
    ("mixed_8w_x24", 24, 8, "m", "pos", {}),
    ("fault_nan", 4, 8, "r", "inject", {"INJECT": 1, "IVAL": "7fc00000"}),
    ("fault_inf", 4, 8, "r", "inject", {"INJECT": 2, "IVAL": "ff800000"}),
    ("fault_overflow", 4, 8, "r", "inject_big", {"INJECT": 0, "IVAL": "7f000000"}),
    ("fault_tag", 4, 8, "r", "fault", {"TAGBAD": 2}),
    ("fault_drop_word", 4, 8, "r", "fault", {"DROP": 1}),
    ("fault_late_producer", 4, 8, "m", "fault", {"LATE": 2}),
    ("fault_unreserved_schedule", 6, 8, "m", "conf", {"CONF": 1}),
]
PRODUCTION_CASES = [
    ("qwen_ar_256w", 1, 256, "r", "pos", {}),
    ("qwen_layer_2x256w", 2, 256, "r", "pos", {}),
    ("qwen_argmax_1w", 1, 1, "g", "pos", {}),
    ("qwen_layer_2x256w_argmax", 3, 256, "rrg1", "pos", {}),
]


def word_events(mode, c, n, lu, ls):
    """Compiled cycles of one message issued at c: input slots, pairing cycles B, S-ring/SerDes write slots W,
    output slots O (exactly the RTL timeline in ot_coll_tp8_static.sv's header)."""
    if mode == 0:
        slots = [c + 1 + w for w in range(n)]
        b = [c + lu + 4 + w for w in range(n)]
        wr = [x + SL + 2 for x in b]
        out = [c + 2 * lu + 2 * SL + ls + 12 + w for w in range(n)]
        hold = []
    else:
        slots = [c + 1 + GC * i for i in range(n)]
        b = [c + lu + 4 + GC * i for i in range(n)]
        wr = [x + 1 + k for x in b for k in range(8)]
        out = [c + lu + ls + 8 + GC * i + k for i in range(n) for k in range(8)]
        hold = [x + 1 + k for x in b for k in range(7)]
    return slots, b, wr, out, hold


def schedule(modes, nwords, lu, ls, start=40, reserve=True, shared_ucie=False):
    """Greedy static scheduler: earliest command cycle per message with no resource collision."""
    used_w, used_o, used_b, used_h = set(), set(), set(), set()
    used_u = set()
    prog, last_slot = [], start - 1
    for m, mode in enumerate(modes):
        n = nwords[m]
        c = max(start, last_slot)
        while True:
            slots, b, wr, out, hold = word_events(mode, c, n, lu, ls)
            p_events = {x+2 for x in slots}
            r_events = {x-lu-2 for x in out} if mode == 0 else set()
            if shared_ucie and not p_events.isdisjoint(r_events):
                raise ValueError("message exceeds single-UCIe static capacity; compiler must split it before scheduling")
            if not reserve:
                break
            if (used_w.isdisjoint(wr) and used_o.isdisjoint(out) and used_h.isdisjoint(b)
                    and used_b.isdisjoint(hold) and (not shared_ucie or
                    (p_events.isdisjoint(r_events) and used_u.isdisjoint(p_events | r_events)))):
                break
            c += 1
        used_w.update(wr); used_o.update(out); used_b.update(b); used_h.update(hold)
        if shared_ucie: used_u.update(p_events | r_events)
        last_slot = slots[-1]
        prog.append(dict(msg=m, mode=mode, words=n, cmd_cycle=c, first_slot=slots[0], first_out=out[0],
                         last_out=out[-1]))
    return prog


def vectors(path: Path, nwords, prog, seed, big=False):
    """part.hex: message m, die r, word w at pbase(m) + r * words(m) + w; sum.hex at sbase(m) + w."""
    rng = np.random.default_rng(seed)
    parts, sums = [], []
    for m, words in enumerate(nwords):
        part = rand_f32(rng, ND * words * LANES).reshape(ND, words, LANES)   # die r = 2 * package + die
        c1 = rng.random((words, LANES)) < 0.1
        part[1][c1] = part[0][c1] ^ np.uint32(0x80000000)
        c2 = rng.random((words, LANES)) < 0.1
        part[2][c2] = part[0][c2] ^ np.uint32(0x80000000)
        rep = rng.random((words, LANES)) < 0.1
        part[7][rep] = part[6][rep]
        if big and m == 0:
            part[:, 0, 3] = np.uint32(0x7F000000)
        f = G.from_bits(part)
        pk = [G.add(f[2 * p], f[2 * p + 1]) for p in range(4)]
        parts.append(part)
        sums.append(G.bits(G.fold(pk)))
    path.mkdir(parents=True, exist_ok=True)

    def hexw(arr):
        return "".join("".join(f"{int(x):08x}" for x in row[::-1]) + "\n" for row in arr.reshape(-1, LANES))
    (path / "part.hex").write_text("".join(hexw(x) for x in parts))
    (path / "sum.hex").write_text("".join(hexw(x) for x in sums))
    pb = sb = 0
    lines = []
    for p, words in zip(prog, nwords):
        lines.append(f"{p['cmd_cycle']:08x}{p['first_out']:08x}{pb:08x}{sb:08x}{words:04x}{p['mode']:04x}\n")
        pb += ND * words
        sb += words
    (path / "cmd.hex").write_text("".join(lines))


def build(out: Path, lu: int, ls: int, xu: int, xs: int, define: str | None, qfd: bool = False) -> Path:
    obj = out / f"obj_u{lu}_s{ls}_xu{xu}_xs{xs}{'_qfd' if qfd else ''}{('_' + define) if define else ''}"
    h = out / "harness.cpp"
    h.write_text('#include "Vtb_coll_tp8_static.h"\n#include "verilated.h"\n'
                 "int main(int argc, char** argv) { Verilated::commandArgs(argc, argv);\n"
                 "  auto* t = new Vtb_coll_tp8_static; t->clk = 0;\n"
                 "  while (!Verilated::gotFinish()) { t->clk = !t->clk; t->eval(); }\n"
                 "  t->final(); delete t; return 0; }\n")
    cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-TIMESCALEMOD", "--top-module", "tb_coll_tp8_static", f"-GLATU={lu}", f"-GLATS={ls}", f"-GXU={xu}",
           f"-GXS={xs}", "-Mdir", str(obj)] + ([f"+define+{define}"] if define else []) + [str(s) for s in SRC] + \
          [str(h), "-CFLAGS", "-O1", "-j", "16"]
    if qfd:
        cmd += ["+define+OT_TP8S_QFD", f"+define+OT_QFDS_LU={lu}", f"+define+OT_QFDS_LS={ls}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"build failed:\n{r.stdout[-3000:]}{r.stderr[-3000:]}")
    return obj / "Vtb_coll_tp8_static"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--latu", type=int, default=19, help="UCIe link, cycles (static UCIe RD->RX 19, static_io_tx3_1014)")
    ap.add_argument("--lats", type=int, default=344, help="SerDes board link, cycles (static board RD->RX 344)")
    ap.add_argument("--xu", type=int, default=0, help="negative control: UCIe link longer than compiled")
    ap.add_argument("--xs", type=int, default=0, help="negative control: SerDes link longer than compiled")
    ap.add_argument("--production", action="store_true")
    ap.add_argument("--mutant-define", default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--qfd", action="store_true", help="bench the die-name master qfd_io_collective_static")
    a = ap.parse_args()
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    cases = PRODUCTION_CASES if a.production else UNIT_CASES
    if a.only:
        cases = [c for c in cases if re.search(a.only, c[0])]
    if a.xu or a.xs:   # link-latency negative control: one positive shape, every die must flag the link schedule
        cases = [("link_longer_than_compiled", 4, 8, "m", "link", {})]
    exe = build(a.out, a.latu, a.lats, a.xu, a.xs, a.mutant_define, a.qfd)
    bad, records = [], []
    for i, (name, nmsg, words, mk, kind, extra) in enumerate(cases):
        rng = np.random.default_rng(100 + i)
        if mk == "rrg1":
            modes, nw = [0, 0, 1], [words, words, 1]
        else:
            modes = {"r": [0] * nmsg, "g": [1] * nmsg, "m": [int(x) for x in rng.integers(0, 2, nmsg)]}[mk]
            nw = [words] * nmsg
        prog = schedule(modes, nw, a.latu, a.lats, reserve=(kind != "conf"))
        vec = a.out / f"vec_{name}"
        vectors(vec, nw, prog, 1000 + i, big=(kind == "inject_big"))
        args = [str(exe), f"+VEC={vec}", f"+NMSG={nmsg}"] + [f"+{k}={v}" for k, v in extra.items()]
        run = subprocess.run(args, capture_output=True, text=True)
        txt = run.stdout
        (a.out / f"{name}.log").write_text(txt + run.stderr)
        m = RES.search(txt)
        ok = run.returncode == 0 and bool(m) and any(l.strip() == "PASS" for l in txt.splitlines())
        g = m.groups() if m else None
        span = (max(p["last_out"] for p in prog) - prog[0]["first_slot"] + 1)
        print(f"case {name} kind={kind} latu={a.latu} lats={a.lats} xu={a.xu} xs={a.xs} mutant={a.mutant_define or '-'} "
              f"{'PASS' if ok else 'FAIL'} " + (f"mismatches={g[0]} extra={g[1]} out_err={g[2]} fault={g[3]} code={g[4]} "
              f"words_out={g[5]} compiled_span={span}" if g else "no result: " + txt.strip()[-300:]), flush=True)
        records.append(dict(name=name, kind=kind, exact=ok, messages=nmsg, words_per_message=nw, modes=modes,
                            program=prog, compiled_span_cycles=span, fault=g[3] if g else None,
                            fault_code=g[4] if g else None, mismatches=int(g[0]) if g else None,
                            words_out=int(g[5]) if g else None))
        if not ok:
            bad.append(name)
    (a.out / "record.json").write_text(json.dumps(dict(
        schema="opentallas.qwen.tp8.collective.static.v1", ranks=ND, lanes=LANES, latu=a.latu, lats=a.lats,
        xu=a.xu, xs=a.xs, die_name_master=a.qfd, slice_latency=SL, gather_cadence=GC, mutant=a.mutant_define, production=a.production,
        cycle_span="first compiled input slot to last compiled output slot (inclusive); every output checked at its exact "
                   "compiled cycle",
        mechanism="no credits/ready/backpressure: compiled command + fixed-offset rings; checks are fault-only",
        cases=records, source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC},
        executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), native_layer_qualified=False), indent=2) + "\n")
    if bad:
        print(f"COLL_TP8S FAIL mutant={a.mutant_define or '-'} failed={','.join(bad)}")
        sys.exit(1)
    print(f"COLL_TP8S PASS cases={len(cases)} latu={a.latu} lats={a.lats}")


if __name__ == "__main__":
    main()
