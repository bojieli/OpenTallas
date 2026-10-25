# Lane HBM-KITS

2026-10-25 06:20 PDT HBM-KITS (sub-agent of lane HBM): census of the 210 B2n hard-core modules (OWNERS hbm/core: 208 NEEDS-KIT + 2 GEOM-REQ),
branch claude/hbm-kits-census-1025@919adf3e6c results/hbm_kits_1025/census.tsv (+census.py, fleet_kits_probe_1025.tsv).
Plan B2n die_plan sha f710e18c5dd5 = views_b2n.json (280 views). design = RTL top+params + straps + outline + pin table
(names+xy); unify = RTL top + outline (same logic, differs only by strap constants / plan pin placement).
Result: 210 modules / 280 views -> 226 DISTINCT designs today, 66 unify groups. Prior kits on the current plan stop at synth
(1_2_yosys; the face_guard-FAIL kits were deleted); none SIGNED except lanes outside this census (argmax, gq_land ROUTING).

| family (parent) | distinct designs | replicas covered (modules/views/placed) | state | blocker | next |
|---|---|---|---|---|---|
| IDXS idx_score_quarter hcol h0/h1 + tail | 14 (3 unify) | 66/66/132 | QUEUED B1 (CTS live) | none (B2n grew outline 1.45x vs 86% overfull; HBM-FACE guard PASS) | B1 GEOM REQ -> autopilot finish; then plan delta: one pin table per half -> 3 cores |
| TKM coll_tkm_m_tp192 tile/root | 33 (2 unify) | 33/33/33 | NEEDS-KIT | straps tile_tid per tile (6b) make 32 tiles 32 netlists; 26 tiles already share pin xy | plan/RTL delta: tile_tid -> ID input pins tied at parent => 1 tile core (x32) + root; then B2 |
| SFU sfu_core_split3 lane/ctl/opstore_a/b | 19 (4 unify) | 19/19/38 | NEEDS-KIT | straps map_lane_j per lane; 9 lane pin tables | same strap->ID-pin delta => 1 lane core (x16) + 3; B2 |
| PGS pgslice_lg pv6 exp lanes | 30 (+lane_full 1) | 15 mods/31 views/~64 | blocked | ALAT4 exp flat synth keeps 1 of 6 SRAMs (face shell ties ld/ld_bank/ld_c0, lane_id0 -> rd_addr X; CODEX 06:20) + lane_lane_id straps + MULTI_TABLE (2 pin tables per module) | structural RTL/shell fix (owner HBM-EXP/CODEX), then strap->ID pin => 1-2 cores; do not kit |
| PGS pgslice_lg pv6/pv14 lanes4, pretree, side_rest, side_softplus | 25 (4 unify) | 16 mods/25 views/~50 | NEEDS-KIT | MULTI_TABLE: same module, 2 pin tables; 21 pg_lanes4 views across 2 outlines (440.64x457.92, 760.32x725.76) | plan delta: one outline + pin table per lanes4 => 2 cores; B3 |
| HC hc_root_static (hcp_sys1, tail rest/sk_steady/sk_step0) | 7 (4 unify) | 7/7/7 | NEEDS-KIT | tail0/tail1 rest share pins; sk_* differ by plan pins | B2 (tail0/1 unify by plan pins => 4 cores) |
| HCB hc_bankq / bankq0 / bankq_ft / bankq_term | 22 (8 unify) | 12 mods/22 views/44 | NEEDS-KIT | MULTI_TABLE; bankq0/term 1 NO_RECIPE each; bankq_ft prior routes FAIL (DRT 25 GB, hold) | B3 after plan pin unification; bankq_ft structural review first |
| SVC svc_pc_ctrl_leaf_cfg_h9b | 10 (1 unify) | 1/10/20 | NEEDS-KIT | MULTI_TABLE (10 pin tables, one module); prior routed NOT SIGNED | plan: one pin table => 1 core; B2 |
| VM/SMSVC multi-table singles (vms_bank_native_q0_faces x8, vmdel_lane_n x5, sm_group_rel_id x4, xcal_rel_t x4, bfqg x4, kshare x4, bdring x2, pegress x2, ep_static x2, aq_tree13 x2) | 37 (10 unify) | 10/37/74 | NEEDS-KIT | MULTI_TABLE (one module, several pin tables) | plan pin unification => 10 cores; B3 |
| COLL q2_hard_v8g body/reduce/ring_ag, gq_issue, inj_idx_join_rg | 5 | 5/5/10 | NEEDS-KIT | none known | B2 |
| singles w/ recipe (qhub, idx qctl/rootctl/selector/topk_link, serdes, host_cp_rxs, cfg_collar, dma_back, sfustore_hw, programme_store_r10, wb_kport_q) | 13 | 13/13/~17 | NEEDS-KIT | topk_link synth 50 GB peak (needs 128 GB); serdes 394k cells (near 400k cap) | B2 |
| singles NO_RECIPE (idx_query, vm_query_n12, qw_dec, sm_vm_wr_q_t_lanes4, xload_ctlx, su pslice_c5/cxport_ij_q/qcore_r13, vm_calendar_f20, vms_glue_nw_t) | 10 | 10/10/20 | blocked | NO_RECIPE in views_b2n (no synth recipe for the B2n module) | recipe import (HBM-CORES) |
| SM hnx_rp3lp3h_n/s | 2 | 2/2/256 | NEEDS-KIT (other lane) | HNX-SM4P hardened halves (physical/hbm_next/sm4) | owner HNX/SM lane |
| argmax_static_sw_vm_r2, gq_land | 2 | 2/2/3 | GEOM-REQ / ROUTING (other lanes) | CLOCK-RESET/HBM-CORES own | skip |

