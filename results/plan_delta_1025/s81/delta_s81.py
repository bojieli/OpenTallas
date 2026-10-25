#!/usr/bin/env python3
"""PLAN-DELTA/S81 2026-10-25: batched S81 type-reduction delta, NON-PATH types only (COORD TYPE-REDUCE rulings 06:47).

What it applies (deterministic, idempotent, base-agnostic -- re-derived from whatever plan it is given):
  exact type merges found by tools/die_plan/dedup.py with --fix-order (TYPE-DEDUP: same netlist key + same die
  interface up to a die-wide bit-order repair of abutting ports; the die netlist, lanes, latency and census are
  untouched), restricted so that
    * no PATH-S81 type is merged, used as the merge target, or has its pin table touched by the order repair;
    * the bound-RTL identity gate of dedup runs when PLANDIR/bind/bound_r8/rtl exists.
  A group whose order repair would touch a path type is dropped (and reported), never forced.
Everything else in the TYPE-REDUCE S81 list is deferred (see README.md next to this file).

usage (repo root):  python3 results/plan_delta_1025/s81/delta_s81.py physical/die_plan/s81/die_plan.json \
                        [--out OUT.json] [--prov PROV.json]
Without --out the plan is rewritten in place in the repo's compact format (physical/die_plan/s81/compact_plan.py:
indent 1, ft_slots / contents / hard_cores entries on one line), byte-identical to the input when nothing applies.
2026-10-25 09:30 re-run (PLAN-DELTA-S81R) on main 863d618928 (S81-PLAN2/PLAN3 + eng E2 reservation 70bb1be9ab):
writer switched to compact_plan.dumps (main's format; the old indent-1 writer expanded 'contents' entries)."""
import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(ROOT / "physical" / "die_plan" / "s81"))
import dedup  # noqa: E402
import compact_plan  # noqa: E402  (repo format of the S81 plan since S81-PLAN2/PLAN3, byte-identical round trip)

# PATH-S81 (coord lanes/PATH-S81.md, 08:07-08:12 PDT) -- never changed by this delta
PATH = {"seqhost__t1", "slice_station__t18", "slice_station__t20", "slice_station__t22",
        "svc_hi_dsdv_svc_rs__t5", "svc_hi_dsdv_svc_rs__t6", "svc_lo_dsdv_svc_rs__t6", "svc_lo_dsdv_svc_rs__t7",
        "eng__t1", "dsdv_slice_c1x_C__t8", "dsdv_slice_c1x_C__t9", "dsdv_slice_lepe_mu_C__t1",
        "dsdv_slice_lepe_nh_mus_C__t1", "svc_hi_dsdv_svc_pvso_entry__t1", "svc_hi_dsdv_svc_pvso_entry__t2",
        "svc_hi_dsdv_svc_rs__t2", "svc_hi_dsdv_svc_rs__t3", "svc_lo_dsdv_svc_rs__t2", "dsdv_slice_iq_C__t1",
        "dsdv_slice_lepw_mu_C__t1", "col_h10_r0_p1__t1", "col_h10_r0_p4__t1",
        # C1 representative (PATH-S81 08:12): kept exactly as on the base
        "col_h9_r1__t1"}
# eng E2 path (70bb1be9ab reserves the actual E2 core in eng__t1, listed above); the E2 boot/data chain types
# (svc t5/t6/t7, leaves t36/t55-t61, stations t18/t20/t22, c1x t8/t9) are in this set too.
PATH |= {"ot_s81sl_leaf__t%d" % i for i in [36, 55, 56, 57, 58, 59, 60, 61] + list(range(65, 72))}


def dumps(p):
    """repo format (results/s81_faultfeed_1025/fmt.py): indent 1, hard_cores / ft_slots entries compact."""
    p = copy.deepcopy(p)
    slots = {}
    for t in p["partition_types"].values():
        for key in ("hard_cores", "ft_slots"):
            fs = t.get(key)
            for i, s in enumerate(fs or []):
                k = "@@FT%d@@" % len(slots)
                slots[k] = json.dumps(s, separators=(",", ":"))
                fs[i] = k
    txt = json.dumps(p, indent=1)
    for k, v in slots.items():
        txt = txt.replace(json.dumps(k), v, 1)
    return txt


def select(raw, rep):
    """filter the dedup report: drop members touching PATH; then drop groups whose order repair touches PATH."""
    rep = copy.deepcopy(rep)
    dropped = []
    for g in rep["exact_groups"]:
        keep = []
        for m in g["members"]:
            if m["type"] in PATH or m["into"] in PATH:
                dropped.append(dict(member=m["type"], into=m["into"], why="path type"))
            else:
                keep.append(m)
        g["members"] = keep
    rep["exact_groups"] = [g for g in rep["exact_groups"] if g["members"]]
    # per-group trial: which types' pin tables the order repair touches
    for g in sorted(rep["exact_groups"], key=lambda g: g["canon"]):
        one = dict(rep, exact_groups=[g])
        _, prov = dedup.apply(raw, one)
        bad = sorted(set(prov["pin_table_touched_types"]) & PATH)
        g["_touched"] = prov["pin_table_touched_types"]
        if bad:
            for m in g["members"]:
                dropped.append(dict(member=m["type"], into=m["into"], why="order repair touches path " + ",".join(bad)))
            g["members"] = []
    rep["exact_groups"] = [g for g in rep["exact_groups"] if g["members"]]
    return rep, dropped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--prov")
    a = ap.parse_args()
    src = Path(a.plan)
    raw = json.loads(src.read_text())
    missing = sorted(t for t in PATH if t not in raw["partition_types"])
    rtl = src.resolve().parent / "bind" / "bound_r8" / "rtl"
    rep = dedup.analyze(raw, fix_order=True, rtl_dirs=[str(rtl)] if rtl.is_dir() else [])
    rep, dropped = select(raw, rep)
    new, prov = dedup.apply(raw, rep)
    probs = dedup.verify(raw, new)
    touched = set(prov["pin_table_touched_types"])
    assert not (touched & PATH), touched & PATH
    for tn in PATH & set(raw["partition_types"]):
        assert new["partition_types"][tn] == raw["partition_types"][tn], tn
    path_parts = {p["name"]: p for p in raw["partitions"] if p["type"] in PATH}
    for p in new["partitions"]:
        if p["name"] in path_parts:
            assert p == path_parts[p["name"]], p["name"]
    if probs:
        raise SystemExit("dedup verify not exact: %s" % probs[:5])
    prov.update(verify=dict(exact=True), dropped=dropped, path_types=sorted(PATH), path_types_missing=missing,
                rtl_gate=str(rtl) if rtl.is_dir() else "n/a (no bound_r8 rtl in tree)")
    if not prov["merged"]:            # idempotent: nothing left to merge -> leave the plan byte-identical
        new = raw
    out = Path(a.out) if a.out else src
    txt = compact_plan.dumps(new)
    if not (out.exists() and out.read_text() == txt):
        out.write_text(txt)
    if a.prov:
        Path(a.prov).write_text(json.dumps(prov, indent=1) + "\n")
    print("delta_s81: %d -> %d types; merged %s; %d ports bit-order repaired; touched %s; dropped %s"
          % (prov["types_before"], prov["types_after"],
             {k: v["into"] for k, v in prov["merged"].items()}, len(prov["reordered_ports"]),
             sorted(touched), [(d["member"], d["why"]) for d in dropped]))


if __name__ == "__main__":
    main()
