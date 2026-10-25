# Lane PATH-S81 -- one complete DeepSeek path (L14 eng E2 + head B)

Started 2026-10-25 08:07 PDT (Claude, fresh lane per _FRESH_LANE_BRIEF item 10).
Path source: CODEX-LOG handoffs 08:03-08:04 (S81 PLAN3, CCONN, LEAF0719, cores parent, KITS0719, HEAD0719) and the
exact boundary inventory epyc1:/srv/opentallas-scratch2/claude/codex-s81-kits-0719/L14_boundary_paths.json.
Plan basis: immutable P1 snapshot epyc1:/srv/opentallas-scratch2/claude/codex-s81-plan-0719/locked_l14_p1/src (eng E2
reservation 70bb1be9ab + 4 leaf fields t7/t55/t56/t57 + t18 knees + loRS_t6 FT3+1). **P1 G0C collected 08:06: PASS
0 errors / 1287 warnings** (unit oth-ubuntu-3954988-1792940522 exit 0).
"Signed off" = GEOM PASS + route + TT setup / FF hold sign-off (833 ps, 60/25) + LEC + lint gate + bound in die.

## Path (layer die s81, L14)
- Boot/control: seqhost -> s_4S_L4(t36) -> s_5S_x00(st t18) -> s_6S_L4(t55) -> s_7S_x05(st t22) -> svc_15(hiRS t6) -> svc_14(loRS t7) -> eng   (41 cyc)
- Data south 276 b: eng.xtier_o0 -> svc_14(loRS t7).ft4 -> svc_12(loRS t6).ft3 -> svc_13(hiRS t5).ft3 -> s_6S_L4(t55).ft8 -> s_6S_L2(t56).ft8 -> s_6S_L0(t57).ft7 -> s_6S_C(c1x_C t8)   (39 cyc, return 39 the same way)
- Data north 276 b: ... s_6S_C -> s_6S_L1(t58) -> s_6S_L3(t59) -> s_6S_x06(st t20) -> s_6N_L2(t60) -> s_6N_L0(t61) -> s_6N_C(c1x_C t9)   (69 cyc)
- Return north: s_6N_C -> s_7N_C(lepe_mu_C t1) -> t71 -> t70 -> t69 -> t68 -> t67 -> s_7S_C(lepe_nh_mus_C t1) -> t66 -> t65 -> st t22 -> svc_15 -> svc_14 -> eng   (71 cyc)
- Attention: seqhost -> svc_5 (svc_hi_dsdv_svc_pvso_entry__t1, 64 x hcore) <-> s_3S_C(iq_C t1), svc_4(lo t2), svc_3(hi t2), svc_7(hi t3), svc_11(pvso_entry t2)
- Return/ctrl: s_0N_C(lepw_mu_C t1) -> seqhost ; die IO x_E2_in/x_E2_out via frame col_h10_r0_p1/p4.
- Scope note: Codex's statement includes "all 16 norm slices / 80 leaves" after attention -- that is most of the die. This list
  covers the named chain; the norm-slice fan-out is item G (one group), see OWNER? below.

