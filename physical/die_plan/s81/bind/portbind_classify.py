#!/usr/bin/env python3
"""S81/PORTBIND 10-25: classify portbind_raw.json (portbind_audit.py) into the port-bind gap audit.

Classes:  ok        die IO of a modelled PHY macro (SerDes pma_*), declared position strap
          needs_lane a functional path the plan must carry (fix = lane / design item named in `fix`)
          planned    the plan carries it (lane exists) but the as-built die does not wire it: bind/RTL owed
          dead       no consumer / no producer: drop on BOTH ends (RTL port narrowed or removed, as OWNER DECISION 8)
          tied       a literal on a functional input (violation; none left after the reclassification below)
          strap      a literal the bind should declare as a position strap (bind config gap, not a design gap)

    python3 classify.py portbind_raw.json core_conns.json die_plan.json OUT/audit.json
"""
import json
import re
import sys
from collections import defaultdict

raw = json.load(open(sys.argv[1]))
cc = json.load(open(sys.argv[2]))
plan = json.load(open(sys.argv[3]))

FAULT = "D-FNET (die fault/status network to seqhost, OWNER?/COORD)"
RULES_IN = [
    (r"^ot_pdie_serdes_col\.pma_(rx|rck)$", "ok", "SerDes PHY off-die input (modelled PHY, die.io window)"),
    (r"^dsdv_bk_sel_vmtx\.(ca|cb)$", "planned", "H4 lanes ca/cb__s_0N_LP__bk_sel; GEN/bind must take the H4 RTL "
     "(ot_s81sl_lep_mu_ab_idx ca_o/cb_o), not the as-built die-top ports"),
    (r"^dsdv_idx_qf\.ql$", "needs_lane", "D-QTREE: rank-tree query fan-out (parent die -> this die), OWNER?/COORD"),
    (r"^dsdv_idx_qf\.uid$", "needs_lane", "D-CFG: die rank-tree uid (die-position config), OWNER?/COORD"),
    (r"^dsdv_eng_rr\.cfg_(en|layer|rank)$", "needs_lane", "D-CFG: engram die-position config, OWNER?/COORD"),
    (r"^dsfd_coll_lane_[ew]_safe8_ntf\.chb$", "strap", "slice strap ch_b passed to the coll lane leaf as chb: the "
     "bind straps regex lists ch_b only (asbuilt straps += chb)"),
    (r"^dsdv_svc_rs(_pvso_entry)?\.(dn_i|up_i|ri|gi_v|gi_d|si_v|si_d)$", "dead",
     "D-SVCARITY: unused child arms of the 4-arm svc tree node (as-built ties 0, outputs *_nc): narrow per type"),
    (r"^dsdv_svc_rs_pvso_entry\.q$", "dead", "D-SVCARITY: q[514:513] above the 513-b q frame (as-built ties 0)"),
    (r"^ot_s81sl_capc(5r|2)\.rt_[ew]$", "dead", "D-CAPEND: rt return input of a capc at the slice-row end (no "
     "neighbour on that side): narrow per variant (both ends)"),
    (r"^\$adff\.D$", "dead", "D-GLUE: iq slice glue flop with D=const (Yosys $adff), its Q drives only block_fault"),
]
RULES_OUT = [
    (r"^ot_pdie_serdes_col\.pma_(tx|tck)$", "ok", "SerDes PHY off-die output (modelled PHY)"),
    (r"^dsdv_bk_sel_vmtx\.tl_o$", "planned", "H4 lane tl__bk_sel__s_0N_LP; GEN/bind must take the H4 RTL"),
    (r"^dsdv_idx_qf\.qc0$", "needs_lane", "D-QTREE: rank-tree query fan-out to the NEXT-stage child, OWNER?/COORD"),
    (r"^dsdv_idx_qf\.qc1$", "dead", "D-QTREE: second child link -- every S81 tree child is NEXT-ward (shard_tree over "
     "consecutive stages, one stage circuit pair A); qc1 == qc0 copy: drop both ends"),
    (r"^(dsdv_bk_sel_vmtx\.(fault|vm_fault|tx_st)|dsdv_eng_rr\.st|dsdv_eng_tap(_w)?\.fault|dsdv_gunit\.fault|"
     r"dsdv_idx_qf\.st|dsdv_idx_rg3(_nq)?\.st|dsdv_svc_rs_pvso_entry\.(fault|so_ready|so_done|so_fault_code)|"
     r"dsfd_dvland_pvrd\.fault|ot_hbm3e_phy_v41x_aw30_e8p5_k\.k_oor|ot_s81sl_sflt\.q|\$dff\.Q|"
     r"dsdv_hostb_seqhost_mux\.(t_mf|hostb_fault|hb_job_active)|"
     r"dsdv_hostb_stage_hbc\.(fault|hbc_fault|return_fault|arm_mask|arm_commit|context_valid)|"
     r"ot_s81_mu72_lnland\.k_st)$", "needs_lane", FAULT),
    (r"^col_h(9|10)_l4_lp_r0\.xo_o0$", "dead", "D-XEND: x pass-through output of the row-end frame (frame chain end, "
     "no consumer): row-end variant without xo (both ends)"),
    (r"^dsdv_hostb_stage_hbc\.(boot_edge|receiver_edge)$", "dead", "D-HBCDBG: 48-b epoch-edge counters exported for the "
     "native census only, no die consumer: drop the ports"),
    (r"^ot_s81sl_lep_mu_a\.mu_rt$", "dead", "D-MURT: MU route-return tag of the TP-end leps (s_0S/s_7S); only s_0N/s_7N "
     "carry h windows (LINK5) -> mu_rt_0n/7n lanes; tie-free drop of the port in the TP-end lep variant"),
    (r"^ot_s81sl_(xg|xgt_xo)\.xw_v$", "dead", "D-XWV: xw valid of the slice x-gather whose xw_d consumer uses its own "
     "framing; drop (both ends)"),
    (r"^\$(logic_not|not)\.Y$", "dead", "Yosys glue of the iq slice fault flop (follows D-GLUE)"),
]
LANE_RULES = [
    (r"^(tl|ca|cb)__", "planned", "H4 tree lanes: as-built has no endpoint; bound once GEN takes the H4 RTL"),
    (r"^coll__(lk_(EN2|EN3|WS2|WS3)__|s_(7N|0S)_LP__lk_(EN2|EN3|WS2|WS3))", "planned",
     "XDIE reserve pair B: RTL owed (s_7N / s_0S lep pair-B coll ports, lanes/S81.md XDIE)"),
    (r"^sid_(s_7N_C__seqhost|seqhost__s_7S_C)$", "needs_lane", FAULT + ": seqhost sidr_o/sidr_i have no RTL"),
    (r"^vid_", "needs_lane", FAULT + ": svc id/fault ring has no RTL endpoint at all"),
]


