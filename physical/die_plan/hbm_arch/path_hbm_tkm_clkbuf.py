#!/usr/bin/env python3
"""PATH-HBM TKM corridor clock buffers (COORD ruling (1) 2026-10-25 14:44): the TKMCLK step put every TKM core clock
pin at the E-face mid (column hops 354.24 um, turns 328.51 um), but the 4 column hops across the L4 corridor (285.12
gap) stay 630.72 um and the 4 across L150 (60.48 gap) 406.08 um: with one master in one orientation per column, no
pin placement fixes them.  Structural fix: ONE shared clock branch buffer per corridor crossing, on std-cell sites in
the corridor (never on a hard core), driving both tiles of the hop, so launch and capture share their last common
clock point (CPPR) and each leg is half the hop (315.36 / 203.04 um <= 405).  Plan form: root clock.branch_buffers[] +
taps[].parent (schema/check.py check_clock_branch_buffers).  CLOCK-RESET signs the insertion budget (budget_owner).

    python3 path_hbm_tkm_clkbuf.py --src <plan dir> --out <new plan dir>
"""
import argparse, json, os, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import path_hbm_b2p as PB  # noqa: E402
import schema as S  # noqa: E402
import check as C  # noqa: E402

LEG_MAX = C.CLOCK_LEG_MAX_UM
CELL = "BUFx12f_ASAP7_75t_R"
BUDGET = ("CLOCK-RESET (COORD 14:44 ruling (1)): the corridor buffer replaces a branch segment of the partition clock "
          "tree; the partition tree balances all 33 TKM taps to the same insertion, so the buffer adds no skew budget; "
          "related-pair skew across the corridor hop = leg mismatch only (equal legs by construction)")


def apply(plan):
    T = plan["partition_types"]["root"]
    ck = T["clock"]
    HC = {c["inst"]: c for c in T["hard_cores"]}
    taps = {t["name"]: t for t in ck["taps"]}
    if ck.get("branch_buffers"):
        raise ValueError("root already has branch_buffers")
    pairs = [("u_tkm_SW_root", "u_tkm_SW_tile0")] + [(f"u_tkm_SW_tile{k}", f"u_tkm_SW_tile{k + 1}") for k in range(31)]
    bufs, rows = [], []
    for a, b in pairs:
        ta, tb = taps[a]["xy"], taps[b]["xy"]
        d = abs(ta[0] - tb[0]) + abs(ta[1] - tb[1])
        if d <= LEG_MAX:
            continue
        if round(ta[0], 3) != round(tb[0], 3):
            raise ValueError(f"{a}->{b}: {d:.1f} um turn hop over reach (only column corridor hops are expected)")
        ya0, ya1 = HC[a]["origin_um"][1], HC[a]["origin_um"][1] + HC[a]["outline_um"][1]
        yb0, yb1 = HC[b]["origin_um"][1], HC[b]["origin_um"][1] + HC[b]["outline_um"][1]
        lo, hi = (ya1, yb0) if ya1 <= yb0 else (yb1, ya0)
        if hi - lo <= 0:
            raise ValueError(f"{a}->{b}: no corridor between the cores")
        # the buffer sits mid-corridor at the clock-pin x (E face, M6 pin): equal legs to both taps
        y = round((ta[1] + tb[1]) / 2, 3)
        if not (lo < y < hi):
            raise ValueError(f"{a}->{b}: mid point {y} not inside the corridor {lo}..{hi}")
        x = round(ta[0], 3)
        col = int(round((HC[a]["origin_um"][0] - 181.44) / 328.32))
        corr = "L4" if hi - lo > 200 else "L150"
        name = f"u_tkmclk_{corr}_c{col}"
        legs = [round(abs(ta[1] - y), 2), round(abs(tb[1] - y), 2)]
        bufs.append(dict(name=name, xy=[x, y], drives=[a, b], cell=CELL, legs_um=legs,
                         budget_owner="CLOCK-RESET", site=f"std-cell rows of the {corr} corridor y {lo:.2f}..{hi:.2f} "
                         f"(gap {hi - lo:.2f} um), column {col}",
                         note="PATH-HBM TKMCLKBUF: shared corridor clock buffer (COORD 14:44 ruling (1)); " + BUDGET))
        for t in (a, b):
            if taps[t].get("parent"):
                raise ValueError(f"{t} would hang on two corridor buffers")
            taps[t]["parent"] = name
            taps[t]["note"] = (taps[t].get("note", "") + f" | PATH-HBM TKMCLKBUF: hangs on {name}").lstrip(" |")
        rows.append(dict(launch=a, capture=b, tap_dist_um=round(d, 2), buffer=name, legs_um=legs, corridor=corr,
                         corridor_gap_um=round(hi - lo, 2)))
    ck["branch_buffers"] = bufs
    return rows


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--src", required=True)
    a.add_argument("--out", required=True)
    x = a.parse_args()
    src, out = Path(x.src), Path(x.out)
    if out.exists():
        raise ValueError("new output directory required")
    out.mkdir(parents=True)
    for p in src.iterdir():
        if p.name.startswith("g0") or p.name.startswith("gates") or p.name == "die_plan.json" or p.suffix in (".log", ".exit"):
            continue
        if p.is_symlink():
            os.symlink(os.readlink(p), out / p.name)
        elif p.is_dir():
            shutil.copytree(p, out / p.name, symlinks=True)
        else:
            shutil.copy2(p, out / p.name)
    plan = json.loads((src / "die_plan.json").read_text())
    rows = apply(plan)
    plan["note"] = plan.get("note", "") + " | PATH-HBM TKMCLKBUF: shared corridor clock buffers (L4/L150 crossings)"
    S.Plan(plan, out / "die_plan.json")
    (out / "die_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    rep = dict(src=str(src), src_plan_sha256=PB.sha(src / "die_plan.json"), buffers=rows,
               worst_leg_um=max((max(r["legs_um"]) for r in rows), default=0.0),
               out_plan_sha256=PB.sha(out / "die_plan.json"))
    (out / "tkm_clkbuf_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(n=len(rows), worst_leg_um=rep["worst_leg_um"],
                          buffers=[(r["buffer"], r["launch"], r["capture"], r["legs_um"]) for r in rows],
                          plan=rep["out_plan_sha256"][:12]), indent=1))


if __name__ == "__main__":
    main()