## Item list (state 08:10)  -- states: NEEDS-KIT / GEOM / ROUTING / FIX / SIGNED
| # | item | kind | state | blocker / live job |
|---|------|------|-------|--------------------|
| 1 | seqhost__t1 | part | NEEDS-KIT | bound kit RTL (strict bind, item X1) |
| 2 | ot_s81sl_leaf__t36 | part | NEEDS-KIT | X1 + CS forwarding (X2) |
| 3 | slice_station__t18 | part | GEOM (REQ, knee PASS-COND) | R2 receiver input hold structure (CLOCK/CP1) before fresh kit |
| 4 | slice_station__t22 | part | GEOM (REQ) | density taps a11549 49 taps; R2 hold; sender t55 kit |
| 5 | svc_hi_dsdv_svc_rs__t6 (svc_15) | part | NEEDS-KIT | G2 proof live intel2 unit 758336 (pre-P1 trial input) |
| 6 | svc_lo_dsdv_svc_rs__t7 (svc_14) | part | NEEDS-KIT | old G2 s3 HOTSPOT 26 ov FT4; native_pair 18 nm MY M3 pin fold bug |
| 7 | eng__t1 (wrapper) | part | NEEDS-KIT | E2 reservation in P1 (G0C PASS); X1 |
| 8 | dsdv_eng_rr_e (E2 core) | core | FIX | old-source route live epyc1 ot-run 3783378 (TT -237/643, ROM->CID); successor = boundread c8496ae75 + CID retime a11cb0db4 + LEC |
| 9 | dsdv_eng_rr_h0 | core | FIX | s2 insertion FAIL TT mean 305.5 vs 263.7, TT -28.2 |
| 10 | dsdv_eng_rr_h1 | core | SIGNED | LEC vs current RTL owed (old runners LEC_CHECK=0) |
| 11 | svc_lo_dsdv_svc_rs__t6 (svc_12) | part | NEEDS-KIT | G2 HOTSPOT 67 ov, TT+264/FF+67 |
| 12 | svc_hi_dsdv_svc_rs__t5 (svc_13) | part | NEEDS-KIT | X1 |
| 13 | ot_s81sl_leaf__t55 | part | NEEDS-KIT | G2 live g2four unit 3891158; X2 CS |
| 14 | ot_s81sl_leaf__t56 | part | NEEDS-KIT | G2 live 3891164; nudge WIP (404.9 um ctl) |
| 15 | ot_s81sl_leaf__t57 | part | NEEDS-KIT | G2 live 3891161 |
| 16 | dsdv_slice_c1x_C__t8 (s_6S_C) | part | NEEDS-KIT | X1 |
| 17 | ot_s81sl_leaf__t58 | part | NEEDS-KIT | alloc5 done, payload/review/G2 owed |
| 18 | ot_s81sl_leaf__t59 | part | NEEDS-KIT | same |
| 19 | slice_station__t20 | part | SIGNED (release cache) | clock HOLD note (KITS) |
| 20 | ot_s81sl_leaf__t60 | part | NEEDS-KIT | alloc5 |
| 21 | ot_s81sl_leaf__t61 | part | NEEDS-KIT | alloc5 |
| 22 | dsdv_slice_c1x_C__t9 (s_6N_C) | part | NEEDS-KIT | X1 |
| 23 | dsdv_slice_lepe_mu_C__t1 | part | NEEDS-KIT | X1 |
| 24 | leaves t65..t71 (7 types) | part | NEEDS-KIT | X1/X2 |
| 25 | dsdv_slice_lepe_nh_mus_C__t1 | part | NEEDS-KIT | X1 |
| 26 | svc_hi_dsdv_svc_pvso_entry__t1 (svc_5) | part | NEEDS-KIT | X1 + X3 hcore profile |
| 27 | ot_s81c_attn_hcore | core | FIX (GEOM-REQ) | FF +3.71/0 but TT -29.15/13 EP (FP fanout 3x BUFx2 190 ps); all13 report unparsed |
| 28 | attention neighbours svc_3/4/7/11, s_3S_C | part | NEEDS-KIT | X1 |
| 29 | dsdv_slice_lepw_mu_C__t1 (s_0N_C) | part | NEEDS-KIT | X1 |
| 30 | die IO frame col_h10_r0_p1/p4 (x_E2) | part | NEEDS-KIT | CP1 pair r0/r1 autopilot (proof vehicle) |
| G | remaining norm-slice types (16 slices / 80 leaves) | group | NEEDS-KIT | scope question |
| H1 | hd_serdes (head link) | part | NEEDS-KIT | plan maps coll_o0[513:0] -> rx[511:0]; PMA pad binding |
| H2 | hd_lep0N | part | NEEDS-KIT | kit_rtl pruned; binder |
| H3 | hd_spn / hd_spn_end | part | GEOM (REQ) | 07:05 REQ, routes queued --geom REQ |
| H4 | hd_st_* (6 types) | part | GEOM (REQ) | 5 diagonal types need knee/lattice |
| H5 | hd_tile | part | KIT-PLACED | LEC owner |
| H6 | ot_s81hd_elemB_cv (head B) | core | FIX | elemB_if2 live epyc1 unit 3932795 (538 IF anchors, stage-local preCTS) |
| H7 | ot_s81hd_elemA_cv | core | SIGNED | - |
| H8 | hd_ctl / hd_host | part | NEEDS-KIT | no RTL on main (OWNER? 04:39 host width) |
| X1 | strict bind (cap30 nested reset) | gate | RUNNING | v10 bind OOM 40G 08:04 -> rerun bind-only v10b --mem 160 unit oth-ubuntu-4115518-1792940837 (PATH-S81) |
| X2 | CS_* forwarding into ot_s81sl_slice lf[k] | RTL | OPEN | t55/56/57 params not in cap30 source |
| X3 | hcore native profile CTLA/RSTE miter | proof | RUNNING | units 3705891 (pass) / 3705894 (mutant), C++ compile |
| X4 | TOK-DS exact-path pass on bound views | token | OPEN | needs X1 emitted RTL; I13 554 on claude/tok-ds-i13b-1025 |

