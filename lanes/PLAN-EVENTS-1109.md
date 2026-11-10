# PLAN-EVENTS-1109: every pending plan change, per die (PLAN-CENSUS-1, 2026-11-09 02:3x PST)

Read-only census. Nothing changed. Goal: each die makes ONE final plan switch, not a series.
Sources: COORD-REVIEW-QUEUE.md 11-08 00:00 to 11-09 02:27, _RESTART_1109.md, autopilot/kit_wave_stages.tsv (FAIL|PLAN rows), autopilot/kit_wave.json (current wave plans). There are no lanes/*TRANSPORT* files. The transport evidence is in the TRANSPORT-1/2/3, QC/S81/KV-TRANSPORT-FIX and DIE-HBM-94 queue posts.

State key: proposed = idea or spec only. composed = plan or bind built, not READY. READY = posted READY to KW-FIX. applied = in the wave config now.
Why key: FUNC = correctness/functional, TIM = timing, CLK = clock, PDN/GEOM = PDN or geometry, HOLD = hold/relay safety, CAP = cell cap.
**UNOWNED** = no live lane in _RESTART_1109 or later. **NOT FOLDED** = not in the die's planned switch, so it would force a second switch.

## Wave plans of record now (kit_wave.json, 02:26)
| die | plan | bind |
|---|---|---|
| S81 | kw34/wave_cg_frz_xrt plan_h2_2249.json (event e9eda32d41c) | none set |
| HEAD | kw23/prep_l48ui source_plan.json (l48ui) | none (no bind exists) |
| QC | qct11/wave plan_qc53v4nS 7e4789251637 (first switch, 22:05) | bind_v4nS |
| KV | kv-types-5/ev/plan_kvr8 | bind_kvr8 |
| HBM | die-hbm-93/plan_final2 (+ plan_final3 item_inputs for 11 types) | bind_lat_vJ |

---
## S81. Planned switch: TYPE-SAFE-5 recompose c72370dacfc365c1 (romq split base + relay event)
| # | change | why | owner | state | rides | types |
|---|---|---|---|---|---|---|
| S1 | Relay/type-safe event: 269 buses, 415 lanes, 750 stations, +1695 PIN CYCLES | HOLD | TYPE-SAFE-5 | composed. Event bind n_errors 1: col_h10_r0_p4__t1 clk_t29 radius 240.9 > 220 (ctap-v4 xy vs main). Baseline split-only bind crashed (native list). | S81 switch | 48 |
| S2 | xrt leaf norm_blocked: +1 on dn_s_1S_L1, 3N_L3, 3N_L4, 6N_L3, 7N_L3 (leaf bench 112/112) | FUNC | TYPE-SAFE-5 | composed (in febfb, carried into c72370) | S81 switch | c1x_C__t1, kv512_C__t1, c1x_C__t9, lepe_mu_C__t1 |
| S3 | romq split base (208 _hw/_he halves in the 26 col_h types). febfb was refused at 00:48 because it still had the old ROM. | GEOM | TYPE-SAFE-5 | on main; base of c72370 | S81 switch | 26 col_h |
| S4 | Carried by the v3b base: ctap v4, colh 14, ts1, main-only events, clock.tap_pair_affinity (block_ignore needed, otherwise 178 types re-key, 17 counted) | CLK | TYPE-SAFE-5 / KW-FIX-42 | composed | S81 switch | 178 re-key unless ignored |
| S5 | Switch actions: FORCE 21 rows whose bound RTL changed (kv_leaf t1/t3/t4/t5, station t45, svc_rs t*, pvso_entry). Hold 9 counted rows. NEW dsdv_gunit_l1f_bf (plan-keyed replica land form). | FUNC/GEOM | TYPE-SAFE-5 -> KW-FIX-42 | listed in TYPE-SAFE-4-S81-SWITCH.tsv; table must be redone for c72370 | S81 switch | 21 + 9 + 1 |
| S6 | Transport RTL already on main: 3a k_v/k_rdy pcr (930bc9c0c25), 3b RETURN_AGE 640->1536 (c50c0711850), 4b leaf compiler terms | FUNC | S81-TRANSPORT-FIX (done) | applied on main; reaches types only through the switch rebind (dsfd_ctrl_rg2/rg3, eng__t1) | S81 switch (rebind) | ctrl rg2/rg3, eng |
| S7 | **Leaf t42 early-core-tap event**: recompute clock.taps (kind core) from signed core means, margin 40 (+19 taps per leaf, clk_c5..c23); taps follow OT_MACRO_MOVES cores (vq, vsw) | CLK/TIM | DIE-S81-85 (spec, PARKED 02:24) -> TYPE-SAFE-5 | proposed. Default at 03:00 is "next S81 event after the switch". | **NOT FOLDED** (second switch unless TS5 carries it) | all ot_s81sl_leaf__t* that use those cores (t42, t16, t27 seen) |
| S8 | Leaf OT_MACRO_MOVES now kit-local item_env (t3, t7, t21, t46, t47, ...). S7 says moves must go into the plan for taps to follow. | GEOM/CLK | S81-TYPES-13 (ended) -> DIE-S81 successor | applied kit-local; plan form proposed | NOT FOLDED (goes with S7) | leaf batch (~15) |
| S9 | t6 / t24c648 station large misses: their one ECO is spent, so they go "to the structural switch" | HOLD | DIE-S81-85 | waits on S1 | S81 switch | slice_station t6, t24c648 |
| S10 | pin_cycle_deltas consumer map (compiler side of the +1695 PIN CYCLES: s81_latency, frame_schedule_asb, norm_q_plan) | FUNC | S81-SVC-9 took it 00:50. **UNOWNED now** (S81-SVC-9 is parked with no successor in RESTART 1109) | proposed | must land with the S81 switch | compiler |
| S11 | Transport OPEN classes: xo_o (no usable frame programme; 8/8 frames GAP), rebind_links on cbind3b, 89 OPEN buses in 40 classes (TRANSPORT-3 matrix) | FUNC | **UNOWNED** (TRANSPORT-3 and S81-SVC-8/9 parked) | open | none | unknown |
| S12 | svc_rs R5 (H8 slice + 2 head-jobs) | CAP/FUNC | S81-SVCRS-3 / S81-SVCC-1 / codex-svc | RTL + compiler; svc_rs rows in S5's FORCE list; flat-4M hold stays | S81 switch (FORCE rows) | svc_lo/hi_dsdv_svc_rs* |
| S13 | FAIL\|PLAN rows: KIT_TOPOLOGY_BIND_STALE c1x_C__t5, lepe_mu_LP__t2, lepe_nh_mus_LP__t1 (rebind); kv_leaf t1/3/4/5 LEC (FORCE in S5); gunit__t1 cell cap (PROVISIONAL children) | FUNC | KW-FIX-42 / TYPE-SAFE-5 | cleared by the switch rebind, except gunit__t1 | S81 switch | 8 |
Not plan (core-local): bksel P four-face re-pin pk2_vRP (pins.json only; pre-floor LEC UNPROVEN 204), t51 vE region bound (0 PIN CYCLES), gunit bf MW, eng vR1536.

## HEAD (s81_head). Planned switch: NONE
| # | change | why | owner | state | rides | types |
|---|---|---|---|---|---|---|
| H1 | CTL vH ds8 (.DSREP(8) rings, FSM hold margin) | TIM/HOLD | DIE-HEAD-91 | private form at GRT; "DO_NOT_COUNT until plan events bind" | **NOT FOLDED, no HEAD switch** | hd_ctl |
| H2 | HSPLIT: hd_host split e / w_hr (w_hr kit LEC KEEP FAIL 3/12059; e ds8 at GRT) | CAP/TIM | DIE-HEAD-91 | private forms | NOT FOLDED | hd_host -> hd_host_e/w |
| H3 | MESH: collector ds8 + Codex common-lane split codex/head-mesh-split-1108@2a97f030863 | CAP/TIM | DIE-HEAD-91 | routed, LEC running | NOT FOLDED | hd_mesh |
| H4 | LEP density-entry clock (85 clk_t entries; die must measure the 85-entry window; tapbal on main 422126acd12) | CLK | DIE-HEAD-91 | private re-form at CTS/GRT | NOT FOLDED | hd_lep0N (+ siblings) |
| H5 | hd_spn paid station event (KW-FIX-36 17:59 hold table). SPN vH form. | HOLD | DIE-HEAD-91 | proposed; LEC running | NOT FOLDED | hd_spn |
| H6 | TX hm10ff "CH_STAGE+1 unbound" (a pin cycle not in any plan) | TIM | DIE-HEAD-91 | at DRT | NOT FOLDED | TX / hd_serdes |
| H7 | **HEAD relay/type-safe event**: never computed ("no bound RTL on the fleet", TS2/TS3) | HOLD | **UNOWNED** (TS4 scope "HEAD as far as bound RTL exists", not in TS5) | not started | none | ? |
| H8 | **HEAD bind + transport check**: "HEAD has no bind, none" (TRANSPORT-2) | FUNC | **UNOWNED** | not started | none | all |
HEAD has no lane that composes a die plan event or switch. H1-H6 all need one, and none can bind until HEAD has a bind.

## QC (qwen_compute). Planned switch: SECOND switch = 282ca18ef6cc + transport pads + relay, composed by QC-TRANSPORT-FIX-4
| # | change | why | owner | state | rides | types |
|---|---|---|---|---|---|---|
| Q0 | First switch: plan_qc53v4nS 7e4789251637 (v4w + FWS + CLAND + CTLM + START qc53v4s) | various | KW-FIX-39 | applied 22:05 | done | 119 |
| Q1 | MEM9 EXTRA + VM-write landing: x_su_l0_ctl 18->19 (+1 pad) on 12 slices, plan 282ca18ef6cc | FUNC | DIE-QC-96 -> DIE-QC-97 | READY 00:57, then held: COORD ruled the depth-match PROOF does not meet R8. PROOF bench waits for the final plan. | QC second switch | 9 su_l0/su_l1 + 27 MEM9 landing |
| Q2 | Transport pads hook qc_fabric_transport (xhead3 N/S pad, tail1 SKEW/HI/NB_IN/RD/NB pads, 242,864 flops), embed_prov ROPE=1 in glue, compiler DV_EMB_TRANSPORT +11 | FUNC | QC-TRANSPORT-FIX-4 | composing on 282ca18ef6cc (bind pass 1 running). Station bench rerun as 4 jobs on epyc6. NB_IN_PAD and mode 2 not proven yet. | QC second switch | 45 = 16 hc3/st + 27 MEM9 landing + glue + native59 |
| Q3 | QC relay event a235c337: 9 sc types, 83 lanes, +107 PIN CYCLES (skip-bus su_l0/1) | HOLD | TYPE-SAFE-5 | composed on 7e47 only. Must be re-derived on the Q1+Q2 compose (R8 trades key on su_c/su_l depths). | QC second switch, only if TS5 reruns it on QC-TRANSPORT-FIX-4's final plan | 9 sc |
| Q4 | su_idle status race (4a): SU compiler term (+23 is 9 short) | FUNC | DIE-QC-96 -> DIE-QC-97 | compiler only, READY 23:42 | compiler, no plan | none |
| Q5 | HI_PAD 166k flops: compiler reschedule of N-half return could replace 127k of them | CAP | QC-TRANSPORT-FIX-4 | advisory estimate | would change Q2 values: decide BEFORE the switch | st types |
| Q6 | FAIL\|PLAN: none on QC now (KIT_TOPOLOGY_BIND_STALE fixed by the v4t/v4s rebind) | | | | | |
Q1 view link (COUNT-ARCHIVE-2 11-10, per COORD): the mem9 form of su_lane_w_l3 (l3s) is signed off and archived, store id dbdce3cc5a364050 (signoff), routed DB + kit in store id 570173901a488bc1 (eco1/i1), flow-20261109-fe-qc, routed LEC EQ. When Q1 switches: flip the HOLD row intel1:/srv/opentallas-scratch2/claude/dq97/l3s/resign_eco in lanes/COUNT-DO-NOT-COUNT.tsv to CLEARED in the same commit and force a count; l3 stays 1 design, count-flat. Until then the old l3 is the only credit.
Not plan: cland window grow (landing_placement.tcl, DIE-QC-97), conservative forms for 9 attempt>=6 grt/hold rows.

## KV (qwen_kvsys). Planned switch: ONE switch plan_p4 + bind5 + src_p5 (DIE-KV-97 READY 02:24)
| # | change | why | owner | state | rides | types |
|---|---|---|---|---|---|---|
| K1 | plan_p4 = PV/SD/PC-band 7cd661ba + kvr8p3 delta (PHY +3, 192 latency rows, edge taps on 4 hubs, PLL view, hub_C clk_t17 move), reset contract, boot_cdc tie, kit-rtl plan-dir fix | FUNC/CLK | DIE-KV-97 -> KW-FIX-42 | READY 02:24, staged intel1/epyc4/epyc6 (+epyc7 data). Branch faeb1ac9 does NOT merge on main (12 conflicts, ROOT-MERGE-57 02:27). | KV switch | hub_C/Eo/Wi/Wo, phy, phy_v1, 6 kv3_pc |
| K2 | **ZB_ADD = 83** on qkd_attn_cal_gen_r17 + EO_E/EO_RL per EP type (bind hook) + compiler astk_zb_add | FUNC (attention Z calendar 82/83 short; EP chain fault) | **UNOWNED**: DIE-KV-97 parked 02:24 and names a "ZB_ADD successor" that does not exist yet | proposed. The RTL is only in a bench copy (cg.sv); no branch. | **NOT FOLDED**: plan_p4/bind5 have no ZB/EO hook, so this is a second KV bind switch | kv3_hub_C + 8 kv3_hg* (held) |
| K3 | Boot compiler refuses on every KV bind: 176 unpriced kvpc<->slg INNER edges (kv_boot_v36) | FUNC | **UNOWNED** | proposed | compiler only; boot image blocked | none (kits not blocked) |
| K4 | dcal.tok_start 3->84 stages: NOT DECIDED, can fail silently | FUNC | DIE-KV-95 named (TRANSPORT-3), never answered. **UNOWNED** now. | open | ? | sys_c / hub_C |
| K5 | PV ctl FIRST_INPUT_AGE/TRUNK_D/FLAG_D (boot vport RT/DQ), EXP_START base, d2d/kvs_ctl abort corner (sweep 3/4/5) | FUNC | **UNOWNED** | not benched | ? | pv, hub |
| K6 | KV relay/type-safe event: TS3 "0 edits but unmeasured" (no plan face/window_um on 253 buses) | HOLD | **UNOWNED** (TS4 "as needed", not in TS5) | not started | NOT FOLDED | ? |
| K7 | kv3_hub_Wi SPLIT delta (wi_split.py, DIE-KV-91 dry run 11-08 00:02) | CAP/GEOM | no follow-up since 00:02 11-08. State unknown. | proposed | NOT FOLDED | kv3_hub_Wi |
| K8 | FAIL\|PLAN kv3_pc__cl254f2e73 / cl5a95b461 LEC (boot_cdc class) | FUNC | DIE-KV successor | fix inside K1. Read the routed LEC at sign-off. | KV switch | 6 kv3_pc |

## HBM. Planned switch: plan_final3 (11 types) was declared "the last HBM plan change" (COORD 19:0x). The items below are NOT in it.
| # | change | why | owner | state | rides | types |
|---|---|---|---|---|---|---|
| B0 | plan_final3 for 11 types (SPB pads, rst_n tables, q_sm vK) | various | KW-FIX | applied by item_inputs, except q_hub_nw/ne (held) | done | 11 |
| B1 | Hub rebind bind_F3d: writer_sid straps, vm core port rename (writer_kq/tkw), r8_extra map, GQI 4 dead pins drop | FUNC | DIE-HBM-97 | bind RC 0, verify RC 2 (setup issue, not proven). Hub dry running. Hubs held. | hub item_inputs | q_hub_nw, q_hub_ne |
| B2 | q_hub_ne + root macro on outline edge (7 macros): kit_core_margins_um S=0 or hand move list | GEOM | DIE-HBM-97 | proposed ("next plan event") | **NOT FOLDED** | q_hub_ne, root |
| B3 | q_b010 / q_b010pv1 split: 535,757 / 645,297 cells over the 400k cap (FT station flops) | CAP | DIE-HBM-97 (DIE-HBM-93 parked it: "next plan event") | proposed | **NOT FOLDED** | q_b010 (+pv1) |
| B4 | programme_store_r10: outline +43.2 N, M6 ceiling, re-pitched streets | GEOM/PDN | HBM-CORES-B (ps10_vN1 GRT is the judge) | ruled YES, conditional | NOT FOLDED (new plan file) | q_hub_nw/ne, q_b113 (+pv1) |
| B5 | rx_bm3_rest M6 (option A): core PG published on M6, landing M6->M7 | PDN | HBM-CORES-A | proof form | core plus parent landing; affects NW_io, NE_io, q_spb0 (+pv1), vsN0 | 5 parents |
| B6 | Q2NF: q_hub_ne body_n2 outline 786.24x311.04, M6 ceiling | GEOM | HBM-Q2NF-RF -> DIE-HBM-97 pricing | after vF GRT | NOT FOLDED | q_hub_ne |
| B7 | q_sm: registered smh faces = default shell +1/+1 (vs compiler SM extra 0); static_front +1 PIN CYCLE (expected_request, schedule_fault); q_sm0-3 bind must take asbuilt_1108 gu/xs1109 + 6 be wrappers | FUNC/HOLD | HBM-SM-KIDS-2 / DIE-HBM-97 ("shell compensation RTL ownership" still open) | proposed | NOT FOLDED (needs a q_sm rebind) | q_sm0-3 + 17 children |
| B8 | **HBM relay/type-safe event**: TS3 estimate 6 types, 21 buses, 139 stations, +139 PIN CYCLES; worst NW_io<->root L8007/L8008 +22/+23 | HOLD | **UNOWNED** since TS3 (TS4 "as needed", TS5 S81+QC only) | estimate only | **NOT FOLDED** | 6 (hubs excluded) |
| B9 | R5 host control-plane link: RXLAT 101, RSTLAT 70 (cac6fd2efcd5 on main); host obligation "frames >= 110 edges apart" | FUNC | HBM-CORES-A (host_cp_rxs rebuild, 0 PIN CYCLES). The compiler/host obligation has **NO named owner**. | RTL applied; physical rebuild pending | type-local | ot_hbm_host_cp_rxs (root) |
| B10 | PDN-0179 class (M4-column + partial M5 band) in partition_ft_reserve.py | PDN | DIE-HBM-97 | fix proven on q_b011. ETA 03:15 / 04:00 | tool/kit (re-keys?) | q_b011, q_b101, q_b103, q_b101_nw, q_b100 (+pv1) |
| B11 | FAIL\|PLAN q_b102pv1 MPL-0034, q_b111 (+pv1): kit-local OT_MACRO_MOVES (ruled, no plan event) | GEOM | KW-FIX-42 | ruled | kit-local | 4 |
| B12 | FAIL\|PLAN q_b000/001 (+pv1) PDN-0179 / cap, PROVISIONAL on idx_score ra/rb contract views | PDN | DIE-HBM-97 / HBM-CORES | waits on child views | kit | 4 |
| B13 | istareach_1108 (117 entries, 661 stations, PIN CYCLES 83 lanes) | HOLD/TIM | DIE-HBM-91-REACH (11-08 02:31) | no post since. Not shown to be in plan_final2. State unknown. | ? | ~12 native types |
Not plan: svc_pc h9b define (recipe event), q_mca sparse-rows form, opsa/opsb/rest forms.

---
## Transport at bound depth: functional checks per die
| die | bench at bound depth | errors found | still open |
|---|---|---|---|
| QC | YES. TRANSPORT-1 embedding (73/73 words wrong, then fixed 73/73). Fabric 48/48 with controls. Head pad equivalence. Station bench rerunning. | embedding/RoPE, ctl<->fw/fe offsets, station joins, su_idle | station NB_IN_PAD / mode 2; whole-programme token |
| S81 | YES. k_rdy (3a), Engram (3b), xrt leaf 112/112, sid_o, all with failing controls | 3a, 3b, 4b | xo_o, 89 OPEN buses / 40 classes, rebind_links (S11, unowned) |
| KV | YES. EP chain sim on real ctl + 8 EP + 32 EX + 4 ZN, every hop from bound lanes; Z strip bench | EP offset, Z calendar 82/83 | tok_start, PV ctl ages, EXP_START, boot compiler (K3-K5, unowned) |
| **HBM** | **PARTIAL.** Only the R5 host CP link has a bound-depth bench (DIE-HBM-94, 14000 requests, mutants), plus DIE-HBM-92's SFU vmsim/lane benches (fixed-latency consumers). R5 itself was found by arithmetic. | R5 host CP, SFU fixed-latency consumers | 420 buses, 258 JOIN sinks, 187 unequal replicas never benched. su_N taps closed "by law, not benched". hleaf.s_ready, mu_fused ready, mcb->hub ready (23 st), root<->hub ready "not traced". TRANSPORT-3 read bind_F3; the wave bind_lat_vJ depths were never compared. **No owner.** |
| **HEAD** | **NONE.** No bind exists, so there is no transport table, no bench and no relay event. | n/a | everything (H7, H8, unowned) |

## Does each die's planned switch include all its events?
- **S81: NO.** S7 (leaf t42 early-core-tap, plus taps following moved cores) and S8 (macro moves into the plan) are slated "after the switch". S10 (compiler pin_cycle_deltas) is unowned. TS5's c72370 does not bind yet (1 error).
- **HEAD: NO SWITCH EXISTS.** H1-H6 are private forms waiting on plan events that no lane writes. No bind.
- **QC: YES IF** TYPE-SAFE-5 reruns the relay event (Q3) on QC-TRANSPORT-FIX-4's final compose and the HI_PAD reschedule (Q5) is decided first. Otherwise Q3 becomes a third switch.
- **KV: NO.** K2 ZB_ADD/EO hook is not in plan_p4/bind5 and is unowned. K6 (relay) and K7 (Wi split) are outside it. The branch also needs a rebase onto main.
- **HBM: NO.** plan_final3 is "last", but B2, B3, B4, B6, B7, B8 (and maybe B5, B13) are pending plan-level changes. They should be batched into ONE HBM event file by DIE-HBM-97. B8 has no owner.

## Counts (pending = not applied; done rows excluded)
| die | pending | unowned | not folded into the planned switch |
|---|---|---|---|
| S81 | 13 (S1-S13) | 2 (S10, S11) | S7, S8 (+S10 compiler) |
| HEAD | 8 (H1-H8) | 2 (H7, H8) + no switch owner | all 8 |
| QC | 5 (Q1-Q5) | 0 | Q3 is at risk |
| KV | 8 (K1-K8) | 4 (K2, K3, K4, K5) + K6 | K2, K6, K7 |
| HBM | 13 (B1-B13) | 1 (B8) + B9 host obligation | B2, B3, B4, B6, B7, B8 |
