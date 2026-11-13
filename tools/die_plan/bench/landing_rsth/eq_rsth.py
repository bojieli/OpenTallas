#!/usr/bin/env python3
"""CLAND-RELAY-3 RSTH-1 yosys equivalence (COORD 11-13 (3): two reader-START copies per 64-bit chunk).

Two proofs, both flattened yosys equiv_make / equiv_simple -seq 4 / equiv_induct -seq 4 / equiv_status -assert:

  IDENT  GOLD = rtl/common/{ot_dp_clk_landing_ca,ot_meso_fifo,ot_dp_clk_landing}.sv of the base tree (origin/main),
         GATE = the same files of the branch, SAME parameters.  Covers ot_dp_clk_landing_cas / ot_meso_ring_ca /
         ot_dp_clk_landing_ca / ot_meso_dsel over the parameter sets the generator emits (RSTREP 0, legacy chunk
         groups <= 1 + NCH, DSREP 1/4/8, WREG, PLACEREP, READ_CHUNK, DEPTH 4/8): every ring that does not take the new
         per-chunk copy count is logic-identical to main.
  RSTH   both sides = the branch files; module rsth_wrap = the reader-START stage as built by the generator
         (ot_dp_landing_relay_rep #(N), d = start, rst_raw_n = raw reset) driving ot_dp_clk_landing_cas rst_n / rst_xn.
         GOLD N = 1 + NCH (the CLAND-RELAY-2 one-copy-per-chunk form), GATE N = 1 + RH x NCH (RSTH-1).  The relay copies
         are same-D / same-clock / same-reset kept flops; with keep cleared, opt_merge merges them (that merge IS the
         claim "every copy equals rst_n"), and equiv then proves q / ready / fault identical.
  Mutant: the RSTH set re-run with -DOT_MESO_CA_MUTANT_RSTH on GATE must be UNPROVEN.

usage: eq_rsth.py GOLD_DIR GATE_DIR OUT_DIR [-j N]   (yosys on PATH: openroad/orfs:asap7lock)
"""
import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

FILES = ("rtl/common/ot_dp_clk_landing_ca.sv", "rtl/common/ot_meso_fifo.sv", "rtl/common/ot_dp_clk_landing.sv")

WRAP = """
module rsth_wrap #(parameter integer N = 10, parameter integer W = 568, parameter integer DEPTH = 4,
                   parameter bit WREG = 1, parameter integer DSREP = 8, parameter bit PLACEREP = 1,
                   parameter integer WRITE_CHUNK = 64, parameter bit STATUS_REG = 0) (
    input wire fclk, input wire t_rst_n, input wire clk, input wire start, input wire raw_n,
    input wire [$clog2(DEPTH)+3:0] strap_k, input wire [W-1:0] d,
    output wire [W-1:0] q, output wire ready, output wire fault);
    wire rs_q; wire [N-1:0] rs_x;
    ot_dp_landing_relay_rep #(.N(N)) u_rs (.clk(clk), .rst_raw_n(raw_n), .d(start), .q(rs_q), .qx(rs_x));
    ot_dp_clk_landing_cas #(.W(W), .DEPTH(DEPTH), .WREG(WREG), .DSREP(DSREP), .WRITE_CHUNK(WRITE_CHUNK),
                            .STATUS_REG(STATUS_REG), .RSTREP(N), .PLACEREP(PLACEREP)) u_ring (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rs_q), .rst_xn(rs_x), .strap_k(strap_k), .d(d), .q(q),
        .ready(ready), .fault(fault));
endmodule
"""