**Progress 08:10: 2 of 43 items signed off** (t20, elemA; rr_h1 counted after LEC). Items = rows 1-30 + G + H1-H8 + X1-X4 counted as listed.

## OWNER?
- Scope of "one complete path": is the named chain above (eng E2 -> slice V rung -> svc_5 attention -> s_0N_C return + head B)
  enough, or must every one of the 16 norm slices / 80 leaves (item G, most of the die) be closed for the S81 path to count?

## TOK-DS exact-path spec (item X4) -- 2026-10-25 08:10 PDT PATH-S81
The token pass for this path = L14 (L0 skips Engram) on the strict-bound die netlist (X1 emitted RTL), not on dv_die/as-built relays:
1. Inputs: released-checkpoint L14 entry H (codex/entry-engram-1025@82d63dab7 helper, exact) at seqhost; boot 53 b seqhost->eng over t36/t18/t55/t22/svc_15/svc_14 (41 cyc).
2. Exercised RTL: eng__t1 with direct E/H0/H1 (adopt_eng_split 363dd0fa20, on main) + boundread (main) + CID retime a11cb0db4 if adopted (0 public cycles);
   276 b eng->s_6S_C over svc_14/12/13 + t55/56/57 WITH CS_* forwarding realized (X2; FT +1 lane deltas from LEAF0719: eng->s6SC 39->40, s6SC->eng 39->40, eng->s6NC 69->70);
   svc_5 pvso_entry with hcore EH profile (CTLA/RSTE: +1 load-ready edge, +2 boot) and I13 gather 554 cyc/job (claude/tok-ds-i13b-1025@5f03a61d8);
   return s_0N_C -> seqhost.
3. Checks: strict cut replay (as cuts 0S/0N/7) on a NEW cut "eng+s6S" built from the bound netlist, real cycles per hop reported, input-corrupt + wrong-cycle mutants caught; compare to the priced calendar (AR 785.1 / MTP 2,750.2 basis) and record the delta from items X2/X3.
4. Blocked until X1 emits RTL (v10b running) and X2 is proven. Owner of the run: TOK-DS lane (PATH-S81 supplies the bound netlist + this spec).
2026-10-25 08:11 PDT FLOW-INFRA/DIE-PROTO -> PATH-S81: s81 die-top GRT (plan 7f0e38c8 = main 394765394, signals M4-M7 @0.75 adj) still LIVE epyc1 dtrial-grt-3950895 (iter 2/50 at 07:47) -> no overflow yet; plan hops 0 over 405; die clock 627/539 ps FAIL (CLOCK); sta_ideal TT live. claude/die-proto-1025@bd51e6310 results/die_proto_1025/SUMMARY.md

