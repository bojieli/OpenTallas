#!/usr/bin/env python3
"""Q-CLUSTER-LANDALL (10-18): refresh the compiler / die record results/arch/qwen_cluster_1017/q_cluster16/die_clock_contract.json
from the generated contract (cluster_contract_dv.json, qc_gen.py) and the region audit (region_audit.json): every
multi-bit region crossing landed (+E+1 edges each), latencies, communicating pairs, die obligations.

  die_clock_update.py [--branch B]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "results/arch/qwen_cluster_1017"
REC = ARCH / "q_cluster16/die_clock_contract.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="claude/q-cb16rst-1019")
    a = ap.parse_args()
    C = json.loads((ARCH / "cluster_contract_dv.json").read_text())
    A = json.loads((ARCH / "q_cluster16/region_audit.json").read_text())
    D = json.loads(REC.read_text())
    L = C["landings"]
    assert L.get("mode") == "all" and not A["fails"]
    D.update(lane="Q-CB16RST", branch=a.branch,
             owner_decision="0ei 10-18: 16-region clock split (one region per A0 tile); 0fy 10-18 (owner 0fd accepts latency + "
                            "landing tiles): clock the cluster like the die: a local tree per region, EVERY multi-bit "
                            "region crossing landed")
    D["die_obligations"] = [
        "drop 16 regional clocks per cluster instance (dv2r8f: 48 instances -> 768 regional clock drops) at the cluster's 16 "
        "regional clock pins (face pins of the contract: rows 0 / 3 on the S / N face, rows 1 / 2 on the W / E face, M4; the "
        "die may also feed them as centre area pins); each region builds its own local tree",
        "NO phase alignment owed for data (Q-CLUSTER-LANDALL replaces Q-CL16-EARLY's +/-60 ps): every multi-bit region "
        f"crossing is landed (D {L['D']}, E = K = {L['E']}), so it tolerates any region-to-region skew dL in the window "
        f"{L['window_ps']} at TT and FF.  The die keeps the drops of COMMUNICATING region pairs within +/-400 ps of each other "
        "(TT and FF) only for the cluster SDC's inter-region uncertainty; Q-CB16RST: no 1-bit reset hop crosses a region "
        "seam any more (regional resets below), so no in-cluster single-cycle path depends on region-to-region skew",
        "boundary ports are timed against the region that holds their pin register (port_domains); the die's neighbour links "
        "into / out of the cluster land against THAT region's clock (LANDING-CONTRACT)",
        "REGIONAL RESETS (Q-CB16RST 10-19, replaces the single rst_n): 16 reset pins rst_c<c>r<r> per instance (beside "
        "each ck_c<c>r<r>; 48 instances -> 768 drops).  The die releases all 16 of an instance on the SAME die calendar "
        "edge, each delivered on (and timed against) its own region clock: the die reset tree LANDS each drop (fixed "
        "latency, calendared release).  Each pin is registered at its region entry (u_fab.u_rpin_<q>, ROOT-RST); "
        "in-cluster depth unchanged: tiles / xstn 19 edges after the pin, landing epochs at each landing's common depth "
        "(G == R0, warm-up 25 edges).  A slip of one region by one edge breaks the landings (bench MUT 8 FAILs).",
        "the cluster's port latencies grow (compiler record below): the die schedule takes tap / bco / rs / rs_i->rs_o from "
        "compiler.latency_edges"]
    lat, lat0 = L["latency_edges"], L["latency_edges_unlanded"]
    D["compiler"] = dict(
        added_edges_per_landed_crossing=L["added_edges_per_crossing"],
        note=f"Q-CLUSTER-LANDALL: {L['count']} landed crossings ({L['bits']} b), each +{L['added_edges_per_crossing']} edges "
             "(ring write + E = K read edges); the tree re-aligns with soft pad stages (hard station sites unchanged); "
             "lockstep vs the 8-region fabric: every port = the reference delayed by exactly port_added_edges.",
        latency_edges=lat, latency_edges_unlanded=lat0,
        port_added_edges=dict(L["port_added_edges"], **{f"tap_row{r}": lat["tap"][r] - lat0["tap"][r] for r in lat["tap"]},
                              bco=lat["bco"] - lat0["bco"], rs_i_to_rs_o=lat["rs_i_to_rs_o"] - lat0["rs_i_to_rs_o"]),
        rs_fabric_added=lat["rs_fabric"] - lat0["rs_fabric"],
        realigned_legs=L["realigned_legs"],
        added_edges_per_link={x["name"]: x["added_edges"] for x in L["list"]})
    D["communicating_pairs"] = A["communicating_pairs"]
    D["seam_crossings"] = A["crossings"]
    D["seam_crossing_bits"] = A["crossing_bits"]
    D["seam_crossings_note"] = (f"Q-CLUSTER-LANDALL region_audit.py: {A['crossings']} crossings = {A['landed']} LANDED multi-bit + "
                                f"{A['crossings'] - A['landed']} plain (Q-CB16RST R7: must be 0, regional resets)")
    D["landings"] = [dict(name=x["name"], crossing=x["crossing"], src_region=x["src_region"], dst_region=x["dst_region"],
                          bits=x["bits"], D=x["D"], E=x["E"], K=x["K"], added_edges=x["added_edges"]) for x in L["list"]]
    D["landing_flops"] = L["flops"]
    for q, v in D["clocks"].items():
        v["fabric_flops"] = C["clocks"][q]["fabric_flops"]
    REC.write_text(json.dumps(D, indent=1) + "\n")
    print(REC, L["count"], "landings")


if __name__ == "__main__":
    main()
