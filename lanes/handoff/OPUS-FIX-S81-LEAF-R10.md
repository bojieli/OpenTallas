# OPUS-FIX-S81-LEAF-R10 handoff (Opus; succeeds FABLE-FIX-S81-LEAF-R9 at 23:1x 11-21; owns ot_s81sl_leaf__t* + kv_leaf t1 t3 t4 (+t2 split, J9))
Lane dir intel2 /srv/opentallas-scratch2/claude/opus-fix-s81-leaf-r10. R9 dir (gate trees, clone) = /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r9. Read R9 handoff for background.

## COORD 23:25 stop list
kv_leaf t2 28-piece split is NOT J8 (goes to J9). Focus: gate c leaf re-grid (incl kv_leaf t1 t3 t4) -> J8 rows to S81-J6-ASSEMBLY-R5 by 11-22 14:00. t2 split draft only after the hand-off.

## Gate c (plan c 8c21a4c06257, unit oth-ubuntu-2637398-1795324543) DONE 23:17
ELAB_RC=0 BIND_RC=0 (873 crossings, 0 errors) LAT PASS 873/873 with the expected 4 lane deltas, PRE PASS.
G0: 1 NEW error vs J7 (2 gone): t62 ft0 stage 0 bit cells (123) hit u_lf.u_vp.g_ln[6].u_l after R9 nudge (0,-43.2) of lanes 7,6.
Fix = plan d: ft_nudge.py --no-snap allocator, ONLY t62 ft0 bit_sites spliced (script r10_t62fix.sh, out rgd/). Then G0+PRE re-check on plan d.

## t2 split (parked for J9)
R9/t2s: census done; type_split patches in R9/clone (ts_patch.py, ts_patch2.py by R9; tmp/ts_patch3.py by R10: band_fixed_um follows landing bands, insertion_target_override copied; spec drops landing_reader/writer_start). Next failure: reset_tree wf_solve "added tap clk_t82 violates outline/halo/tap spacing" in _reset_trees on the piece plan.

## t39 proof (R8 chain b1, epyc7): geom PASS, route started 23:03 (kit epyc7 kw43-wave-1109n/.../private/FABLE-FIX-S81-LEAF-R8/ot_s81sl_leaf__t39_1121220439/gen/ot_s81sl_leaf__t39, log otrun_route.log). Chain process on intel2 (waiter PID 3546224 tree) posts as FABLE-FIX-S81-LEAF-R8.

## 23:4x update
- Plan d 19d389f9e9b7 (rgd/plan_h2_2249.json; only t62 ft0 bit_sites differ from plan c, 123 bits <= 18.09 um). Gate d unit oth-ubuntu-3457055-1795332181 (script r10_gated.sh = R9 gate in the SAME tree R9/g68b_src, plan swapped in place; log g68d.otrun.log, markers G68D_*, R10_GATE68D_DONE). Waiter armed.
- Draft J8 delta j8_leaf_rg9_delta.json (r10_delta.py J7 -> plan d): 68 types, 4 lanes fixed_cycles, 4 latency rows. Rebuild it from the final plan before the hand-off.
- Intake item 3 (leaf raw reset rows): reach_rules check on plan d leaf types (plan path must be inside the tree!) = 59 edge_reach + 24 start_raw_net (J7: 52 + 15). All on clock.landing_local_resets raws (rst_rl_*), which reach_rules fix --rules 1 skips by design (0 types changed). The bind re-picks them by anchor site (RESET_ANCHOR lines, moves up to 203 um). Fix tool r10_rawfix.py SRC PLAN BIND_DIR OUT REP TYPE_RE [--check]: bound tree (bind rtl), bind anchor + LOCAL-RESET-RAW-1 receipts written back, over-limit (180 half-cycle negedge / 405) -> nearest same-depth bound rst_rl (0 cycles), anchor re-recorded. Run it on gate d bind out (R9/g68b_src/.../native_bind/out) once gate d bind is done -> plan e -> gate e.
- t39: CTS on epyc7 (23:35); waiter on R8/t39spec/chainB.log.