## Scope additions (owner-approved 10-25, via coordinator) -- 2026-10-25 08:12 PDT PATH-S81
(1) Die level is part of "complete". New path items D1-D6:
| # | item | state | evidence / blocker |
|---|------|-------|--------------------|
| D1 | die GRT with the path's real signed-off views (stand-ins elsewhere) | OPEN | die-top GRT on main plan (stand-ins everywhere) LIVE epyc1 dtrial-grt-3950895 (DIE-PROTO, iter 2/50 at 07:47); path views not yet signed off |
| D2 | die STA TT setup / FF hold over the path | OPEN | DIE-PROTO sta_ideal TT live (ideal clock); real-view STA needs D1 + signed views |
| D3 | clock tree die root -> path flops (regional taps, related-pair skew + CPPR) | FAIL | S81 die clock 627/539 ps FAIL (CLOCK lane, DIE-PROTO 08:11); t22 density taps a11549 49 taps model only |
| D4 | reset + START broadcast to the path | OPEN | X1 nested core-reset emission (v10b); START broadcast e84452a8fd not on S81 bind (TOK-DS 05:41) |
| D5 | die-to-die link layer die -> head B | NEEDS-KIT | layer x_E*_out SerDes frame -> head hd_serdes (plan maps coll_o0[513:0] onto rx[511:0]: plan defect; PMA pad binding) = items 30 + H1 |
| D6 | token test on exactly those bound views | OPEN | = X4 spec above |
(2) Representative coverage: chosen type **col_h9_r1__t1** (s81 type replica count 60 in OWNERS.tsv, tied with col_h9_r2__t1 at 60; next is 12).
Why: (a) the highest-replica partition type on the layer die; (b) it sits ON this path: frame fE2 carries x_E2_in/rt_E2_in into s_6S_C (path slice), and fE2_p2_b1/p3_b1/p5_b1/p6_b1 are col_h9_r1__t1;
(c) it has a known structural failure to close (Codex g2o30 col_h9_r1: TT -247.61 on reset pr_reset_u_rrl_73->74, ~359 um planned hop forced ~700 um detour across an M7-closed core because the prototype G2 routes reset on M2-M7 instead of the reserved M8/M9);
(d) TYPE-REDUCE folds the col family 12 -> 8, so the post-fold col_h9_r1 form is what gets copied 60x. col_h9_r2 is its sibling (same count) and becomes the second representative only if the fold merges them.
Collective-bus stretch (item C2): frame_int lanes fi_E2_p2_r0r1 (1167 b, 4 cyc) col_h9_r0_p2 -> col_h9_r1 and fi_E2_p2_r1r2 (1167 b, 4 cyc) col_h9_r1 -> col_h9_r2, plus xo_E2_in_a/b (1104 b) along frame fE2 to fE2_p1_b0 (x_E2 path entry).
| C1 | col_h9_r1__t1 (post-fold form) | NEEDS-KIT | ask PLAN-DELTA to land this one type first in the S81 delta; reset-on-M8/M9 G2 fix (CLOCK owns) before kit |
| C2 | collective-bus stretch fi_E2_p2 r0r1/r1r2 + xo_E2_in_a/b | OPEN | needs C1 + col_h9_r0_p2/col_h9_r2 views (stand-ins OK for die GRT) |
**Progress 08:12: 2 of 51 items signed off** (43 + D1-D6 + C1-C2).
2026-10-25 08:13 PDT PATH-S81/ENG: item 8 started. codex/eng-map-retime-0719@a11cb0db4e pushed to GitHub. Branch claude/path-s81-eng-1025 = main 3947653943 (has boundread c8496ae75 + aq decl fix) + retime a11cb0db4 + checked runner a83ef61cd1. E3 kit epyc1:/srv/opentallas-scratch2/claude/path-s81-eng/dsdv_eng_rr_e_e3 = e2 recipe (same 410.4x466.56, pins.json/io.tcl byte-identical, same macro sites) + current RTL + -DOT_S81ENG_TMAP_CPRE + main signoff/pair_skew bundle. Gate A (rtl_lint + synth) live ot-run oth-ubuntu-255370-1792941172 (epyc1). Old E2 run untouched.
2026-10-25 08:15 PDT FLOW-INFRA -> PATH-S81: flow canaries (main 202a50a59): s81_head hd_turn_a FAIL grt_gate: TT pin-reg 225.83 vs 250 (dev 24.17), FF 179.94 vs 202.5 (22.56), both > 20 (FLOW-INFRA checking a common cause with KV io_ft, same -23 ps signature). s81 slice_station t12 canary still live (5_1_grt done after 63.8 min, post-CTS gate running). epyc1:/srv/opentallas-scratch2/claude/flow-canary/runs/
2026-10-25 08:16 PDT PATH-S81/HEADB: elemB_if2 (unit 3932795) COLLECTED: place rc0 08:11. Gates on 3_place: HEAD_ROM_IF 538/538 anchored, macro-IF dist p50 7.5/p90 9.4/max 12.2 um (0 >20) PASS; halo/macro overlap 0 PASS; t_r->w_r n256 median 15.1 PASS / max 102.4 um, 1 >100 FAIL (bit 128 only). Cause (viewed epyc1:/srv/opentallas-scratch2/claude/path-s81-headb/review + render): lane L8 (w_r[128+:16]) straddles the ROM rd_out pin-side split (bits 128/129 exit the RIGHT edge x~209, the other 14 the LEFT edge; L8 placed left x~20), so 2 register stages carry ~190 um across under rom0; also cap->t_r (ungated) up to 248 um (L8) / 202 (L1). Own copy elemB_if2c -> CTS (TT, PRE_CTS clear) ot-run unit oth-ubuntu-471784-1792941306. LEC: lec.py config parser treats make '+=' as '=' -> lint read only ot_s81hd_rom_addr_copy.sv (UNPROVEN elaboration); patched copy, LEC rerun unit oth-ubuntu-152855-1792941101.
2026-10-25 08:19 PDT GEOM-REVIEW -> PATH-S81: verdicts in GEOM-REVIEW.md. #8 E2: floorplan ACCEPTED, route held; successor needs a tapped clock (now one tree at 520 ps) + CID retime a11cb0db4e + a registered pre-decoded fck->vo_b beat select + F6 regions. #27 hcore_eh1: FAIL, TT from the g_a y[msb]->u_k1 fanout; register-duplicate it. H6 head B elemB_if2: placement PASS, F6 measured PASS (ROM addr/CE <=11.1, DO capture <=11.5 um); continue CTS, post-CTS REQ with ROM-vs-IF clock table. #30 cp1 r0_p1: GEOM-REVIEW-2 owns it; my diagnosis NOTE says 90% of failures are input pin-reg hold from the -40 seam basis + t48/t49 leaf skew.
2026-10-25 08:19 PDT FLOW-INFRA -> PATH-S81: s81 slice_station t12 canary (202a) FAIL grt_gate: TT pin-reg 224.20 vs 250 (dev 25.80, setup_est -36.29), FF 181.35 vs 202.5 (21.15). Same signature as head/KV: treat as a FLOW-level cause (being diagnosed), not a t12 kit problem.
2026-10-25 08:20 PDT PATH-S81/BIND: X1 v10b strict bind (unit 4115518, --mem 160) FINISHED rc=1: 398 parts/183 types, n_errors 13029 = 12800 MULTI_DRIVEN (ALL in leaf ot_s81sl_vp: module-scope 'integer i, k' written by 4 always blocks -> slang $driver$i/$driver$k, 160 b x 80 leaves) + 200 TIED listed (7.33M tied sinks total, mostly internal $mux/$mem literals of now-unblackboxed vp/vn/ve bodies; leaf-port ties e.g. ot_pl_seam_w_plr.ir 160k) + 29 unlisted (report truncates at 2000); unbound 14469, undriven 0. Fix for MULTI in claude/path-s81-cs-1025 (vp integers block-local). X2: branch claude/path-s81-cs-1025@93f4907907 = main + R3 cherry-picks + LF_CS_* per-leaf forwarding; miter/leaf/beat proofs queued on epyc1 /srv/opentallas-scratch2/claude/path-s81-cs. G2 hi t6 (svc_15): STRUCTURAL ov 30282 (70.8% bbox), TT +179.76 FF -2.46; render viewed: 29k station flops packed in the ~10 um channels of the left 3 of 8 core columns (72 hard-core blockages), right 5 columns station-free -> FT corridor must move to a core-free band / widen channels.
2026-10-25 08:22 PDT GEOM-REVIEW-2 -> CLOCK-RESET/CP1 + PATH-S81 item 30: cp1 col_h10_r0_p1__t1 (autopilot 92cd4ba072f2) post-CTS FAIL-F1, placement accepted. Fix = early band-following face taps for the 2826 ingress flops (CP2 clk_c mechanism, FF ~140, <=400 sinks/tap), re-pitch the 56-tap grid to the sink bands (<=204 um), and arst_n->u_rst_root as a reset-synchroniser false path. Apply to the r1 twin too. Full verdict in lanes/GEOM-REVIEW.md 2026-10-25 08:22 PDT.
2026-10-25 08:23 PDT PATH-S81/HCORE: item 27 all-13 TT parse (intel2 codex-s81-legacy-0719/hcore_tt_all13): 13 EP = 3 launch flops, ALL f12 LAT-4 chain adders, launch = previous adder y[29]/y[30] (exponent) -> next adder u_k1 cut: g_c2.g_a7 -> g_node2 (7 EP, -29.15..-11.97, L255.87/C~239), g_c2.g_a1 -> g_a2 (4 EP, -8.81..-5.67), g_c2.g_a3 -> g_a4 (2 EP, -3.52/-2.38); 17-18 stages, each via 3 (or 2) serial fanout BUFx2 (23/17/24, 24/24/24, 10/24/24 loads; 130-200 ps). Probe (find_timing_paths through the nets on 4_cts): every such net fans out to u_k1 bits small[0..26], big man, exp, sign = the SWAP SELECT (|b|>|a|: field compare + 23-bit frac compare), 61 mux loads at set_max_fanout 24 -> serial BUFx2 chain. Same structure for all 13; not floorplan, not clock (skew <= 17 ps).
2026-10-25 08:23 PDT PATH-S81/HCORE: FIX (structural, 0 cycles) claude/path-s81-hcore-1025@35baa97a11 (+sdc_lint.json fixup): -DOT_F12_SWAP_REP builds the swap select 4x in keep_hierarchy leaf ot_hdc_f12_swsel (non-param, + SYNTH_KEEP_MODULES), one per mux group (<=17 loads); off by default in rtl/hdc/ot_hdc_fp32_f12.sv. PROOF epyc1 /srv/opentallas-scratch2/claude/path-s81-hcore/miter: f12 l4/l5x/l5 vs unchanged text 3 seeds x 2M cycles PASS (623k equal-field compares/seed), mutant CAUGHT 3/3; hcore (EH 7a00f9ed/780e8010, CTLA+RSTE) vs EH source, all pins every cycle, 3 seeds x 40k PASS (ov ~29.9k, oy changes ~39.9k), mutant CAUGHT 3/3 (~860 mismatches).
2026-10-25 08:23 PDT PATH-S81/HCORE: X3 COLLECTED: profile miter units 3705891 PASS (S81C_HGRP_BENCH PASS seeds 1-3, 20000 cyc, 0 mismatches, ov 14790; S81C_LOAD_PROFILE load_transport=1 reset_release=2 stage_bad=0) / 3705894 mutant FAIL seeds 1-3 (19954 mismatches) = CAUGHT. Both exit 0, done.
2026-10-25 08:23 PDT PATH-S81/HCORE: kit epyc1:/srv/opentallas-scratch2/claude/path-s81-hcore/kit_swr (= branch kit dir __157.68x259.2_swr; hcore_eh1 outline/pins/SDC/clock recipe unchanged) runner run_swr.sh: synth -> LEC fail-closed -> swsel count >=124 -> face_guard -> CTS -> isolated FF repair (repair_ff.tcl, one FF scene) -> independent TT check at placement; GRT with SKIP_INCREMENTAL_REPAIR + DRV-only post hook; signoff exit propagated. LIVE goal=cts unit oth-ubuntu-932737-1792941668 (40 GB).

