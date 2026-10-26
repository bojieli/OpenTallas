#!/usr/bin/env python3
"""S81 + S81-HEAD hard-core clock-latency status vs the common target (METHODOLOGY 12.3: 250 TT / 202.5 FF +-20).

Reads (read-only, git refs so the table is reproducible):
  S81 island plan  claude/s81-core-lat-r2-1026:physical/die_plan/s81/core_lat/island_plan_s81_1026.json
                   (per type: replicas, outline, 12.8 class, current signed/kit VIEW insertion = liberty
                    max_clock_tree_path min/max, plan-model prediction)
  HEAD plan        origin/main:physical/die_plan/s81_head/die_plan.json (hd_tile core taps, CP2 early insertion)
plus MEASURED trial rows recorded in the lane files (each with its source + CHECKED/UNCHECKED label).

"view" numbers are the existing kits' face-pin / early-tap views (what the die sees today), NOT a 12.8 structure.
usage: core_lat_table.py [--repo R] [--out DIR]
"""
import argparse, collections, json, subprocess
from pathlib import Path

TT, FF, TOL = 250.0, 202.5, 20.0
S81_REF = "origin/claude/s81-core-lat-r2-1026:physical/die_plan/s81/core_lat/island_plan_s81_1026.json"
HEAD_REF = "origin/main:physical/die_plan/s81_head/die_plan.json"

# measured 12.8-structure trials (lane files are the source; numbers copied verbatim)
MEASURED = {
    "dsdv_gunit_l4": dict(tt=259.69, ff=208.55, rc="GRT", label="CHECKED (NUMBER-CHECK 06:59)",
                          what="cl26rt centre M5 pin + 4x1 count-split H-tree, 0 pads; all-reg mean (pinreg 261.39/210.27)"),
    "dsdv_gunit_l1": dict(tt=None, ff=None, rc="-", label="NO NUMBER",
                          what="cl26rt died FAIL_PREFLOOR kit LEC (old kit lec.py) 06:49"),
    "ot_s81sl_eg": dict(tt=None, ff=None, rc="-", label="NO NUMBER",
                        what="cl26rt stopped after synth at the 06:4x park (no CTS)"),
    "ot_s81hd_elemA_cv": dict(tt=344.05, ff=280.95, rc="GRT", label="UNCHECKED",
                              what="Codex v4q r2 quadrant H-tree (4 TritonCTS quadrants), quadrant means TT 336.7-355.2 / "
                                   "FF 274.0-290.2; root cause non-NDR trunk + 70-sink leaves (lanes/HEAD-CORE-LAT 08:16); GEOM-REVIEW: V4Q FAIL STRUCTURAL "
                                   "for adoption -- NW quadrant 2,953 sinks vs ~8,500 others, ~25% outline empty -> fix in the PLAN "
                                   "(rebalance quadrant sink loads / outline from logic), not per-quadrant CTS settings"),
    "ot_s81hd_elemB_cv": dict(tt=295.0, ff=236.6, rc="GRT", label="UNCHECKED",
                              what="c2 centred island single CTS tree, 10 BUFx24 stages from 836 leaves (06:34)"),
}


def show(repo, ref):
    return json.loads(subprocess.run(["git", "-C", repo, "show", ref], capture_output=True, text=True,
                                     check=True).stdout)


