#!/usr/bin/env python3
"""DIE-S81-85 11-09 DSREP append: yosys equivalence of every module in rtl/common/ot_meso_fifo.sv and
rtl/common/ot_dp_clk_landing.sv, GOLD = the files before the DSREP commit (git parent), GATE = the branch files, both at
DEFAULT DSREP (the parameter is never set here).

Per (module, parameter set, defines): elaborate GOLD and GATE separately (read_verilog -sv, chparam, hierarchy, proc,
keep_hierarchy cleared, flatten, memory, opt_clean), then equiv_make gold gate / equiv_simple -seq 4 / equiv_induct
-seq 4 / equiv_status -assert.  Verdicts: PROVED, UNPROVEN (equiv_status reports unproven cells), ILLEGAL (GOLD and GATE
both refuse to elaborate the set: a parameter combination the RTL rejects; same verdict on both sides), TOOL_ASSERT
(yosys crashed on both sides: not a proof and not a rejection), ELAB_MISMATCH
(only one side elaborates) or ERROR.

Matrix (covers every parameter set instantiated on main: the bind emits ot_dp_clk_landing #(.W, .WNEG, .FREG) on all
dies; HBM stations / qwen slab ports / s81 dsfd glue instantiate ot_meso_fifo with the bit parameters below, every bit
combination is in the grid; ot_meso_ring is instantiated only inside these two files, grid over all its bit
parameters): see jobs().  W sweeps one bit, chunk edges 64 / 65 and every landed width on main (LANDED_WIDTHS, +0/+1/+2).

usage: run_eq.py GOLD_DIR GATE_DIR OUT_DIR [-j N]     (needs yosys on PATH; ORFS image on the fleet, in docker)
"""
import argparse
import itertools
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

FILES = ("ot_meso_fifo.sv", "ot_dp_clk_landing.sv")

# every distinct landing width in the 9 landing tables on main (s81, qwen_kvsys, qwen_compute; all rows default ring form)
LANDED_WIDTHS = (
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 15, 16, 18, 20, 23, 24, 25, 28, 29, 30, 31, 32, 33, 34, 35, 38, 39, 40,
    43, 44, 45, 48, 50, 53, 56, 57, 59, 60, 61, 64, 69, 70, 73, 75, 76, 82, 84, 93, 95, 96, 107, 112, 116, 119, 128,
    129, 132, 138, 140, 143, 144, 159, 160, 174, 176, 187, 228, 256, 258, 261, 264, 267, 268, 271, 276, 287, 291,
    293, 299, 321, 325, 380, 384, 396, 415, 438, 450, 452, 453, 456, 512, 513, 514, 516, 520, 522, 523, 524, 530,
    536, 538, 539, 543, 544, 547, 548, 549, 551, 552, 553, 562, 566, 568, 571, 572, 597, 598, 600, 604, 631, 651,
    652, 668, 671, 682, 764, 765, 766, 780, 789, 799, 805, 908, 1044, 1056, 1062, 1080, 1087, 1088, 1104, 1118,
    1120, 1167, 1230, 1264, 1368, 1559, 1573, 1574, 1591, 1607, 1882, 2103, 2133, 2663, 2938, 3740, 4015)


