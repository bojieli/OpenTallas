#!/usr/bin/env python3
"""Reset release-cycle bench for a relay-form plan event (DIE-S81-85 serdes 11-09), any die: elaborates each type's real
reset tree (reset_tree.rtl_lines) from two plans, simulates a release and compares the cycle every tap / out reset net
goes high.  Exit 0 = same cycles on every net of every type.  --mutant drops one internal relay of plan B's tree and
expects the bench to catch it (exit 0 = caught).
usage: relay_release_bench.py PLAN_A PLAN_B OUT_DIR TYPE [TYPE ...] [--mutant]"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_rtl  # noqa: E402
import reset_tree as R  # noqa: E402
import schema as S  # noqa: E402

FLUSH = 40


def tb(T, lines):
    nets = [f"rst_n_t{i}" for i in range(len(T["taps"]))]
    outs = [f"rst_o_{k}" for k in range(len(T.get("outs", [])))]
    decl = "".join(f"  wire {o};\n" for o in outs)
    body = "\n".join(lines)
    prn = "".join(f'      if (!seen_{n} && {n} === 1\'b1) begin seen_{n} = 1; $display("REL {n} %0d", c); end\n'
                  for n in nets + outs)
    regs = "".join(f"  reg seen_{n} = 0;\n" for n in nets + outs)
    return (f"`timescale 1ns/1ps\nmodule tb;\n  reg clk = 0; always #5 clk = ~clk;\n  reg arst_n = 0; integer c = 0;\n{decl}"
            f"{body}\n{regs}  initial begin\n    repeat ({FLUSH}) @(posedge clk);\n    @(negedge clk); arst_n = 1;\n"
            f"    for (c = 0; c < 64; c = c + 1) begin\n      @(posedge clk); #1;\n{prn}    end\n    $finish;\n  end\nendmodule\n")


def mutate(lines):
    for i, ln in enumerate(lines):
        m = re.match(r"\s*ot_dp_rrelay\S* (u_rrl_\d+) \(\.clk\(clk\), \.d\((\w+)\), \.q\((rst_rl_\d+)\)\);", ln)
        if m:
            return lines[:i] + [f"    assign {m.group(3)} = {m.group(2)};  // MUTANT: relay {m.group(1)} removed"] + lines[i + 1:], m.group(1)
    raise SystemExit("mutant: no internal relay")


def sim(src, work):
    src_p, exe = work.with_suffix(".v"), work.with_suffix(".vvp")
    src_p.write_text(gen_rtl.CELLS + gen_rtl.LOCKUP_CELLS + src)
    subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(src_p)], check=True)
    out = subprocess.run(["vvp", str(exe)], capture_output=True, text=True, check=True).stdout
    return {m.group(1): int(m.group(2)) for m in re.finditer(r"^REL (\w+) (\d+)$", out, re.M)}


def main(argv):
    mutant = "--mutant" in argv
    a, b, d, *types = [x for x in argv if x != "--mutant"]
    Pa, Pb = (S.Plan(json.load(open(p)), p) for p in (a, b))
    Path(d).mkdir(parents=True, exist_ok=True)
    rc, rep = 0, {}
    for tn in types:
        Ta, Tb = R.for_type(Pa, tn), R.for_type(Pb, tn)
        la, lb = R.rtl_lines(Ta), R.rtl_lines(Tb)
        mut = None
        if mutant:
            lb, mut = mutate(lb)
        ra = sim(tb(Ta, la), Path(d) / f"{tn}_a")
        rb = sim(tb(Tb, lb), Path(d) / f"{tn}_b")
        same = ra == rb and len(ra) == len(Ta["taps"]) + len(Ta.get("outs", []))
        diff = sorted(n for n in set(ra) | set(rb) if ra.get(n) != rb.get(n))
        rep[tn] = dict(nets=len(ra), same=same, ndiff=len(diff), first_diff=diff[:3], max_cycle=max(ra.values()),
                       min_cycle=min(ra.values()), mutant=mut,
                       nl_a=sum("ot_dp_rrelay_nl " in x for x in la), nl_b=sum("ot_dp_rrelay_nl " in x for x in lb))
        rc |= (same == mutant)
    print(json.dumps(rep, indent=1))
    return int(rc)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