def cls(rules, key):
    for rx, c, why in rules:
        if re.search(rx, key):
            return c, why
    return "UNCLASSIFIED", ""


items = []
for r in raw["inputs"]:
    key = f"{r['module']}.{r['port']}"
    c, why = cls(RULES_IN, key)
    if r["kind"] == "tied" and c not in ("dead", "strap"):
        c = "tied"
    items.append(dict(dir="in", src_kind=r["kind"], pin=r["pin"], module=r["module"], port=r["port"], part=r["part"],
                      type=r["type"], bits=r["bits"], cls=c, fix=why, asbuilt=r["src"][:2]))
for r in raw["outputs"]:
    key = f"{r['module']}.{r['port']}"
    c, why = cls(RULES_OUT, key)
    items.append(dict(dir="out", src_kind=r["kind"], pin=r["pin"], module=r["module"], port=r["port"], part=r["part"],
                      type=r["type"], bits=r["bits"], cls=c, fix=why, asbuilt=r["top"][:2]))
lanes = []
lw = {}
pw = {p["id"]: p["width"] for p in plan["ports"]}
for L in plan["lanes"]:
    lw[L["id"]] = pw.get(L["ports"][0], 0) if L.get("ports") else 0
for lid in raw["unused_lanes"]:
    c, why = cls(LANE_RULES, lid)
    lanes.append(dict(lane=lid, bits=lw.get(lid), cls=c, fix=why))
T = plan["partition_types"]
hc_no_conns = [tn for tn, t in T.items() if t.get("hard_cores") and tn not in cc]
summ = defaultdict(lambda: dict(ports=0, bits=0))
for it in items:
    if it["cls"] == "ok":
        continue
    s = summ[(it["dir"], it["cls"])]
    s["ports"] += 1
    s["bits"] += it["bits"]
for L in lanes:
    s = summ[("lane", L["cls"])]
    s["ports"] += 1
    s["bits"] += L["bits"] or 0
out = dict(
    schema="opentallas.s81.portbind_audit.v1",
    note="S81/PORTBIND 10-25: every leaf port bit of the S81 die that plan v4.8 does not carry, from tools/die_plan/bind.py "
         "(Binder map+analyse+buses) on plan claude/s81-h4-1024r@48590fb90f with the BINDER4 as-built die (cap30 dv_die, "
         "cached elab) and asbuilt_s81_off + map from mk_map_s81.py on the v4.8 instance_map (bk_col retired -> transport)",
    proof=raw["proof"], load_bits=raw["load_bits"],
    summary={f"{d}:{c}": v for (d, c), v in sorted(summ.items())},
    items=sorted(items, key=lambda x: (x["cls"], x["module"], x["pin"])),
    unused_plan_lanes=lanes,
    empty_partitions=raw["empty"],
    core_conns_missing_types=dict(n=len(hc_no_conns), types=hc_no_conns,
                                  note="hard-core types without core_conns.json entries: their hard-core pin binding "
                                       "is not checkable from the plan (kit wrappers bind by name); INFO, not a gap "
                                       "class of this audit"),
)
json.dump(out, open(sys.argv[4], "w"), indent=1)
for k, v in out["summary"].items():
    print(k, v)
print("UNCLASSIFIED", [i["pin"] for i in items if i["cls"] == "UNCLASSIFIED"],
      [L["lane"] for L in lanes if L["cls"] == "UNCLASSIFIED"])