def jobs():
    out = []
    add = lambda mod, params, defs=(): out.append((mod, dict(params), tuple(defs)))
    # ot_dp_clk_landing: widths x WNEG x FREG x the S81 landing defines
    for w, wneg, freg, defs in itertools.product((1, 2, 5, 64, 65, 513, 514, 1105), (0, 1), (0, 1),
                                                 ((), ("OT_S81_CLAND_WCHK",), ("OT_S81_CLAND_WCHK", "OT_S81_CLAND_LOCAL_ON"))):
        add("ot_dp_clk_landing", dict(W=w, WNEG=wneg, FREG=freg), defs)
    # ot_meso_ring: every bit parameter combination, W 64 and 513; DEPTH 8 / OFFSET 4 points
    bits = ("RDREG", "WCHK", "PLREG", "ONV", "RSPLIT", "WCHKC", "TNEG")
    for w in (64, 513):
        for v in itertools.product((0, 1), repeat=len(bits)):
            add("ot_meso_ring", dict(W=w, **dict(zip(bits, v))))
    for rd in (0, 1):
        add("ot_meso_ring", dict(W=64, DEPTH=8, OFFSET=4, GUARD_LO=1, GUARD_HI=7, RDREG=rd))
    # ot_meso_fifo: every bit parameter combination at W 64, ENABLE 1 (+ ENABLE 0, PINREG define, dsfd DEPTH 8 set)
    fbits = ("RDREG", "NOBP", "CRDREG", "WCHK", "OBYP", "PLREG", "ONREG", "RSPLIT")
    for v in itertools.product((0, 1), repeat=len(fbits)):
        add("ot_meso_fifo", dict(W=64, ENABLE=1, **dict(zip(fbits, v))))
    add("ot_meso_fifo", dict(W=64, ENABLE=0))
    add("ot_meso_fifo", dict(W=65, ENABLE=1))
    add("ot_meso_fifo", dict(W=64, ENABLE=1), ("OT_MESO_PINREG",))
    add("ot_meso_fifo", dict(W=64, ENABLE=1, RDREG=1, NOBP=1), ("OT_MESO_PINREG",))
    for en in (0, 1):
        add("ot_meso_fifo", dict(W=64, ENABLE=en, DEPTH=8, OFFSET=4, GUARD_LO=1, GUARD_HI=7, CREDITS=16))
    # text-unchanged leaf modules of the two files
    for n in (1, 4, 64):
        add("ot_meso_sel", dict(N=n))
    for n in (2, 4, 9):
        add("ot_meso_ohor", dict(N=n))
    for reg, split, srep in itertools.product((0, 1), (0, 1), (1, 4)):
        add("ot_meso_dsel", dict(W=64, DEPTH=4, REG=reg, SPLIT=split, SREP=srep))
    add("ot_meso_dsel", dict(W=64, DEPTH=8, REG=1))
    for w in (16, 64):
        add("ot_meso_wch", dict(W=w, DEPTH=4))
        add("ot_meso_wcc", dict(W=w, DEPTH=4))
    add("ot_meso_dsel_sel", dict(DEPTH=4))
    add("ot_meso_dsel_sel", dict(DEPTH=8))
    for w in (1, 64):
        add("ot_dp_landing_input_face", dict(W=w))
    add("ot_dp_landing_fault_port", {})
    for n in (1, 3):
        add("ot_dp_landing_collect", dict(N=n))
    add("ot_dp_landing_face", {})
    # every landed width as bound: W, W+1 (S81 valid bit) and W+2 (dataflow status bits), both write edges
    done = {(p["W"], p["WNEG"]) for m, p, d in out if m == "ot_dp_clk_landing" and not d and p["FREG"] == 0}
    for w, wneg in itertools.product(sorted({x + k for x in LANDED_WIDTHS for k in (0, 1, 2)}), (0, 1)):
        if (w, wneg) not in done:
            add("ot_dp_clk_landing", dict(W=w, WNEG=wneg, FREG=0))
    return out


def elab(side, d, mod, params, defs):
    dd = " ".join(f"-D{x}" for x in defs)
    ch = " ".join(f"-set {k} {v}" for k, v in params.items())
    chp = f"chparam {ch} {mod}\n" if params else ""
    files = " ".join(str(Path(d) / f) for f in FILES)
    # chparam + rename -top: `hierarchy -chparam` asserts in yosys 0.67 on ot_meso_dsel SREP 4 (Design::add, both sides)
    return (f"read_verilog -sv {dd} {files}\n{chp}hierarchy -check -top {mod}\nproc\n"
            f"setattr -mod -unset keep_hierarchy *\nflatten\nmemory\nopt_clean\nrename -top {side}\n"
            f"design -stash {side}\n")


