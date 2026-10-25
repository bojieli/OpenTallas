#!/usr/bin/env python3
"""KV-FT 10-24: before/after report of the v3.9ft candidate (ft crossings, bit-mm, latency, types, modelled options).

    python3 ft_compare_v39.py BEFORE.json AFTER.json AUDIT_BEFORE_DIR AUDIT_AFTER_DIR > report.json
"""
import functools
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("OT_DIE_PLAN_TOOLS", os.path.join(HERE, "..", "..", "..", "tools", "die_plan")))


def fault_age(raw, sinks):
    """longest lane-cycle path into each sink over the fault / flag chain lanes (fch / efault / pvf / pvw flags)."""
    ports = {x["id"]: x for x in raw["ports"]}
    lat = raw["latency"]["lanes"]
    edges = {}
    for ln in raw["lanes"]:
        a, b = ports[ln["ports"][0]], ports[ln["ports"][-1]]
        if re.search(r"(fch|efault|pvf_|o_pvw__u_sN_j_(fault|y_valid))", a["src"]["bus"]):
            edges.setdefault(b["dst"]["part"], []).append((a["src"]["part"], lat[ln["id"]]["cycles"]))

    @functools.lru_cache(None)
    def depth(n):                      # chains are acyclic
        return max([0] + [c + depth(s) for s, c in edges.get(n, [])])
    return {s: depth(s) for s in sinks}