def nch(w):
    return -(-w // 64)


def rh(dsrep, depth):
    for h in range(1, dsrep + 1):
        if dsrep % h == 0 and (dsrep // h) * 2 * depth + 1 <= 48:
            return h
    return dsrep


def jobs():
    J = []
    cas = "ot_dp_clk_landing_cas"
    for w in (1, 64, 65, 130, 568):
        for depth in (4, 8):
            for wreg, dsrep in ((0, 1), (1, 4), (1, 8), (0, 8)):
                n = nch(w)
                reps = {0}
                if n > 1:
                    reps |= {1 + n, 1 + max(1, n // 3)}       # one copy per chunk / legacy fanout-max chunk groups
                else:
                    reps |= {2}
                for rep in sorted(reps):
                    for pl in ((0, 1) if n > 1 else (0,)):
                        J.append(("IDENT", cas, dict(W=w, DEPTH=depth, WREG=wreg, DSREP=dsrep, RSTREP=rep, PLACEREP=pl), ()))
    for w, rc in ((568, 48), (130, 16)):
        J.append(("IDENT", cas, dict(W=w, DEPTH=4, WREG=1, DSREP=1, READ_CHUNK=rc, RSTREP=1 + -(-(-(-w // 64) * 64) // rc)), ()))
    for w in (64, 568):
        J.append(("IDENT", "ot_dp_clk_landing_ca", dict(W=w, DEPTH=4, K=3, DSREP=8 if w > 64 else 1), ()))
    for srep in (1, 4, 8):
        for depth in (4, 8):
            J.append(("IDENT", "ot_meso_dsel", dict(W=64, DEPTH=depth, REG=1, SREP=srep), ()))
    # RSTH: the new per-chunk copy count against the one-copy-per-chunk form
    for w, depth, wreg, dsrep, wc, st in ((568, 4, 1, 8, 16, 0), (568, 4, 1, 8, 64, 0), (130, 4, 1, 8, 16, 1),
                                         (568, 8, 1, 8, 16, 0), (256, 4, 0, 8, 64, 0), (256, 4, 1, 4, 16, 0)):
        h = rh(dsrep, depth)
        if h > 1:
            base = dict(W=w, DEPTH=depth, WREG=wreg, DSREP=dsrep, PLACEREP=1, WRITE_CHUNK=wc, STATUS_REG=st)
            J.append(("RSTH", "rsth_wrap", dict(base, N=1 + nch(w)), dict(base, N=1 + h * nch(w)), ()))
    J.append(("RSTH_MUT", "rsth_wrap", dict(W=568, DEPTH=4, WREG=1, DSREP=8, PLACEREP=1, WRITE_CHUNK=16, N=10),
              dict(W=568, DEPTH=4, WREG=1, DSREP=8, PLACEREP=1, WRITE_CHUNK=16, N=19), ("OT_MESO_CA_MUTANT_RSTH",)))
    return J


def elab(side, d, mod, params, defs, wrap, merge):
    dd = " ".join(f"-D{x}" for x in defs)
    ch = " ".join(f"-set {k} {v}" for k, v in params.items())
    files = " ".join(str(Path(d) / f) for f in FILES) + (f" {wrap}" if wrap else "")
    mg = ("setattr -unset keep *\nsetattr -mod -unset keep *\nopt_merge -share_all\nopt_clean\n"
          "opt_merge -share_all\nopt_clean\n") if merge else ""
    return (f"read_verilog -sv {dd} {files}\nchparam {ch} {mod}\nhierarchy -check -top {mod}\nproc\n"
            f"setattr -mod -unset keep_hierarchy *\nflatten\nmemory\nopt_clean\n{mg}rename -top {side}\n"
            f"design -stash {side}\n")


def run(args, idx, job):
    kind, mod = job[0], job[1]
    if kind == "IDENT":
        gp, tp, defs = job[2], job[2], job[3]
        gd, td, wrap, merge, gdefs = args.gold, args.gate, None, False, defs
    else:
        gp, tp, defs = job[2], job[3], job[4]
        gd, td, wrap, merge, gdefs = args.gate, args.gate, str(Path(args.out) / "rsth_wrap.sv"), True, ()
    wd = Path(args.out) / "work"
    tag = f"{idx:04d}"
    y, lg, st = wd / f"{tag}.ys", wd / f"{tag}.log", wd / f"{tag}.status"
    y.write_text(elab("gold", gd, mod, gp, gdefs, wrap, merge) + elab("gate", td, mod, tp, defs, wrap, merge) +
                 "design -copy-from gold -as gold gold\ndesign -copy-from gate -as gate gate\n"
                 "equiv_make gold gate eq\nhierarchy -top eq\nequiv_simple -seq 4\nequiv_induct -seq 4\n"
                 f"tee -o {st} equiv_status\nequiv_status -assert\n")
    p = subprocess.run(["yosys", "-q", "-l", str(lg), "-s", str(y)], capture_output=True, text=True)
    status = st.read_text() if st.exists() else ""
    verdict = "PROVED" if p.returncode == 0 else ("UNPROVEN" if status else "ERROR")
    cells = " ".join(l.strip() for l in status.splitlines() if "equiv cells" in l or "unproven" in l)
    if verdict == "ERROR":
        errs = [l.strip() for l in lg.read_text(errors="replace").splitlines() if l.startswith("ERROR")]
        cells = (errs[:1] or ["no ERROR line"])[0][:200]
    want = "UNPROVEN" if kind == "RSTH_MUT" else "PROVED"
    return dict(i=idx, kind=kind, module=mod, gold=gp, gate=tp, defines=list(defs), verdict=verdict,
                ok=verdict == want, status=cells)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gold"); ap.add_argument("gate"); ap.add_argument("out"); ap.add_argument("-j", type=int, default=8)
    a = ap.parse_args()
    (Path(a.out) / "work").mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "rsth_wrap.sv").write_text(WRAP)
    J = jobs()
    with ThreadPoolExecutor(a.j) as ex:
        R = sorted(ex.map(lambda ij: run(a, *ij), enumerate(J)), key=lambda r: r["i"])
    lines = ["i\tkind\tmodule\tgold\tgate\tdefines\tverdict\tequiv_status"]
    for r in R:
        lines.append("\t".join([str(r["i"]), r["kind"], r["module"], json.dumps(r["gold"], sort_keys=True),
                                json.dumps(r["gate"], sort_keys=True), ",".join(r["defines"]), r["verdict"], r["status"]]))
    (Path(a.out) / "result.tsv").write_text("\n".join(lines) + "\n")
    summ = {}
    for r in R:
        summ.setdefault((r["kind"], r["verdict"]), 0)
        summ[(r["kind"], r["verdict"])] += 1
    bad = [r for r in R if not r["ok"]]
    txt = "\n".join(f"{k} {v}: {n}" for (k, v), n in sorted(summ.items()))
    txt += f"\nTOTAL {len(R)} sets, as expected {len(R) - len(bad)}, unexpected {len(bad)}\n"
    txt += "EQ " + ("PASS" if not bad else "FAIL") + "\n"
    (Path(a.out) / "summary.txt").write_text(txt)
    print(txt)
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