def verdict(tt, ff):
    if tt is None:
        return "NO NUMBER"
    ok_t = abs(tt - TT) <= TOL
    ok_f = ff is None or abs(ff - FF) <= TOL
    if ok_t and ok_f:
        return "IN"
    side = "HIGH" if tt > TT + TOL or (ff is not None and ff > FF + TOL) else "LOW"
    return side


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    a = ap.parse_args()
    rows = []
    sp = show(a.repo, S81_REF)
    for t in sp["types"]:
        li, lf = t.get("lib_insertion_tt") or {}, t.get("lib_insertion_ff") or {}
        vt = None if li.get("max") is None else (li["min"] + li["max"]) / 2
        vf = None if lf.get("max") is None else (lf["min"] + lf["max"]) / 2
        m = MEASURED.get(t["module"])
        rows.append(dict(die="S81", module=t["module"], replicas=t["replicas"], outline_um=t["outline_um"],
                         c2c_um=t.get("centre_to_corner_um"), cls=t["mode"],
                         view_tt=[li.get("min"), li.get("max")], view_ff=[lf.get("min"), lf.get("max")],
                         view_verdict=verdict(vt, vf), pred=t.get("pred_total_tt_ff"),
                         trunk_chain=(t.get("trunk_chain") or {}).get("stages"),
                         meas=m, meas_verdict=verdict(m["tt"], m["ff"]) if m else None))
    hp = show(a.repo, HEAD_REF)
    cnt = collections.Counter(p["type"] for p in hp["partitions"])
    hd = hp["partition_types"]["hd_tile"]
    by_mod = collections.defaultdict(list)
    for hc in hd["hard_cores"]:
        by_mod[hc["module"]].append(hc)
    ins = {tp["name"].rsplit(".clk", 1)[0]: tp.get("insertion_ps") for tp in hd["clock"]["taps"]}
    for mod, hcs in sorted(by_mod.items()):
        w, h = hcs[0]["outline_um"]
        e = ins.get(hcs[0]["inst"])
        m = MEASURED.get(mod)
        rows.append(dict(die="S81-HEAD", module=mod, replicas=len(hcs) * cnt["hd_tile"], outline_um=[w, h],
                         c2c_um=round((w + h) / 2, 2), cls="CENTRE_HTREE (in-core islands)" if (w + h) / 2 > 200 else
                         "CENTRE_TREE", view_tt=[e, e], view_ff=[None, None], view_verdict=verdict(e, None),
                         pred=None, trunk_chain=None, meas=m, meas_verdict=verdict(m["tt"], m["ff"]) if m else None))
    summ = collections.Counter((r["die"], r["meas_verdict"] or ("view " + r["view_verdict"])) for r in rows)
    out = Path(a.out)
    (out / "core_lat_table.json").write_text(json.dumps(dict(
        target=dict(tt=TT, ff=FF, tol=TOL), sources=[S81_REF, HEAD_REF], rows=rows,
        summary={f"{k[0]}|{k[1]}": v for k, v in sorted(summ.items())}), indent=1) + "\n")
    f = lambda v: "-" if v is None else f"{v:.0f}"
    L = ["| die | module | x | outline um | c->corner | 12.8 class | view TT (min-max) | view FF | view | pred TT/FF "
         "| measured 12.8 trial TT/FF (RC, label) | trial |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    order = {"HIGH": 0, "NO NUMBER": 1, "LOW": 2, "IN": 3}
    for r in sorted(rows, key=lambda r: (r["die"], order.get(r["meas_verdict"] or r["view_verdict"], 9), -r["replicas"])):
        m = r["meas"]
        ms = "-" if not m else (f"{f(m['tt'])}/{f(m['ff'])} ({m['rc']}, {m['label']})" if m["tt"] else m["label"])
        p = "-" if not r["pred"] else f"{r['pred'][0]:.0f}/{r['pred'][1]:.0f}"
        L.append(f"| {r['die']} | {r['module']} | {r['replicas']} | {r['outline_um'][0]:g}x{r['outline_um'][1]:g} | "
                 f"{f(r['c2c_um'])} | {r['cls']} | {f(r['view_tt'][0])}-{f(r['view_tt'][1])} | "
                 f"{f(r['view_ff'][0])}-{f(r['view_ff'][1])} | {r['view_verdict']} | {p} | {ms} | {r['meas_verdict'] or '-'} |")
    L += ["", "Measured-trial notes:"] + [f"- {k}: {v['what']} [{v['label']}]" for k, v in MEASURED.items()]
    (out / "core_lat_table.md").write_text("\n".join(L) + "\n")
    print(json.dumps({f"{k[0]}|{k[1]}": v for k, v in sorted(summ.items())}))


if __name__ == "__main__":
    main()
