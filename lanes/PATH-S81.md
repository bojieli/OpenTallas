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
