#!/usr/bin/env python3
"""QC-CORES-2 btab r8 (COORD RULING BTAB-R7 04:44, METHODOLOGY 12.8c + d1): designed FIXED ENTRY TRUNK for the shallow
no-pad tree.  The no-pad tree (every edge at its own shortest length, su_kit_gate --straight L1,L2,L3, 0 detours) is
balanced by plan-computed per-branch sizing (su_branch_size, 12.8 d1); it is then ~50 ps shallow of the 12.3 target, so
(12.8c) ONE trunk of n identical buffers is inserted between the entry root and the root's children, on a straight column
below the entry at 1.08 um pitch (same form as core_family_slice.add_entry_trunk, S81-CORE-LAT-R14).  Every root->sink
path gains the same n stages (window unchanged by construction); the trunk cells are not resized.  (master, n) is chosen
deterministically by the GATING predictor (phys_gate.predict_file, OT_PHYS_FIT = uf_phys3 v1) before any build:
guard-band PASS first, then min |TT rise - 250| + |FF early - 202.5|, tie -> fewer cells, smaller master.  No measured input.  PLAN MODEL, UNCHECKED.
usage: trunk_r8.py SIZED.tcl ASBUILT.json GEO LIBDIR OUT.tcl
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qc_su_prog_l1_1026"))
import phys_gate as PG  # noqa: E402

MENU = ["BUFx8_ASAP7_75t_R", "BUFx10_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R", "BUFx16f_ASAP7_75t_R", "BUFx24_ASAP7_75t_R"]
NMAX = 12
PITCH = 1.08


def with_trunk(text, master, n):
    if n == 0:
        return text
    rx, ry = map(float, re.search(r"set ot_ms_root \{([\d.]+) ([\d.]+)\}", text).groups())
    names = [f"K_r{i}" for i in range(n)]
    tr = [f" {{{nm} {'root' if i == 0 else names[i - 1]} {rx:.3f} {ry - PITCH * (n - i) - 0.54:.3f} {master}}}"
          for i, nm in enumerate(names)]
    head, rest = text.split("set ot_ms_tree {", 1)
    blk, tail = rest.split("\n}", 1)
    lines = [re.sub(r"^(\s*\{\S+) root ", r"\1 " + names[-1] + " ", ln) for ln in blk.split("\n")]
    return head + "set ot_ms_tree {" + "\n".join(tr + [ln for ln in lines if ln.strip()]) + "\n}" + tail


def main():
    spec, asb, geo, libdir, out = sys.argv[1:6]
    base = Path(spec).read_text()
    tmp = Path(out).with_suffix(".try.tcl")
    rows, best = [], None
    for m in MENU:
        for n in range(0, NMAX + 1):
            if n == 0 and m != MENU[0]:
                continue
            tmp.write_text(with_trunk(base, m, n))
            o = PG.predict_file(str(tmp), asb, geo, libdir)
            tt, ff = o["TT_rise"], o["FF_early"]
            err = abs(tt["mean"] - PG.TARGET["TT"]) + abs(ff["mean"] - PG.TARGET["FF"])
            rows.append(dict(master=m, n=n, TT=tt, FF=ff, gate=o["gate"]["verdict"], err=round(err, 2)))
            key = (o["gate"]["verdict"] != "PASS", round(err, 1), n, MENU.index(m))
            if best is None or key < best[0]:
                best = (key, m, n)
    tmp.unlink()
    _, m, n = best
    note = (f"# QC-CORES-2 12.8c fixed entry trunk: {n} x {m} between root and its children (plan-computed by uf_phys3, "
            f"trunk_r8.py, no measured input) of {Path(spec).name}\n")
    Path(out).write_text(note + with_trunk(base, m, n))
    o = PG.predict_file(out, asb, geo, libdir, extra_inputs=[spec, __file__])
    o["trunk"] = dict(rule="12.8c fixed entry trunk + 12.8 d1 (plan-computed before build)", master=m, stages=n,
                      menu=MENU, nmax=NMAX, sweep=rows)
    Path(str(Path(out).with_suffix("")) + ".phys.json").write_text(json.dumps(o, indent=1))
    print("TRUNK", m, n, PG.line(o))


if __name__ == "__main__":
    main()
