#!/usr/bin/env python3
"""Hand annotations (owner / live job / blocker) for the 55 C18 NO-VIEW modules, from OWNERS.tsv (19:52 tick),
docker ps + ot-run clients on intel1/intel2/epyc2 (20:0x), queue.tsv, lane tails (HBM-CORES/HBM-KITS/HBM-CORE-LAT/CODEX).
Writes annot.json; preflight verdicts are merged from MERGED (merge_gen.py output)."""
import json, sys
merged = json.load(open(sys.argv[1]))
PF = "PREFLIGHT_FAIL (generic: gen_core_kit_hbm.py writes no freeze pins_canon_sha256 [GATE-PINS-2] + C18 has no master-plan slice with in-core island pushdown [12.2a1])"
A = {}
def s(m, **k): A.setdefault(m, {}).update(k)
# live / owned
s("ot_hbm_hc_root_static__tailx_sk_steady", owner="CODEX", action="OWNED-LIVE CODEX",
  live="intel2 docker hbmcore-steady_-3743475 (codex-hbm-sk-closure/steady, LEC ABC active)",
  note="Codex sk CE closure; R7 ENTRY_NOT_UNIQUE; CE kits via tools/hbm_b2/sk_ce_kit.py (land1-cap3), P&R HOLD on OWNER CE timing contract")
s("ot_hbm_idx_topk_link_static", owner="CODEX", action="OWNED-LIVE CODEX",
  live="intel2 docker hbmcore-ot_hbm_idx_topk_link_static_36b3f0c7a4d0_-3427450 (path-hbm-cores/topk_tree/kits_r2, LEC ~20 h)",
  note="live job is on the U6b pin table 36b3f0c7a4d0; C18 table is ae6a5e94c493 -> that job's view is stale for C18")