## 01:0x update (11-22)
- OWNERS: COORD-ROUTED-OWNERS.tsv prefix rows s81sl_kv_leaf__* / ot_s81sl_kv_leaf__* -> R10; kv_leaf t2 row -> R10; 61 ot_s81sl_leaf__t* rows -> R10 (COORD ruling). kv_leaf t1/t5 stay FAM-S81-MISC-R4 (J7 work; J8 form = my delta).
- GATE D GREEN (plan d 19d389f9e9b7): ELAB/BIND 0, LAT 873/873 (4 expected), G0 0 new, PRE PASS. HANDED to S81-J6-ASSEMBLY-R5 00:5x (hub ce2cd8a1c2): j8_leaf_rg9_delta.json sha 1565ba0a3271 (68 types + 4 lane + 4 latency rows). Evidence g68d/.
- Raw-reset fix (COORD approved): r10_rawfix.py on gate d bind (rtl/s81p_<type>.sv): 53 half-cycle hops over 180 -> 0 (16 same-depth re-picks + 41 leaf-site slides, margin 18 um, consumers <= 217 um). Plan e a0a696072693 (rge/), only clock.landing_local_resets + reset_tree_anchor differ, 60 types. Delta ready: j8_leaf_rg9_rawreset_delta.json sha dc684cd7a257 (75 types). Gate e unit oth-ubuntu-2842638-1795337930 (r10_gatee.sh, log g68e.otrun.log, markers G68E_*). If green -> post replacement delta to R5; else plan d delta stands.
- NOTE: gate d/e reuse R9/g68b_src (plan swapped in place); its native_bind/out is now gate e's.
- t2 split: may be drafted in background now (plan d handed off); next failure was reset_tree wf_solve added tap clk_t82 spacing on the piece plan.

## 01:4x update
- COORD accepted the plan e slides; plan e replaces plan d if gate e is green.
- RESPACE (R5 die-wide istation_respace 300 um; ledger epyc9 s81-j6-r5/j8_respace/ledger.json is on J7 geometry): my analysis in respace/. J7 ledger rows on my 75 types: 4909 (3480 on rows my re-grid rewrote, 1416 untouched, 13 index-shifted). The J7 ledger reprices my 4 delta lanes by +1 (double count: on plan e respace reprices none of them). istation_respace --limit 300 on plan e leaf types: 6389 rows respaced, 1675 rows +2025 stations (1723 bus / 302 core), 136 die lanes +152 cycles, 0 refused (ledger_e300.json, plan_e_resp300.json). G0 of plan_e_resp300 vs gate d G0 running (r10_respg0.sh, log respace/respg0.otrun.log). POST to R5 before 06:00.
- t2 split (J9 draft, my copy t2s/; R9 clone patched ts_patch3 + ts_patch4 [inline map.parts overrides map_file]; mkplan placeholder now tap-clear): clock/reset/map stages pass. BLOCKER: PORT-GEOMETRY on xtier__seqhost__s_4N_C__7/8 = ft5 window [1630.656,1690.724] straddles cut 1684.8; clip makes the t2 end 10 um narrower than the src type window. No 8.64 lattice cut in 1555..1693 clears all N/S ft windows (ft0/ft1/ft5/ft2 back to back, gaps <= 1.2 um); store starts x 1693.44. J9 options: re-site ft5 slot windows wholly west of the cut (with matching neighbour-type windows), or a cross-type window row for the ft4_o ends.

## 02:5x update (after the 01:4x weekly limit; resumed 02:2x)
- GATE E GREEN (plan e a0a696072693): BIND 0, LAT 873/873 (same 4), G0 0 new, PRE PASS; gate-e bound tree raw refs 228, 0 over limit, anchors <= 0.09 um. HANDED to S81-J6-ASSEMBLY-R5 02:5x (hub 58a3c15461): j8_leaf_rg9_rawreset_delta.json sha dc684cd7a257 (75 types) REPLACES the plan d delta.
- RESPACE: posted 02:2x (hub 443a6b1af2): don't apply J7 ledger to my 75 types; re-run on composed plan; respaced plan e G0 0 new errors; J7 ledger double-counts my 4 lanes.
- Open: t39 proof (epyc7 GRT, waiter on chainB.log); t2 split J9 blocker (ft5 window straddle); leaf sign-off follows the J8 apply (11-23 04:15) via the wave.

