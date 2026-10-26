"""TYPE-REDUCE-2/KVQC census: one row per ownership.py plan_items design of qwen_kvsys + qwen_compute (origin/main).
reason = FIRST cause keeping the design distinct from another design of the same logic; after_class = the design it
collapses into after fixing (2) ID constants -> strap_* pins and (3) per-slot pins -> one pin table per template only."""
import csv, sys, json
before = {}
for f in sys.argv[2:]:
    for r in csv.reader(open(f), delimiter="\t"):
        before[(r[0], r[1])] = r
C = {}   # (die, item) -> (reason, after_class, note)
def s(die, item, reason, after=None, note=""):
    C[(die, item)] = (reason, after or item, note)
KV, QC = "qwen_kvsys", "qwen_compute"
# ---------------- KV types
s(KV, "kv3_hg_v1", "different-logic", note="hg family base (24 rows); kv3_hg / kv3_hg_v3 are its chain ends")
s(KV, "kv3_hg", "edge", note="chain-head hg: *_head astk owner/ep modules + u_id_row ot_dp_id_src (chain-derived row ID source, already not a strap)")
s(KV, "kv3_hg_v3", "edge", note="chain-tail hg: no u_fch/u_id_next, fewer astk Q_N buses")
s(KV, "kv3_hgi_v1", "different-logic", note="hgi family base (12)")
for v, n in (("kv3_hgi", 7), ("kv3_hgi_v2", 4), ("kv3_hgi_v3", 29), ("kv3_hgi_v4", 23), ("kv3_hgi_v5", 26), ("kv3_hgi_v6", 29), ("kv3_hgi_v7", 23), ("kv3_hgi_v8", 27)):
    s(KV, v, "ft-population", note=f"identical to kv3_hgi_v1 except ft_slots (+{n} slots); PROPOSAL (not in delta): uniform FT lane bank -> kv3_hgi_v1, 9 -> 1")
for t in ("kv3_hroot", "kv3_hub_C", "kv3_hub_Ei", "kv3_hub_Eo", "kv3_hub_Wi", "kv3_hub_Wo", "kv3_sys_c"):
    s(KV, t, "different-logic", note="unique function")
s(KV, "kv3_io_cor", "different-logic", note="io corner base")
s(KV, "kv3_io_cor_v1", "edge", note="other corner: 9 fewer host/serdes buses + different ft_slots")
s(KV, "kv3_io_ft", "different-logic", note="io ft base")
s(KV, "kv3_io_ft_v1", "ft-population", note="ft_slots only (3 differ); PROPOSAL uniform FT bank -> kv3_io_ft")
s(KV, "kv3_pc_v1", "different-logic", note="pc family base (24)")
s(KV, "kv3_pc", "edge", note="chain head: qkd_kvs_pc_h_head_p core + qkd_kvs_grp_h_p + u_id_grp source (ID params PC=0/CFG_GROUP=4 single-valued, not a split cause)")
s(KV, "kv3_pc_v3", "edge", note="chain tail: qkd_host_pc_slice_die_head, no fch/o_prev chain")
s(KV, "kv3_phy_v1", "different-logic", note="phy family base (28)")
s(KV, "kv3_phy", "edge", note="+i_host_hbm_rst_n (reset entry row) and -1 ft slot")
s(KV, "kv3_pv_v2", "different-logic", note="pv family base")
for v in ("kv3_pv", "kv3_pv_v1", "kv3_pv_v3", "kv3_pv_v4", "kv3_pv_v5", "kv3_pv_v6", "kv3_pv_v7", "kv3_pv_v8", "kv3_pv_v12"):
    s(KV, v, "glue-by-position", note="row-position relay contents (pv__u_T*Q*_<lane>_r0 qkd_rlyi_258s), vport direction/width buses and ft_slots follow the row; KV-PLAN3F refused pv/v8 + v7/v12 merges (pin tables differ)")
s(KV, "kv3_sys_SD", "different-logic", note="serdes side W")
s(KV, "kv3_sys_SD_v1", "edge", note="E-side serdes: o_serdes_E_* + 522-b fdi vs W 523-b")
# ---------------- KV cores
s(KV, "kv3_head_eighth_e0", "different-logic", note="head front eighth: u_kt + g_front q/row/lt inputs, 1802 pins (vs 1358 even)")
s(KV, "kv3_head_eighth_e6", "different-logic", note="EVEN master (= e4 slot already, pin table identical); straps strap_hid/strap_bsel declared on main")
s(KV, "kv3_head_eighth_e2", "ID-constant", "kv3_head_eighth_e6",
  note="bsel constant + lane-numbered port names g_t_4/5,g_front_1 (vs e6 g_t_12/13,g_front_3); after names->lane-neutral + strap master the RTL is e6's; (3) e2 pin table -> e6 table R0: 891/1358 pins move, max 345.8 um, p50 14.4, 269 pins N->S face -> needs PATH-KV floorplan call (heads 0-3 on path)")
