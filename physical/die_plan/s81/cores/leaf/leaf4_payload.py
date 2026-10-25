#!/usr/bin/env python3
"""S81/LEAF4 10-25: build the leaf delta payload (only the 72 ot_s81sl_leaf types' physical fields) from
  BASE   the current plan (faultfeed + IR + gather B + FTCHAN, branch claude/s81-plan2-1025r@0cb4df92f0),
  PLACED corridor.py r3 output on BASE (hard_cores + internal_stations; 3-group template with 25.92-um streets),
  JOBS   per-type ft_sites.py results on PLACED (ft_slots stations / regs_um / bit_sites_um / bit_site_cell_um).
Per type it writes: hard_cores (+ obs_max = the core LEF OBS ceiling: lane_pr / vsw / rxsf / rxsb M5, 512x128 SRAM M4,
the leaf plan-LEF cores vn_a / vn_b / vq / vs / ve_m / ve_s M7 -- G2 obstructs to obs_max), internal_stations
(normalised to the plan convention: launch = conn[0], capture = conn[1], from_um / regs_um ordered from conn[0], so
tools/die_plan/kit_istations.py maps every core<->core entry onto its CS_* class), ft_slots.
usage: leaf4_payload.py BASE PLACED JOBS OUT_PAYLOAD [--types t6,t8] [--repo WT]"""
import argparse
import json
import re
import subprocess
from pathlib import Path

LEAF = "ot_s81sl_leaf__t"
DERIVED = {"stations", "regs_um", "bit_sites_um", "bit_site_cell_um"}


def lef_ceiling(repo, lef, cache={}):
    if lef not in cache:
        t = subprocess.run(["git", "-C", repo, "show", "HEAD:" + lef], capture_output=True, text=True).stdout
        if not t:
            raise SystemExit(f"leaf4_payload: LEF {lef} not in the repo (fail closed)")
        L = [int(x) for o in re.findall(r"\n\s*OBS\b(.*?)\n\s*END\b", t, re.S) for x in re.findall(r"LAYER M(\d+)", o)]
        cache[lef] = "M%d" % max(L) if L else "M7"
    return cache[lef]


def norm(e):
    """plan convention (gen_plan_v4): launch = first conn element, capture = second (no 'core:'), from_um at launch"""
    if not e.get("conn", "").startswith("core:") or "|" not in e["conn"]:
        return e
    a, b = e["conn"].split("|", 1)
    b = b[5:] if b.startswith("core:") else b
    if e.get("launch") == a:
        return e
    e = dict(e, launch=a, capture=b, from_um=e["to_um"], to_um=e["from_um"], regs_um=list(reversed(e["regs_um"])))
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("placed")
    ap.add_argument("jobs")
    ap.add_argument("out")
    ap.add_argument("--types")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[5]))
    a = ap.parse_args()
    B = json.load(open(a.base))["partition_types"]
    Q = json.load(open(a.placed))["partition_types"]
    sel = set(a.types.split(",")) if a.types else None
    out = {}
    for tn, T in sorted(B.items()):
        if not tn.startswith(LEAF) or (sel and tn.split("__")[1] not in sel):
            continue
        q = Q[tn]
        J = json.load(open(Path(a.jobs) / tn / "plan.json"))["partition_types"][tn]
        for k in T:
            if k not in ("hard_cores", "internal_stations", "ft_slots"):
                assert T[k] == q[k] == J[k], (tn, k)
        assert len(J["ft_slots"]) == len(T["ft_slots"]), tn
        for s, n in zip(T["ft_slots"], J["ft_slots"]):
            assert {k: v for k, v in s.items() if k not in DERIVED} == {k: v for k, v in n.items() if k not in DERIVED}, \
                (tn, s["name"])
        hc = [dict(c, obs_max=lef_ceiling(a.repo, c["lef"])) for c in J["hard_cores"]]
        out[tn] = dict(hard_cores=hc, internal_stations=[norm(e) for e in J["internal_stations"]],
                       ft_slots=J["ft_slots"])
    Path(a.out).write_text(json.dumps(dict(types=out), separators=(",", ":")) + "\n")
    print("payload types", len(out))


if __name__ == "__main__":
    main()