## PARKED 2026-10-25 08:24 PDT (PATH-S81/HCORE)
- Branch claude/path-s81-hcore-1025@35baa97a11 + sdc_lint.json fixup (pushed; rtl/hdc/ot_hdc_fp32_f12.sv OT_F12_SWAP_REP off by default; kit dir physical/die_plan/s81/cores/svc/kits/ot_s81c_attn_hcore__157.68x259.2_swr incl. miter/). Worktree epyc1 /srv/opentallas-scratch2/claude/wt/path-s81-hcore (sparse; remove after merge).
- LIVE: epyc1 kit /srv/opentallas-scratch2/claude/path-s81-hcore/kit_swr, ot-run unit oth-ubuntu-932737-1792941668, run_swr.sh GOAL=cts (in synth at park). Collect: kit_swr/run_cts.log tail; lec_run.log (LEC EQUIVALENT required); count_swsel line (>=124); repair_ff.log OT_REPAIR_FF; tt_check_place.log OT_TT_CHECK (+ tt_check_place.rpt); exit in ../kit_swr_cts.otrun.log. Do NOT relaunch into kit_swr while the unit lives.
- NEXT: when tt_check_place.ok exists: render 4_cts (repair_ff) with the geomrev2 gtools, view, post the follow-up line under GEOM REQ [PATH-S81/HCORE 08:23] (render path + TT/FF numbers + cell count). Autopilot row 204b1a8e2c7c (enqueued --geom REQ, goal finish, runner kit_swr/run_swr.sh, 40 GB, 200k cells) submits on the reviewer's PASS and resumes at GRT. If TT still fails at placement: read tt_check_place.rpt (new worst path) before any further change.
- Old hcore_eh1 run (intel2 unit 3823172) untouched. X3 profile miter collected (PASS/CAUGHT), no live units.
- OWNER?: none.
2026-10-25 08:24 PDT FLOW-INFRA -> PATH-S81: WARNING gen_phys kits generated on main >= cece3ea38 (07:35) with pipelined/wavefront reset crash at CTS ('can't read rt_named_nets', cts.tcl 6). Fix READY claude/reset-taps-scope-1025@66346540c (ROOT merge pending): regenerate after merge, or for an urgent path kit add 'global rt_named_nets' before 'set rt_named_nets {}' in the kit's reset_taps.tcl copy.
2026-10-25 08:32 PDT CLOCK-RESET -> PATH-S81: (1) L14 receiver input hold: IO-HOLD v2 READY+PROPOSAL claude/iohold-0810 (opt-in clock.seam_hold {sender 25, seam 25}); t41 measured FF in_min -40 -> 0: padded ports 1630 -> 146, total pad -95%; R2 pad pair NOT adopted. t41/t22 capture clock is also 83 ps late (11-level tap tree) -> S81-KITS tap structure. (2) DS reset wall col_h9_r1: claude/g2-reset-0810@4b5282937d reset_tree plans relay hops around core walls; PROTO probe 3026 ovf/TT -247.61 -> 0/+313.96. (3) head die clock: stand-in contract claude/dieproto-clk-0810@7986d6ff17 (pair 213/177 -> 78/71, FF hold -154.6 -> -33.8); tree-topology fix in progress (DIECLK-TOPO).
2026-10-25 08:34 PDT PATH-S81: [S81/VQ f6 final] gap closed in autopilot/resolved.tsv: sign-off collected NOT SIGNED (TT+47.70/FF-38.82 433 EP); successor = S81-CORES structural rebuild.
2026-10-25 08:35 PDT FLOW-INFRA -> PATH-S81: canary s81 slice_station__t12 on main 0372e55a4 FAIL in CTS: 'cts.tcl, 6 can't read rt_named_nets' (main cece3ea38 proc-scope bug; hits every gen_phys kit, not only reset-tap kits). Fix READY URGENT claude/reset-taps-scope-1025@66346540c. Don't launch S81 kits from main >= cece3ea38 until it merges. Run: epyc1:/srv/opentallas-scratch2/claude/flow-canary/runs/s81_0372e55a4_1025_081726_083418
2026-10-25 08:36 PDT PATH-S81/ENG: E3 gate A PASS on claude/path-s81-eng-1025@0e227bc31f: strict rtl_lint PASS after 2 structural lint fixes (f6ba7c65a8 parameter checks -> generate-scope elaboration tasks; ef1bbaf96d rtl_lint read_verilog -defer so modules with deliberately illegal defaults lint as instantiated, probe: implicit net still FAILs; 0e227bc31f aq_n32 shared module-scope 'integer i' = multi-driver in check -assert -> local loop indices, no logic change). Synth rc0, sdc_lint PASS, face_guard 2688/2688 PASS (netlist+ODB), 629 CPRE capture flops present in 1_2_yosys.v. Live: LEC (main lec.py, incl implicit-net lint) ot-run oth-ubuntu-3229663-1792942574 (spill epyc2); place->CTS oth-ubuntu-2531393-1792942576 (spill epyc3), kit epyc1:/srv/opentallas-scratch2/claude/path-s81-eng/dsdv_eng_rr_e_e3.
