#!/usr/bin/env python3
"""PLAN-DELTA/QC 2026-10-25: approved TYPE-REDUCE items on the Qwen compute plan, NON-PATH types only (in place, idempotent).

    python3 results/plan_delta_1025/qc/delta_qc.py physical/die_plan/qwen_compute/die_plan.json [--check-only]

Path rule (coord lanes/PATH-QC.md): no type or core used by a PATH-QC instance changes (slice W5, coll_ftc, native59,
glue, phy_ucie_kv, sle_ctl).  A W/E merge re-types the E partitions onto the UNCHANGED W type; the W type json, its
derived wavefront reset pins (IN / rst_o / start_o) and every path partition's published release cycle stay identical.

1. reset.in_sites = the current wavefront IN-site choice (reset_tree.wf_solve on the input plan) of every soft type
   except the non-path E-slice types sle_* (left free).  It freezes the die-global local search so that a re-type
   cannot move a path type's reset pins (an unfrozen re-solve moved coll_ftc / native59 / glue / slw_* pins).
2. W/E merge sle_hc3 -> slw_hc3 (6 E partitions, orient R0 kept; dedup.try_merge proves every die pin unchanged;
   bound RTL of the START bind equal outside the reset tree).  Under (1): path type json + derived reset pins and every
   path partition's release unchanged; die max release 128 -> 127 (START boot S+130 holds).
3. su_lane core re-point (non-path types sle_su_l0 / sle_su_l1 only): an E lane whose pin table equals the W table of
   the same lane exactly (R0) takes module qfd_qc_su_lane_w and the W pins_file (byte-identical W tables untouched).
   Lanes 0-3 and 6 match; lanes 4, 5, 7 differ (E-specific pin placement) and stay qfd_qc_su_lane_e.
Deferred (measured, README): hc0-2, st_a, st_b, su_l0 merges; the su_lane 4-class reduction (changes the path W tables).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import dedup as D  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema as S  # noqa: E402

MERGES = ["hc3"]                                 # sle_<x> -> slw_<x>
SU_TYPES = {"sle_su_l0": "slw_su_l0", "sle_su_l1": "slw_su_l1"}
PATH_PARTS_PREFIX = "sl_W5_"
PATH_TYPES_EXTRA = {"coll_ftc", "native59", "glue", "phy_ucie_kv"}


def pin_tab(path):
    P = json.loads(Path(path).read_text())
    P = P.get("pins", P) if isinstance(P, dict) else P
    return sorted((p["name"], p.get("layer"), round(float(p["x"]), 4), round(float(p["y"]), 4)) for p in P)


def path_types(raw):
    return sorted({p["type"] for p in raw["partitions"]
                   if p["name"].startswith(PATH_PARTS_PREFIX) or p["type"] in PATH_TYPES_EXTRA})


def apply(raw, plan_path):
    log = []
    pdir = Path(plan_path).resolve().parent
    T = raw["partition_types"]
    if raw.get("die", {}).get("name") != "qwen_compute":
        raise SystemExit("delta_qc is scoped to qwen_compute")
    reset = raw["reset"]
    if reset.get("release") != "wavefront":
        raise SystemExit("delta_qc needs the wavefront reset")
    # 1. freeze the wavefront IN sites
    if "in_sites" not in reset:
        sol = RT.wf_solve(S.Plan(raw, path=str(plan_path)))
        keep = set(path_types(raw))
        reset["in_sites"] = {tn: [round(float(v), 4) for v in xy] for tn, xy in sorted(sol["choice"].items())
                             if tn in keep or not tn.startswith("sle_")}
        log.append(f"reset.in_sites frozen for {len(reset['in_sites'])} of {len(sol['choice'])} soft types "
                   "(non-path sle_* types left to the wavefront solver)")
    # 2. W/E merges onto the unchanged W type
    for s in MERGES:
        w, e = "slw_" + s, "sle_" + s
        if e not in T:
            continue
        ok, moves, why = D.try_merge(D.Iface(raw), w, e)
        if not ok:
            raise SystemExit(f"merge {e} -> {w} not exact: {why}")
        for p in raw["partitions"]:
            if p["type"] == e:
                p["type"] = w
                p["orient"] = moves[p["name"]][1]
        del T[e]
        reset["in_sites"].pop(e, None)
        log.append(f"merged {e} -> {w}: {len(moves)} partitions, orients {sorted(set(map(tuple, moves.values())))}")
    # 3. su_lane re-point
    for et, wt in SU_TYPES.items():
        if et not in T:
            continue
        wmap = {h["inst"]: h for h in T[wt]["hard_cores"]}
        for h in T[et]["hard_cores"]:
            wh = wmap.get(h["inst"])
            if wh is None or h["module"] == wh["module"]:
                continue
            same_geom = all(h.get(k) == wh.get(k) for k in ("origin_um", "outline_um", "orient", "track_offset_um"))
            if same_geom and pin_tab(pdir / h["pins_file"]) == pin_tab(pdir / wh["pins_file"]):
                log.append(f"{et}.{h['inst']}: {h['module']} {h['pins_file']} -> {wh['module']} {wh['pins_file']}")
                h["module"], h["pins_file"] = wh["module"], wh["pins_file"]
            else:
                log.append(f"{et}.{h['inst']}: kept {h['module']} (pin table differs from {wt}.{h['inst']})")
    return log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", type=Path)
    ap.add_argument("--check-only", action="store_true", help="report, do not write")
    a = ap.parse_args()
    raw = json.loads(a.plan.read_text())
    before = {tn: D._canon(raw["partition_types"][tn]) for tn in path_types(raw)}
    log = apply(raw, a.plan)
    for tn, k in before.items():
        if D._canon(raw["partition_types"][tn]) != k:
            raise SystemExit(f"PATH type {tn} changed: refusing")
    for ln in log:
        print("delta_qc:", ln)
    if not a.check_only:
        a.plan.write_text(json.dumps(raw, indent=1) + "\n")
        # pin tables no hard core references any more
        refs = {h.get("pins_file") for t in raw["partition_types"].values() for h in t.get("hard_cores", [])}
        for f in sorted((a.plan.parent / "cores" / "su").glob("sle_su_l*_u_lane*_pins.json")):
            rel = str(f.relative_to(a.plan.parent))
            if rel not in refs:
                f.unlink()
                print("delta_qc: removed unreferenced", rel)
    print(f"delta_qc: {len(raw['partition_types'])} types, {len(raw['partitions'])} partitions")


if __name__ == "__main__":
    main()