s(KV, "kv3_head_eighth_e1", "different-logic", note="ODD master base (544 pins)")
s(KV, "kv3_head_eighth_e3", "ID-constant", "kv3_head_eighth_e1",
  note="DELTA DONE (claude/type-reduce2-kv-1025): only .bsel 01 vs 00 + lane-numbered names (g_t_6/7 vs g_t_2/3) differ; pin table identical after the name map (0 pins move) -> master e1, strap_bsel 2'b01; RTL substitution proof IDENTICAL")
s(KV, "kv3_head_eighth_e5", "ID-constant", "kv3_head_eighth_e1",
  note="(2) DONE: odd master e5 (strap_bsel 2'b10) for {e5,e7}; (3) PROPOSAL e5 table -> e1 table: best orient MX: 544 pins move, max 212 um, 68 pins S->W face change -> (3) needs one face-consistent head table")
s(KV, "kv3_head_eighth_e7", "ID-constant", "kv3_head_eighth_e1",
  note="DELTA DONE: .bsel 11 + names g_t_14/15 -> master e5 (strap_bsel 2'b11), 0 pins move, RTL substitution proof IDENTICAL; e5-table -> e1-table is the (3) proposal as for e5")
s(KV, "qkd_ectlk_q0", "different-logic", note="ECTLK column cut of qkd_ectlk_reference (results/arch/kv_plan_1025/ectlk_columns): q0 carries the req/epoch side")
for q in (1, 2, 3):
    s(KV, f"qkd_ectlk_q{q}", "glue-by-position", note="column slice of one controller: port sets differ per column (rsp_data/si/t0 widths) -> not an ID constant")
for m in ("cdc_ch", "cdc_ci", "cdc_hi", "cdc_pc", "core_guard", "core_order", "core_peer", "core_prompt", "core_queue", "core_rx", "core_tx", "host_qm", "ingest_eng", "phy_adp", "phy_pad"):
    s(KV, f"qkd_hr_{m}", "different-logic", note="hroot leaf core, unique function")
s(KV, "qkd_kvs_ctl", "different-logic"); s(KV, "qkd_ahub", "different-logic")
s(KV, "qkd_kvs_pc", "different-logic", note="124 inst, one table (R0/MY)")
s(KV, "qkd_kvs_pc_h_head_p", "edge", note="chain-head pc variant (head_p cut, 2987 vs 4129 pins)")
s(KV, "kv3_astk", "different-logic", note="already ONE strap master (strap_corner, orients R0/MX/MY/R180)")
s(KV, "kv3_pv_pair", "different-logic", note="one table R0/MX")
s(KV, "ot_qwen_tp8_pv_join_t", "different-logic")
# ---------------- QC types
s(QC, "cbf_q00", "different-logic", note="A0 CB tile type base (4x qfd_tile_nk_a0c)")
s(QC, "cbf_q00_s2", "ft-population", note="= cbf_q00 + 5 ft_slots")
s(QC, "cbf_q01", "outline", note="2617.92 vs 2609.28 um tall + bus set (row position)")
s(QC, "cbf_q01_s2", "ft-population", note="= cbf_q01 + 5 ft_slots")
s(QC, "cbf_q11", "outline", note="vs cbf_q00; vs cbf_q01 bus set/edge")
s(QC, "cbn_q00", "ft-population", note="vs cbf_q00: +1 ft slot, own station glue, 3 bus windows")
s(QC, "cbn_q01", "ft-population", note="vs cbf_q01")
s(QC, "cbn_q11", "ft-population", note="vs cbf_q11")
s(QC, "cbx_q10", "different-logic", note="carries qfd_tile_nl_a0c (u_t30)")
s(QC, "coll_ft", "different-logic", note="coll FT base (3)")
for v in ("coll_ftc", "coll_ftm", "coll_ftn"):
    s(QC, v, "ft-population", note="ft_slots differ, outline follows the FT count" + ("; PATH type (coll_f4), record only" if v == "coll_ftc" else ""))
for t in ("coll_core", "coll_n", "coll_ucie", "glue", "native59", "tt_ctlm", "phy_ucie_kv", "sle_ctl", "phy_serdes"):
    s(QC, t, "different-logic", note="PATH type" if t in ("glue", "native59", "phy_ucie_kv", "sle_ctl") else "")
