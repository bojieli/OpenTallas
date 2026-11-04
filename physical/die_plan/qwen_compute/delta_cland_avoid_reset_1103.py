"""DIE-QC-66/CLK 11-03 CLAND class fix (plan delta, fix-only): QC slw_sc_v1 ring band over a reset relay.

Root cause (kit-wave d90b109213 place FAIL "OT_CLAND no legal nonoverlapping row/site in reserved band for
u_bound.u_cland_collect_rst_rl_15/_N_ (collector:rst_rl_15)" on slw_sc_v1__cl63e5a7a2, __cl64543eaf__cl4590432d,
__cl64543eaf__cl5e017c6f): DIE-KV-32 resize_undersized_bands grew band x_fw_fe_p1_i from x 17.28..45.36 to
17.28..62.64 um (4612 um2 for a 4522 um2 ring_ff reserve = 98 % reserved) over the wire reset relay u_rrl_15 at
(45.72, 669.6).  QC never opted into the FLOW-7 reset-site avoidance (budgets.cland_avoid_reset_types empty), so the
resize ignored the relay.  landing_placement.tcl fills the band with the FIRM ring first; the rst_rl_15 collector
cells then find no site even in the x8 grown window (+-17.28 um lies 99 % inside the full band).

Fix: opt the slw_sc_v1 base types into budgets.cland_avoid_reset_types and re-run resize_undersized_bands on their
types (the same tool, the same sidecar collector trees): every band of those types that overlaps a reset relay /
collector site is re-sited by _storage_band with the reset sites as obstacles (405-um reach kept).  Every other type,
band and key stays byte-identical.

usage: delta_cland_avoid_reset_1103.py PLAN SIDECAR [--out OUT] [--report REPORT.json]
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "die_plan"))
import clock_landing_plan as CP  # noqa: E402

TYPES = ["slw_sc_v1__cl63e5a7a2", "slw_sc_v1__cl64543eaf__cl4590432d", "slw_sc_v1__cl64543eaf__cl5e017c6f"]


def base_types(plan, types):
    out = []
    for tn in types:
        b = plan["partition_types"][tn]["clock"]["landing_contract"].get("base_type") or tn
        if b not in out:
            out.append(b)
    return out


def apply(plan, sidecar, types=TYPES):
    p = json.loads(json.dumps(plan))
    sel = p.setdefault("budgets", {}).setdefault("cland_avoid_reset_types", [])
    for b in base_types(p, types):
        if b not in sel:
            sel.append(b)
    new, rep = CP.resize_undersized_bands(p, sidecar, types)
    return new, rep


def relay_hits(plan, types):
    """bands of `types` that overlap a reset relay/collector site (collector_tree relays +-2.16 um)"""
    hits = []
    for tn in types:
        lc = plan["partition_types"][tn]["clock"]["landing_contract"]
        rs = CP.reset_site_rects(lc.get("collector_tree"))
        for bus, b in sorted(lc["bands"].items()):
            if bus.startswith("monitor_") or not b.get("rect_um"):
                continue
            if any(CP._rect_overlap(b["rect_um"], o) for o in rs):
                hits.append((tn, bus))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("sidecar")
    ap.add_argument("--out"); ap.add_argument("--report")
    a = ap.parse_args()
    s = open(a.plan).read(); plan = json.loads(s); assert json.dumps(plan) + "\n" == s, "plan format"
    side = json.load(open(a.sidecar))
    new, rep = apply(plan, side)
    left = relay_hits(new, TYPES)
    assert not left, f"bands still over reset sites: {left[:5]}"
    for tn in new["partition_types"]:
        if tn not in TYPES:
            assert new["partition_types"][tn] == plan["partition_types"][tn], tn
    print(f"cland_avoid_reset_types {new['budgets']['cland_avoid_reset_types']}; resized {len(rep)} bands on "
          f"{len(TYPES)} types; max hop {max(r['hop_um'] for r in rep):.1f} um; bands over reset sites after: 0")
    open(a.out or a.plan, "w").write(json.dumps(new) + "\n")
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)


if __name__ == "__main__":
    main()