## 11-22 08:xx-09:xx update (t31, J9 XRB)
- t31 J7 FAIL kit_topology "soft CS bank stale source": 24 soft_reg_banks rows stamped body 0b75bdfc, bound body 0dc5f53f, banks identical. Main fixes: 64adf7615668 (kit_topology selected_reset_context ignores clock.soft_reg_banks) + af3312b925a4 (soft_cs_placement restamps on body drift when the bank is identical). Wave t31 row (rt d6f543 per T1) still lacks it; fixed at J8 (tools >= af3312b925a4), no plan restamp needed.
- t31 J7 proof: epyc8 fork L/trees/s81_t31_j7 (tools.j7 = J7 tools, tools = rt da102e4d499a, native_bind/out fresh, out.j7 = J7 bind); bind via L/t31fix/r10_t31bind.sh (ot-run log intel2 L/t31fix/bind.otrun.log, markers R10B_*). Next: private-spec s81 ot_s81sl_leaf__t31 --tree L/trees/s81_t31_j7 --bind-out L/trees/s81_t31_j7/physical/die_plan/s81/plan_of_record/native_bind/out --rt da102e4d499a --host epyc8 --goal route, then run-item; read place for the wdo_q class.
- J9 row J9-LEAF-T31-XRB (COORD approved): intel2 L/j9/j9_t31_xrb_row.json; tools in main af3312b925a4: s81_vpw_xrb_overlay.py (define OT_S81SL_VP_XRB), s81_vpw_bank.tcl BANK-AFF (budgets.vpw_bank_aff_types). Proof kit after the J7 place read confirms the cause. -503 cause read: 5 gates + 17 repeaters; bank fill is name-ordered nearest-either so bank-0 FFs land at bank 1.
- 09xx sweep leaf rows t2/t12/t33/t44__clf6cf8492/t45/t47/t52 = BIND-GEN-TOOLSKEW, re-armed by WAVE-OPS-R1 1c8b40168f (t12/t47 a2 running); t65 = copy-back tar race (place passed), re-armed.

## 11-22 18:1x ownership sweep table (COORD 18:0x, OWNERS-SWEEP 98fd8f9f); event 18a2688b741 J7, read from autopilot/jobs a*.log
| type | last result | action |
|---|---|---|
| leaf t1 | live: a2 route running intel2 (dpkit-ot_s81sl_leaf__t1-283252) | keep; XRB proof kit (t31+t1 bind queued epyc8) = J9-LEAF-VPW-XRB |
| leaf t14 | @2 PLACE-SETUP-STOP -512 hi_sw->wdo_q, span 65, path 1649, 23 st | retired-to-J9: J9-LEAF-VPW-CONE (form a place_regions + form b SPR select reg); t14 = proof kit |
| leaf t74 | @2 -301 a_hs->wdo_q, span 37, path 1190 | retired-to-J9: J9-LEAF-VPW-CONE |
| leaf t31 | wave row cancelled by me; private twin (spec4, fork bind GREEN) running epyc8 | private twin + XRB kit; J9-LEAF-VPW-XRB / VPW-CONE |
| leaf t37 | @1 -817 vp_driver_g_sre_nm_r_q->vp_src_q[10], span 613, 26 st | retired-to-J9: J9-LEAF-SRE-SRC (station + depth split, draft) |
| leaf t8 | @1 -855 vp_driver_g_sre_nm_r_q->vp_src_q[97], path 1808 | retired-to-J9: J9-LEAF-SRE-SRC (same driver class as t37) |
| leaf t16 | @1 -462 vp_driver_xsw2_q->x_qd_q[199], span 519, 20 st | retired-to-J9: J9-LEAF-SRE-SRC (driver reach+depth, same row) |
| leaf t29 | @1 FAIL route GRT-0116 congestion | retired-to-J9: J9-LEAF-GRTCONG (read congestion map, draft) |
| leaf t54 cl501e5681, cl706d9749 | @1 FAIL route GRT-0116 congestion (both) | retired-to-J9: J9-LEAF-GRTCONG |
| leaf t51 | @1 FAIL place PLACE-HPWL 1.63x converged | retired-to-J9: J9-LEAF-GRTCONG (place density/region read with t29/t54) |
| leaf t21 | live: a2 route running epyc10 | keep |
| kv_leaf t4 | CANCEL-UNSIGNABLE 12:30 (TT -439, 3.7 h); its route docker dpkit-ot_s81sl_kv_leaf__t4-1087646 still alive on intel1 (not my PID) | retired-to-J9: J9-LEAF-VPW-CONE if the path is the vp write-out, else own row (path read next) |

## 11-22 18:3x J9-LEAF-VPW-CONE (COORD 21:2x/17:49 ruling: forms a + b, t14 proof)
- form (a) place_regions: plan epyc8 L/trees/s81_t31_j7/physical/die_plan/s81/plan_t14A.json (52693b0a0cca) = fork plan + t14 place_regions lcs_wdo_b0/b1 (inst_re u_vp_g_wr1_u_w.(wdo_q[k]|wmw_q[k]|g_slr.g_b[k].), near_re SRAM u_vp_u_b<k>, util .5, cone auto). Uses the GREEN fork bind (no rebind: place_regions is kit-only). Spec intel2 L/t14A/specA, run-item rt d0103507e0c2 launched 18:3x, log L/t14A/runA.log.
- form (b) S81-VPW-SPR: tool L/tools/s81_vpw_spr_overlay.py (scratch copy, not on main yet) = per (bank, slice) 6 one-hot data selects pre-decoded from the raw pins and registered on the XR edge (same edge as sv_q/sa_q), wdo_q D = one AND-OR level; 0 cycles; opt-in define OT_S81SL_VP_SPR; apply after XRB. iverilog lock-step bench SPR0 vs SPR1 PASS (19,996 cycles, 0 mismatches), select mutant FAIL (6,068); XRB1+SPR1 vs plain PASS.
- form (b) is folded into the queued XRB bind (L/t31fix/r10_t31xrb.sh, not started yet, epyc8 memory wait): after XRB it applies SPR and t14 verilog_defines += OT_S81SL_VP_SPR. One bind serves t31/t1 (XRB) and t14 (SPR); t14 spec after R10X_DONE.
- t31 plain-fix kit (spec4): kit_topology 0 (soft-CS restamp works), now src_manifest -> place.