def run(args, idx, job):
    mod, params, defs = job
    tag = f"{idx:04d}"
    wd = Path(args.out) / "work"

    def yosys(script, suffix):
        y, lg = wd / f"{tag}.{suffix}.ys", wd / f"{tag}.{suffix}.log"
        y.write_text(script)
        p = subprocess.run(["yosys", "-q", "-l", str(lg), "-s", str(y)], capture_output=True, text=True, timeout=3600)
        return p.returncode

    rc = yosys(elab("gold", args.gold, mod, params, defs) + elab("gate", args.gate, mod, params, defs) +
               "design -copy-from gold -as gold gold\ndesign -copy-from gate -as gate gate\n"
               "equiv_make gold gate eq\nhierarchy -top eq\nequiv_simple -seq 4\nequiv_induct -seq 4\n"
               "tee -o " + str(wd / f"{tag}.status") + " equiv_status\nequiv_status -assert\n", "eq")
    status = (wd / f"{tag}.status").read_text() if (wd / f"{tag}.status").exists() else ""
    if rc == 0:
        verdict = "PROVED"
    elif status:
        verdict = "UNPROVEN"
    else:
        g = yosys(elab("gold", args.gold, mod, params, defs), "gold")
        t = yosys(elab("gate", args.gate, mod, params, defs), "gate")
        verdict = "ILLEGAL" if g and t else ("ELAB_MISMATCH" if bool(g) != bool(t) else "ERROR")
        if verdict == "ILLEGAL" and "Assert" in (wd / f"{tag}.gold.log").read_text(errors="replace"):
            verdict = "TOOL_ASSERT"       # a yosys crash is not an RTL rejection: never reported as ILLEGAL
    cells = ""
    for line in status.splitlines():
        if "equiv cells" in line or "unproven" in line:
            cells += line.strip() + " "
    if verdict in ("ERROR", "ELAB_MISMATCH", "ILLEGAL", "TOOL_ASSERT"):
        errs = [l.strip() for l in (wd / f"{tag}.eq.log").read_text(errors="replace").splitlines() if l.startswith("ERROR")]
        cells = (errs[:1] or ["no ERROR line"])[0][:200]
    return dict(i=idx, module=mod, params=params, defines=list(defs), verdict=verdict, status=cells.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gold"); ap.add_argument("gate"); ap.add_argument("out")
    ap.add_argument("-j", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--only", default="", help="comma list of job indices (smoke test)")
    args = ap.parse_args()
    (Path(args.out) / "work").mkdir(parents=True, exist_ok=True)
    js = list(enumerate(jobs()))
    if args.only:
        keep = {int(x) for x in args.only.split(",")}
        js = [j for j in js if j[0] in keep]
    with ThreadPoolExecutor(args.j) as ex:
        res = list(ex.map(lambda a: run(args, *a), js))
    (Path(args.out) / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    lines = ["module\tparams\tdefines\tverdict\tequiv_status"]
    for r in res:
        lines.append(f"{r['module']}\t{','.join(f'{k}={v}' for k, v in r['params'].items()) or '-'}\t"
                     f"{'+'.join(r['defines']) or '-'}\t{r['verdict']}\t{r['status']}")
    (Path(args.out) / "result.tsv").write_text("\n".join(lines) + "\n")
    summ = {}
    for r in res:
        summ.setdefault(r["module"], {}).setdefault(r["verdict"], 0)
        summ[r["module"]][r["verdict"]] += 1
    bad = [r for r in res if r["verdict"] not in ("PROVED", "ILLEGAL")]
    txt = [f"{m}: " + ", ".join(f"{v} {n}" for v, n in sorted(c.items())) for m, c in sorted(summ.items())]
    txt.append(f"TOTAL {len(res)} sets, PROVED {sum(r['verdict'] == 'PROVED' for r in res)}, "
               f"ILLEGAL(both sides) {sum(r['verdict'] == 'ILLEGAL' for r in res)}, OTHER {len(bad)}")
    txt.append("EQ rc=" + ("0" if not bad else "1"))
    (Path(args.out) / "summary.txt").write_text("\n".join(txt) + "\n")
    print("\n".join(txt))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