s(QC, "coll_s", "edge", note="vs coll_n: S side, +7 buses, outline 803.52")
s(QC, "phy_serdes_b", "pin-positions", note="corner serdes: all buses on E face vs N (same PHY); R90 not a legal plan orient -> stays")
for side in ("sle", "slw"):
    for r in ("fe", "fw", "sc", "stm", "st_a", "st_b"):
        for v in ("v1", "v2", "v3"):
            pass
# slice row types: family base = *_v1 (W side slw_* is the PATH side)
fam = {}
for (die, item) in before:
    if die == QC and item.startswith(("sle_", "slw_")):
        fam.setdefault(item.rsplit("_v", 1)[0] if "_v" in item[-3:] else item, []).append(item)
for f, ks in fam.items():
    for k in ks:
        if (QC, k) in C: continue
        path = k.startswith("slw_")
        if k.endswith("_v1") or "_v" not in k[-3:]:
            if f in ("sle_hc0", "sle_hc1", "sle_hc2", "slw_hc0", "slw_hc1", "slw_hc2", "slw_hc3"):
                s(QC, k, "different-logic", note=("PATH slice W5; " if path else "") + "hc row: own leaf set (slw has x-head leaves; hc0/1/2/3 differ in contents/outline)")
            elif f.endswith(("su_l0", "su_l1")):
                s(QC, k, "glue-by-position" if f.startswith("sle") else "different-logic",
                  note=("PATH slice W5; " if path else "") + ("vs slw twin: own station glue + ft_slots" if f.startswith("sle") else "SU lane-group type (lanes 0-3 / 4-7)"))
            elif f.endswith("su_c"):
                s(QC, k, "different-logic", note=("PATH slice W5; " if path else "") + ("crh_rp1 replica cores (vs sle crh)" if path else "crh cores (vs slw crh_rp1)"))
            else:
                s(QC, k, "different-logic" if path else "edge", note=("PATH slice W5 family base" if path else "E-side twin of slw_*: direction-named buses (x_fw/x_fe) mirrored, own station glue"))
        else:
            s(QC, k, "ft-population", note=("PATH slice family (record only); " if path else "") + "variant = bus/ft_slot set of the slice position (station glue u_pstn follows the type)")
# ---------------- QC cores
s(QC, "qfd_tile_nk_a0c", "different-logic", note="720 inst, one table (R0/MY)")
s(QC, "qfd_tile_nl_a0c", "different-logic")
for m in ("qfd_dv_s8x_btab", "qfd_dv_s8x_vmr", "qfd_dv_s5_su8_rst3", "qfd_dv_s8x_crh", "qfd_dv_s8x_prog"):
    s(QC, m, "different-logic", note="PATH core (su_c)" if m != "qfd_dv_s8x_crh" else "E-side su_c core")
s(QC, "qfd_dv_s8_crh_rp1", "different-logic", note="PATH core C2: structural replica variant of crh")
lanes = {"qfd_qc_su_lane_w_f8b831e916b0": "lanes 4+5 (one table already, 24 inst)"}
for (die, item) in before:
    if die == QC and item.startswith("qfd_qc_su_lane_w_") and (die, item) not in C:
        L = json.load(open("/home/ubuntu/scratch/type-reduce2/kvqc/lane_sha.json")).get(item.rsplit("_", 1)[1], [])
        C[(die, item)] = ("pin-positions", "qfd_qc_su_lane_w", "PATH core C6 (NEEDS-KIT). per-slot pin table; vs master = lane0 table: " + "; ".join(L) +
                          ". Also port widths differ per slot (c_o 247/219, sc_o 10/9/1): one master needs the superset port list")
for a in ("st_b_v2", "st_a_v2", "hc0", "hc1", "hc2", "st_b_v1", "st_a_v1"):
    for side in ("sle_", "slw_"):
        k = (QC, side + a)
        if k in C:
            C[k] = ("glue-by-position", side + a, ("PATH slice W5; " if side == "slw_" else "") +
                    "G0 near-duplicate of its sle/slw twin (same outline/buses/slots) but bound reset relay tree enters from the opposite face (W IN on E face, E IN on W face); merge deferred by PLAN-DELTA/QC README (changes PATH reset outs or release > S+130; st_b R8 pads)")
out = open(sys.argv[1], "w")
out.write("die\titem\tkind\treplicas\treason\tafter_class\tnote\n")
miss = []
for (die, item), r in sorted(before.items()):
    if (die, item) not in C: miss.append(item); continue
    reason, after, note = C[(die, item)]
    out.write("\t".join([die, item, r[2], r[3], reason, after, note]) + "\n")
print("rows", len(before) - len(miss), "missing", miss, file=sys.stderr)