## 11-22 22:5x COORD 22:4x (relaunch storm) + 21:1x (t15/t24/kv t3)
- HELD 10 leaf rows (kit_wave fb8c23cb04 + 2ef3be216d), "await J9 leaf rows", owner me, eta 11-24 12:00; running kits untouched:
  t14, t74 -> J9-LEAF-VPW-CONE; t37, t8, t16 -> J9-LEAF-SRE-SRC; t15 -> J9-LEAF-FT-DETOUR; t24__cl2456157b -> J9-LEAF-REACH;
  t53__cl958451dd -> J9 leaf sweep (PLACE-SETUP-STOP, class read pending); t21, t36 -> J9-LEAF-GRTCONG (GRT noconverge twice since 08:00).
- Probe (OT_PROBE_THROUGH=1 needs rt >= 0a84fc98a0ae; my forks' binds use da102e/d4aeaa = TOOLSKEW): chain intel2 L/probe/probe_chain.sh:
  intel1 fork L/trees/s81_probe_j7 -> fresh bind rt 0a84fc98a0ae -> private --goal route t15 probe kit (intel1). Log L/probe/chain.log.
- t15 ft-detour (3_detailed_place.rpt): ft0_i[16] input delay 480 ps (ft budget, vs 98.6 other inputs) + 450 latency = arrival 959 ps vs required 1060: ~100 ps left for pin -> u_ft_ft0_o_0 reg.
  The path is pin -> 7 wire buffers (~0.9 mm) -> port buffer input465 -> 7 buffers back -> reg 5 um from the pin, so the PORT BUFFER sits ~0.9 mm off the pin. Stage sites exist for ft stages 1-3 (y 906/595/286) but not for the port buffer.
  Row J9-LEAF-FT-DETOUR: site the port buffer of each ft*_i bit with its stage-0 reg (pin-slot site, FIRM), or skip buffer_ports on ft inputs. A DB trace (L/ft/ft_trace.tcl) is queued on epyc7 (load cap). Sweep: only t15 has the ft-port signature in every post-place marker since 11-19.
- t24 (436 um span, line[38] -> hw_d_q[78]) and kv_leaf t3 (610 um, vn rb_v_c -> u_x.q[21]): reach above 405 -> J9-LEAF-REACH (station on the hop, CBC). kv_leaf t4 is in the same sweep.
- SELREP bench: SR1 x3, dense x2 and SR0 x2 all PASS; off/mutant cases still running. SELREP bind on epyc7 is queued (fork L/trees/s81_sre_selrep).

## 11-22 21:2x (COORD 22:5x order)
- Hold etas -> 2026-11-23 12:00 (18 rows, kit_wave 3032208b20d5).
- J9 rows on hub: lanes/handoff/OPUS-FIX-S81-LEAF-R10-J9-LEAF-{GRTCONG,SRE-SRC,REACH}.json (post 21cf932456). GRTCONG J8 base f65f62779bef (copy intel2 L/grtc/plan_j8_cut_reset.f65f62779bef.json).
- Running: t68 probe chain intel2 L/grtc/t68_chain.sh (waits for intel1 probe bind; log t68_chain.log, run68.log); t13 GPL place kit L/grtc/spec13 run13.log;
  t1/t14 route kits on epyc8 XRB fork (L/xrbk/run_t1.log, run_t14.log); SELREP bind moved to intel1 (L/sre/i1_chain.sh, bind_i1.otrun.log, then t37 + kv_leaf t4 kits);
  ft trace relaunched unpinned (L/ft/t15.otrun.log; earlier exit 125 = duplicate docker mount); probe chain t15/t31/t14A2 unchanged.
- Open: t72 op asked from FIX-SYNC-S81; GPL sparse-exit tool defect for FLOW; t21/t36 congestion maps after current runs; SELREP to main with test.