Batches: B1 = IDXS (14 designs cover 66 modules / 132 placements; no blocker). B2 = TKM/SFU/HC-root/COLL/singles-with-recipe after
the strap->ID-pin + one-pin-table plan delta (posted to COORD-REVIEW-QUEUE as one HBM delta, not ad hoc). B3 = MULTI_TABLE
families after plan pin unification. Blocked: PGS exp (ALAT4 SRAM loss), NO_RECIPE x10.
Owner-rule note (replicas hardened once): with strap->ID pins + one pin table per family the 226 designs collapse to ~66.
2026-10-25 06:20 PDT HBM-KITS: B1 kits gen'd from claude/hbm-kits-1025r@aea2ae39b3 (F2/F1/F4 + pre-DRT FF gate) -> epyc1:/srv/opentallas-scratch2/claude/hbm-kits-1025/batch1/kits (14, gen rc0);
  CTS via ot-run 32 GB/8 thr on epyc3/intel1/intel2/epyc2 runs/<kit> (launcher PIDs epyc1 batch1/launch_pids.txt), started 06:20.
2026-10-25 06:32 PDT HBM-KITS: CENSUS READY claude/hbm-kits-census-1025@919adf3e6c (results/hbm_kits_1025/census.tsv); batch1 = IDXS idx_score_quarter (14 designs / 66 modules, kitted + CTS live; tails LEC NOT EQUIVALENT, investigating); batch2 = TKM tile/root, SFU lane/ctl/opstore, HC root (hcp_sys1 + tail rest/sk_steady/sk_step0), COLL q2 body/reduce/ring_ag + gq_issue + inj_idx_join_rg, singles with recipe (qhub, idx qctl/rootctl/selector/topk_link, serdes, host_cp_rxs, cfg_collar, dma_back, sfustore_hw, programme_store_r10, wb_kport_q); NOTE TKM/SFU straps -> ID-pin plan delta would cut 48 kits to 2; B3 = MULTI_TABLE families (svc_pc h9b, VM/SMSVC singles, HCB bankq*, PGS lanes4/pretree/side); blocked = PGS exp (ALAT4 SRAM loss), NO_RECIPE x10.
2026-10-25 06:47 PDT HBM: COORD TYPE-REDUCE order relayed: per-piece kitting STOPPED; kits keyed by RTL master (66) + params + pin template; batch1 idx_score_quarter cut to one kit per master (3) with redundant runs/data deleted; no TKM/SFU kits until the OWNER strap ruling; q_sm0-3 merge goes into the B2o delta.
2026-10-25 06:49 PDT HBM-KITS-B2: GENERATOR BUG (fixed on claude/hbm-kits-b2-1025@282321554f, base aea2ae39b3): gen_core_kit_hbm.py kits never set SYNTH_CANONICALIZE_TCL=ot_keep_regs.tcl,
  so (* keep *) replicated regs (ot_rst_relay region copies) are opt_merged -> LEC NOT EQUIVALENT (sfustore_hw relay_q[1..3] removed, 97 SRAM ce points) + one reset flop for N regions (decision 2).
  Sibling/batch1: check whether the idx tails LEC fail is the same (regen with 282321554f). B2 per COORD order: tail1_sk_steady/tail1_sk_step0 runs stopped (exact container) + data deleted (tail0 = the core).
2026-10-25 06:51 PDT FLOW-CANARY -> HBM-KITS/HBM-CORES: main's physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py writes NO LAYER_PARASITICS_FILE/SET_RC_TCL (stock setRC at place/CTS/GRT) - your waves use claude/hbm-kits-1025r which has it: please get that to main (the HBM canary builds from main). HBM canary hfd_hgi_vm_calendar_f20 on main 202a50a59: SELRANGE PASS, LEC EQUIVALENT (3484 cp), face_guard FAIL (shared active/fault/tgt_fault, as the 10-24 reference) and run_kit_hbm.sh only RECORDS face_guard and continues; no pre-route FF-hold gate on main. Run epyc1:/srv/opentallas-scratch2/claude/flow-canary/runs/hbm_202a50a59_1025_0648.