def main():
    b, a = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
    sb = json.load(open(os.path.join(sys.argv[3], "ft_audit.json")))
    sa = json.load(open(os.path.join(sys.argv[4], "ft_audit.json")))
    rb = {r["lid"]: r for r in json.load(open(os.path.join(sys.argv[3], "ft_lanes.json")))}
    ra = {r["lid"]: r for r in json.load(open(os.path.join(sys.argv[4], "ft_lanes.json")))}
    keys = ("lanes", "ft_lanes", "crossings", "mean_crossings", "max_crossings", "bit_crossings", "bit_mm")
    out = dict(schema="opentallas.kv_ft_report.v1", before={k: sb[k] for k in keys}, after={k: sa[k] for k in keys})
    out["delta"] = {k: round(sa[k] - sb[k], 3) for k in keys}
    out["delta_pct"] = {k: round(100.0 * (sa[k] - sb[k]) / sb[k], 1) for k in keys if sb[k]}
    out["classes_before"], out["classes_after"] = sb["classes"], sa["classes"]
    out["hub_star"] = dict(before=sb["hub_star"], after=sa["hub_star"])
    slots = lambda raw: sum(len(t.get("ft_slots", [])) for t in raw["partition_types"].values())  # noqa: E731
    out["ft_slots"] = dict(before=slots(b), after=slots(a))
    ch = []
    for tn, tb in b["partition_types"].items():
        ta = a["partition_types"][tn]
        if tb != ta:
            ch.append(dict(type=tn, instances=sum(1 for p in a["partitions"] if p["type"] == tn),
                           hard=bool(tb.get("hard")), ft_slots=[len(tb.get("ft_slots", [])), len(ta.get("ft_slots", []))],
                           buses=[len(tb["buses"]), len(ta["buses"])]))
    out["types_changed"] = ch
    out["types_unchanged"] = sorted(set(b["partition_types"]) - {c["type"] for c in ch})
    # latency
    lb, la = b["latency"]["lanes"], a["latency"]["lanes"]
    out["lane_cycle_changes_kept_ids"] = {l: [lb[l]["cycles"], la[l]["cycles"]] for l in lb
                                          if l in la and lb[l]["cycles"] != la[l]["cycles"]}
    sinks = ["hub_C", "hroot_EN", "hroot_ES", "hroot_WN", "hroot_WS", "hub_Eo", "hub_Wo"]
    fb = {s: v for s, v in fault_age(b, sinks).items()}
    fa = {s: v for s, v in fault_age(a, sinks).items()}
    out["fault_flag_age_cycles"] = dict(before=fb, after=fa,
                                        note="longest fch/efault/pv-flag chain path into each collector (lane cycles)")
    hro = {}
    for q, side in (("EN", "E"), ("ES", "E"), ("WN", "W"), ("WS", "W")):
        lid = {"EN": "L1447", "ES": "L1448", "WN": "L1449", "WS": "L1450"}[q]
        hro[q] = [lb[lid]["cycles"], la[f"LHT_{side}"]["cycles"] + la[lid]["cycles"]]
    out["kvs_ctl_to_hroot_cycles"] = hro
    # modelled options (not in the candidate): numbers from the after-state lane model
    diag = [r for r in ra.values() if r["cls"] == "D:pc<->pv diagonal (row pair)"]
    straight = [r for r in ra.values() if r["cls"] == "D:pc<->pv (shared PV column)"]
    key = lambda r: (re.sub(r"_d\d+$", "", r["sbus"]), re.sub(r"_d\d+$", "", r["dbus"]), r["src"][:5], r["dst"][:4])  # noqa
    Ls = {}
    for r in straight:
        Ls.setdefault(key(r), []).append(r["L"])
    sav = sum(r["w"] * (r["L"] - statistics.mean(Ls[key(r)])) for r in diag) / 1e3
    ec = [r for r in ra.values() if r["cls"].startswith("T") and "hub_C" in (r["src"], r["dst"])]
    io_bot = min(p["origin_um"][1] for p in a["partitions"] if p["name"] in ("sys_c",))
    hub_top = 12165.12 + 1676.16
    Lst = io_bot - hub_top
    far = [r for r in ra.values() if r["cls"] == "C:hroot far chain ends" and r["nx"] >= 7]
    out["modelled_options"] = {
        "MS pc<->pv row-pair re-bind (vport/slg endpoint of even pc rows into the even pv row)": dict(
            lanes=len(diag), crossings=-len(diag), bit_crossings=-sum(r["w"] for r in diag), bit_mm=-round(sav),
            cycles=f"{sorted(set(r['cyc'] for r in diag))} -> {sorted(set(r['cyc'] for r in straight))}",
            cost="binder content move (pv16 vport + slg landing) between pv row types; pv vo all-gather re-derived; "
                 "re-kit all pv types"),
        "MC E-corridor straightening (sys_c <-> hub_C down the pv column)": dict(
            lanes=len(ec), crossings=-2 * len(ec), bits=sum(r["w"] for r in ec),
            route_um=f"{min(r['L'] for r in ec):.0f}-{max(r['L'] for r in ec):.0f} -> {Lst:.0f}",
            bit_mm=-round(sum(r["w"] * (r["L"] - Lst) for r in ec) / 1e3),
            cycles_405=f"{min(r['cyc405'] for r in ec)}-{max(r['cyc405'] for r in ec)} -> {2 + math.ceil(Lst / 405) - 1}",
            cost="plan-only re-route (post_v37s router) but pv_v2/v4/v6 are shared N/S types -> +3 types; "
                 "per-layer d2d <-> kvs_attn round trip"),
        "MR far chain heads (host_hbm_rst_n -> phy_X_0 via pc_X_0; idhr ID chain from row 7)": dict(
            lanes=len(far), crossings=-sum(r["nx"] for r in far),
            cost="hbm_rst_n: hard PHY wrapper pin moves N -> W face (kv3_phy, kv3_phy_v1 drops its ft slot); idhr: "
                 "ID numbering order (strap) change"),
        "IO-row <-> hub trunk": dict(note=f"distance-bound: IO row bottom -> hub row top = {Lst:.0f} um = "
                                     f"{math.ceil(Lst / 405)} stations at 405 um whatever the partition labels; same-"
                                     "outline swaps cannot shorten it (ft_swap_search_v39)"),
    }
    json.dump(out, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