# C18-generated, owners of the residual blockers
own = {
 "hnx_fused_lane": ("HBM-CORES/CODEX (MU fused template)", "BLOCKED NO_RECIPE", "no recipe for the C18 view; R7 ENTRY_NOT_UNIQUE (entry now unique in C18)"),
 "ot_hnx_fused_tnode": ("HBM-CORES/CODEX (MU fused template)", "BLOCKED NO_RECIPE", "no recipe; R7 ENTRY_NOT_UNIQUE"),
 "hnx_rp3lp3h_n": ("CODEX (native four-hard SM profile) + HBM-PLAN (child placements)", "BLOCKED OVER_CAP_400K", "kit generates but recipe is flat: R8 synth 806,841 cells > 400k OpenROAD cap (Codex 08:45/14:12, UNCHECKED here); needs native hard-child composition"),
 "hnx_rp3lp3h_s": ("CODEX (native four-hard SM profile) + HBM-PLAN (child placements)", "BLOCKED OVER_CAP_400K", "flat R8 synth 785,258 cells > 400k (Codex, UNCHECKED here)"),
 "ot_hbm_hc_bank128_pair_core": ("CODEX (hc128_native_kit / HC alpha masters)", "BLOCKED NO_RECIPE", "2 pin tables (MULTI_TABLE c64111/c87c2b); HC kits only via tools/hbm_b2/hc128_native_kit.py with TRIAL masters"),
 "ot_hbm_hc_bank128_pair_first_core": ("CODEX (hc128_native_kit / HC alpha)", "BLOCKED NO_RECIPE", "Codex: alpha source EQ27333, kit /work/PROVENANCE missing, no rerun until packaging/final pins"),
 "ot_hbm_hc_subtree32_core": ("CODEX (hc128_native_kit / HC alpha)", "BLOCKED NO_RECIPE", "Codex: alpha source EQ18912; R12 UNPROVEN63 diag"),
 "ot_hbm_hc_root_static__hcp_sys1": ("CODEX/HBM-CORES (HCP CMD_RST + LEC)", None, "R7 excluded (LEC NEQ 1075 known, CMD_RST); Codex HCP cleanup parked; OWNERS KIT-PLACED (old table eeab18)"),
 "ot_hbm_hc_root_static__tailx_sk_step0": ("CODEX (sk_ce_kit.py CE source)", "BLOCKED NO_RECIPE", "CE kits only via tools/hbm_b2/sk_ce_kit.py --ce-shell-contract land1-cap3; P&R HOLD on OWNER CE7/MCP timing contract"),
 "ot_hbm_idx_score_quarter_static__tailx__v36d446": ("CODEX (native quarter profile)", "BLOCKED NO_RECIPE", "also PENDING-DELTA TR2-HBM (quarter_static) -> autopilot WAIT-PLAN-DELTA"),
 "ot_hbm_idx_score_quarter_static__tailx__v3fcb6a": ("CODEX (native quarter profile)", "BLOCKED NO_RECIPE", "also PENDING-DELTA TR2-HBM"),
 "ot_hbm_idx_selector_static_sel": ("HBM-CORES", None, "R7 synth 323,344 cells (CHECKED synth_stat), place exit 0 on epyc2"),
 "ot_hbm_su_programme_pslice_c5": ("HBM-CORE-LAT (pslice_mp.py explicit macro placement)", None, "100 SRAMs: auto MPL-0003 in R6; R7 k2mp used explicit plan macro placement; preflight also needs MACRO_PLACEMENT_TCL"),
 "ot_hbm_su_static_pgslice_lg__lane_exp0": ("HBM-PLAN (exp family macro placement)", "BLOCKED MACRO_PLACEMENT", "exp_lane.json family macro placement missing (no B2n_inputs/exp_lane.json anywhere on intel2); PENDING-DELTA TR2-HBM"),
 "ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691": ("HBM-CORES (pgslice canon recipe) ", "BLOCKED NO_RECIPE", "R7 ENTRY_NOT_UNIQUE; PENDING-DELTA TR2-HBM"),
 "ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77": ("HBM-CORES (pgslice canon recipe)", "BLOCKED NO_RECIPE", "R7 ENTRY_NOT_UNIQUE; PENDING-DELTA TR2-HBM"),
 "ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526": ("HBM-CORES (pgslice canon recipe)", "BLOCKED NO_RECIPE", "R7 ENTRY_NOT_UNIQUE; PENDING-DELTA TR2-HBM"),
 "ot_hbm_su_static_pgslice_lg__lanes8_11": ("HBM-CORES", None, "R7 PORT_MISMATCH now resolved in C18 (generates); PENDING-DELTA TR2-HBM"),
 "ot_hbm_su_static_pgslice_lg__pretree": ("CODEX (pretree CTS staged, codex-hbm-cores-0815/pretree_cts_1011)", None, "outline changed 164.16x457.92 -> 164.16x241.92; PENDING-DELTA TR2-HBM"),
 "ot_hbm_su_static_pgslice_lg__side_rest": ("HBM-CORES", None, "PENDING-DELTA TR2-HBM"),
 "ot_hbm_su_static_pgslice_lg__side_softplus": ("HBM-CORES", None, "PENDING-DELTA TR2-HBM"),
 "ot_hbm_svc_sm_group_rel_id": ("HBM-CORES", None, "R7 PORT_MISMATCH resolved in C18"),
 "ot_hbm_svc_sm_xcal_rel_t": ("HBM-CORE-LAT", None, "R7 excluded (re-pack outline pending); C18 outline 241.92x224.64; OWNERS KIT-PLACED (old tables)"),
 "ot_hfd_coll_q2_hard_v8g__reduce": ("HBM-CORES (hand wrapper)", "BLOCKED PORT_MISMATCH", "hand wrapper ports != plan pins (clk vs clk_reduce): wrapper/plan clock-pin naming"),
 "ot_hfd_coll_q2_hard_v8g__ring_ag": ("HBM-CORES (hand wrapper)", "BLOCKED PORT_MISMATCH", "hand wrapper ports != plan pins (clk vs clk_ring)"),
 "ot_hfd_coll_q2n2_body_core": ("HBM-CORES", None, "R8 superset-face __E pin copies blocker noted; R7 NO_RECIPE now resolved (recipes_b2)"),
 "ot_hfd_coll_q3_edge_core": ("HBM-PLAN (D-HBM-C16) / CODEX q3sync build_kit", "BLOCKED NO_RECIPE", "q3 kits via q3sync_kits/build_kit.py; PENDING-DELTA D-HBM-C16 (q3 edge outline 190.08->216)"),
 "ot_hgi_coll_tkm_tp192_tile_core__idpin__strap": ("PATH-HBM (tkm)", None, "old v8 rows withdrawn (epyc1)"),
 "ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap": ("PATH-HBM (tkm)", None, "R8 ASK: terminal wrapper ties tile_up_in=0 needs ruling (no-ties rule)"),
 "ot_hgi_qw_dec": ("HBM-CORES", None, "R7 PORT_MISMATCH resolved in C18"),
 "ot_hgi_sfu_core_split3__opstore_b": ("HBM-CORES", None, "R7 synth 210,750 cells, LEC EQ 34853 (Codex 08:35); PENDING-DELTA TR2-HBM (split3)"),
 "ot_hgi_sfu_programme_store_r10": ("HBM-CORES", None, "R7 excluded (GPL-0305 diverged -> new outline first); C18 outline 574.56x738.72"),
 "ot_hgi_sfu_split3_lane_core__idpin": ("HBM-CORES", None, "R7 NO_RECIPE resolved (recipes_b2)"),
 "ot_pdie_serdes": ("CODEX / PATH-HBM", None, "old GP run (50 h, nonconvergent overflow .34) gone; Codex: native successor model needed before a new job"),
}
for m, (o, act, note) in own.items():
    g = merged.get(m) or []
    pf = [x.get("preflight") for x in g if x.get("kit")]
    pfv = ",".join((p or {}).get("verdict", "NOT-RUN") for p in pf)
    issues = sorted({i.split(":")[0] for p in pf if p for i in p["issues"]})
    s(m, owner=o, note=note, preflight=(pfv + (" [" + ";".join(issues) + "]" if issues else "")) if pf else "")
    if act:
        s(m, action=f"{act} ({o})")
    elif pf and all(p and p["verdict"] == "PASS" for p in pf):
        s(m, action="PREFLIGHT-PASS (enqueue pending)")
    else:
        s(m, action=f"BLOCKED PREFLIGHT ({'FLOW gen_core_kit_hbm pins_canon + HBM-PLAN master slices; ' + o})")
json.dump(A, open(sys.argv[2], "w"), indent=1)
print(len(A))
