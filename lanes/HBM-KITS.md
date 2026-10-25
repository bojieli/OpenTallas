# Lane HBM-KITS

2026-10-25 06:20 PDT HBM-KITS (sub-agent of lane HBM): census of the 210 B2n hard-core modules (OWNERS hbm/core: 208 NEEDS-KIT + 2 GEOM-REQ),
branch claude/hbm-kits-census-1025@919adf3e6c results/hbm_kits_1025/census.tsv (+census.py, fleet_kits_probe_1025.tsv).
Plan B2n die_plan sha f710e18c5dd5 = views_b2n.json (280 views). design = RTL top+params + straps + outline + pin table
(names+xy); unify = RTL top + outline (same logic, differs only by strap constants / plan pin placement).
Result: 210 modules / 280 views -> 226 DISTINCT designs today, 66 unify groups. Prior kits on the current plan stop at synth
(1_2_yosys; the face_guard-FAIL kits were deleted); none SIGNED except lanes outside this census (argmax, gq_land ROUTING).

TABLE RE-KEYED BY RTL MASTER (COORD 06:5x, ref TYPE-REDUCE claude/type-reduce-1025@befcf3f66): census_masters.tsv on
claude/hbm-kits-census-1025@c725552671 = 63 rtl_top masters (TYPE-REDUCE counts 66: it splits hcp_lanes into 3 interface classes).
Rule: ONE kit per (master, pin template); replicas reuse it. "templates" = distinct pin xy tables today (the plan delta owed).

| family | masters (templates today) | replicas (modules/views/placed) | state | blocker | next |
|---|---|---|---|---|---|
| IDXS hcol HALF0 / HALF1 / tail_native | 3 (6+6+2) | 66/66/132 | QUEUED B1: 2 CTS kits live (h0 r0c0_k1h0, h1 r0c0_k0h1, both template 59bebf732a32 = the 18-replica table) | tail: LEC NOT EQUIVALENT 36/8711 points (FP32 adder u_a err[1]/rd[27]/rd[55], same signature as LEC lane fd3_et) | plan delta: 1 template per half; tail waits LEC fix |
| TKM tile / root | 2 (4 / 1) | 33/33/33 | NEEDS-KIT (hold) | tile_tid straps x32 | straps -> driven IDs (TYPE-REDUCE R7), then 1-2 tile kits |
| SFU lane / ctl / opstore_a / opstore_b | 4 (8 lane) | 19/19/38 | NEEDS-KIT (hold) | map_lane_j straps x16 | strap delta, then 4 kits |
| PGS lane_exp / lane_full | 2 (10) | 16/30/60 | blocked | ALAT4 flat synth keeps 1/6 SRAMs (face shell ld ties, rd_addr X) + lane_id straps | structural RTL/shell fix first; do not kit |
| PGS lanes4 / pretree / side_rest / side_softplus | 4 (12+2+1+1) | 15/25/54 | NEEDS-KIT (hold) | lanes4: 2 outlines + 12 tables + straps | one outline + template, then 4-5 kits |
| HC root: hcp_sys1 / tail_rest / sk_steady / sk_step0 | 4 (1+1+2+2) | 7/7/7 | NEEDS-KIT | sk_* 2 tables each | 4 kits after template delta (tail_rest ready now) |
| HCB bankq_lanes3 / hcp_lanes(+glue) | 2-4 (12 / 8) | 12/22/44 | NEEDS-KIT (hold) | 12/8 tables; NO_RECIPE x2; bankq_ft prior route FAIL | template delta + structural review |
| multi-table singles (svc_pc h9b 10, vms_bank 8, vmdel 5, group_rel 4, xcal 4, bfqg 4, kshare 4->3, bdring 2, pegress 2, ep_static 2, aq_tree13 2) | 11 (47) | 11/47/94 | NEEDS-KIT (hold) | MULTI_TABLE | one table each -> 11 kits |
| single-table masters with recipe (coll q2 body/reduce/ring_ag, gq_issue, inj_idx_join_rg, qhub, idx qctl/rootctl/selector/topk_link, serdes, host_cp_rxs, cfg_collar, dma_back, sfustore_hw, programme_store_r10, wb_kport_q) | 18 (18) | 18/18/~28 | NEEDS-KIT -> B2 | topk_link synth 50 GB (needs 128); serdes 394k cells | B2: 1 kit each |
| NO_RECIPE singles (idx_query, vm_query_n12, qw_dec, sm_vm_wr_q_t_lanes4, xload_ctlx, pslice_c5, cxport_ij_q, qcore_r13, vm_calendar_f20, vms_glue_nw_t) | 10 | 10/10/20 | blocked | NO_RECIPE | recipe import |
| SM hnx_rp3lp3h_n/s; argmax; gq_land | 4 | 4/4/259 | other lanes | - | skip |

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
2026-10-25 06:54 PDT HBM-KITS: COORD 06:5x STOP per-piece kitting done: stopped 10 redundant hcol CTS containers (exact names); deleted their runs + 2 failed tail runs (12 dirs, 8.2 GB) + 11 kits; deleted 695 superseded per-piece idx_score kit/run dirs fleet-wide (hbm-face kits_all/runs_synth/guards_raw, elem-hbm kits_b2l/b2n/tt/runs, codex-hbm placed_review; ~68.5 GB; 1 busy dir skipped on epyc3). Kept: batch1/kits {r0c0_k1h0, r0c0_k0h1, tail0} + 2 live CTS runs. Tail LEC evidence epyc1 batch1/evidence/.
