# QC-FORMS-2 handoff (Opus; successor of HARD-QC-FORMS-1; QC hard type forms; COORD coordinates)

Started 2026-11-13 06:55 PST. Same scope as HARD-QC-FORMS-1 (read lanes/handoff/HARD-QC-FORMS-1.md first): the unowned DIEVIEW-QC-1113
findings (a) su_l1 / su_c walls, (b) coll_core, (c) CB window binding + tap windows, (d) stm x11 ROM row + ROM-read pipeline,
(e) setup negative at CTS (st_a). Deliver: plan deltas to DIE-QC-100 for s29 (adopted after the 11-15 04:00 freeze), RTL/tool
READY branches off origin main, proof builds (private, DO_NOT_COUNT) through place / GRT / route with renders viewed.

## Where
- Form work dir (inherited): epyc7 /srv/opentallas-scratch2/claude/hard-qc-forms-1 (tools/form_*.py + hqf_apply.py, forms/, plans/, out/street_*.json, png/).
- Build pipe (inherited): epyc9 /srv/opentallas-scratch2/claude/hard-qc-forms-1/pipe (README.md). chain_qc.sh now has BUILD_HOST=auto
  (ot-run picks the host, kit staged with --stage; old copy chain_qc.sh.bak-hqf1). run_q2.sh TAG PLAN TYPE.. = rebind + chains. Logs pipe/logs/q2_TAG.out, pipe/runs/TAG/TYPE/chain.log.
- RTL worktree: epyc7 hard-qc-forms-1/wt, branch claude/hard-qc-forms-1-rtl-1113 @aab1fcfe0c (on hub), off 24b08535da.
- Local scratch: localhost scratchpad qf2/.

## Forms (plan base s28 head 736058c458ee; bound base 9f3ed3486d81)
| form | types | what | street_rule (59858adeb6) |
|---|---|---|---|
| F-STM | 11 stm | 4 tload ROMs as one 2x2 block under the N window (x 77.76/246.24, y 1537.92/1602.72) + define OT_QC_TLOADCAP | 11 face_street -> 0 |
| F-STA-RTL | 9 st_a | define OT_QC_SWREG (u_scale_wait registered output, 0 cycles) | n/a |
| F-SUC | 3 su_c | middle core row +25.92 x, u_cl -8.64 | sle 2 -> 0; slw 3 -> 1 (u_va behind 735 W pins, open) |
| F-COLLCORE | coll_core | face_1 bank[0] SRAM x 17.28 -> 60.48 | face_street 1 -> 0 |
| F-SUL1W | 2 slw_su_l1 | lanes re-pitched to 43.2 streets, u_lane4 129.6 off S, E rings -25.92, N ring -30.24 | 7 -> 0 each |
| F-CB (candidate) | 3 cbn_q00 | col-0 tiles +12.96 x, top row -51.84 y, N rings -12.96 | 3 -> 1 each; window-to-tile binding not yet formed |

## Proof builds (private, DO_NOT_COUNT; started 07:0x PST)
| tag | type | plan | state |
|---|---|---|---|
| base | sle_stm_v2__cl7b3062fa | ev2st_g1 bound | place on epyc4 (pinned, started by HQF-PIPE 06:38) |
| fstm | sle_stm_v2__cl7b3062fa | bound_f_stm 71f7cb02b513 | rebind -> chain |
| fsta | sle_st_a_v2 (MEM 96) | bound_f_sta 38fb4171f467 | rebind -> chain |
| fsucoll | sle_su_c, coll_core | bound_f_su_coll 2dd3bbdeaaa9 | rebind -> chain |
| fsul1 | slw_su_l1__cla2a78701 | bound_f_sul1 13fa49bcbac3 | rebind -> chain |

## State log
- 07:1x Took over. Benches re-run at aab1fcfe0c: swreg base PASS / N=1 FAIL / MUT FAIL; tloadcap N=1 PASS / N=0,2 / CAPTURE_MUT / warm-reset mutant FAIL.

## 2026-11-13 07:26 PST state at handback (COORD: the Fable limit reset, so HARD-QC-FORMS-1 takes the scope back; no job cancelled)

### Pipe changes (epyc9 hard-qc-forms-1/pipe)
- chain_qc.sh has AUTO_HOST=1. BUILD_HOST is then only the data host (default epyc4, where W is rsynced). ot-run runs with --stage W instead of --hosts, so it picks or spills the host. epyc9 is not an ot-run fleet host, so a data host is needed. The pre-change copy is chain_qc.sh.bak-hqf1 and my edit base is chain_qc.sh.orig (localhost scratch).
- run_q2.sh TAG PLAN TYPE...: waits for a running rebind of TAG, then rebind_qc.sh, then TYPE1 rtl+gen (it stops when that fails), then all chains to route in parallel. Logs are in logs/q2_TAG.out.
- fwd_repoint.py PLAN TYPE_RE OUT REP, run from the tree root. This is R-REACH-4 after a form move: it re-points every forwarded clock output to the nearest tap of the current tap_grid. It is NEEDED. Every core or macro move renumbers the derived taps. The first F-STM bind failed with EMIT "slw_stm_v1__cle34a73c3 forwarded clock source clk_t79 is not a planned physical tap input", and the other sources silently pointed at taps 150-1,500 um away. Changes: stm 71, su/coll 41, su_l1 17, cbn_q00 12. The CB base already has clk_t24 at 2,826 um.
- form_stm_reach.py (F-STM-REACH, new): adds internal_stations to stm x11 for x_su_l0_i / x_su_l1_i (S face, 1,097 um: 3 stations, +3 cycles) and x_fe_i (E face, 969-1,099 um: 2-3 stations), toward home rect [86.4,1101.6,527.04,1502]. Then reach_fix.sync_fixed_cycles runs: 35 lanes, 0 rule broken. Evidence is the old-floor STA (epyc4 hard-qc-forms-1/sta/sec_sle_stm_v1): u_stream wd_q -> lane_c over 1.0-1.2 mm with 5-10 cells, -400..-644 ps on 697 endpoints, plus u_cland_x_fe_i ring -> top regs at -258 on 542. This class is SEPARATE from the ROM / TLOADCAP class (1,086 endpoints, -652). BUG: it writes reach_homes, which the pipe tree schema rejects ("unknown key reach_homes", 11 errors, one per stm type). Drop that key, or wait for the RULES-REACH-1 schema merge (claude/rules-reach-1-1113 is not on main). fstm3 may fail at bind or schema for this reason.
- s29/compose_qf2.sh BASE OUT: composes F-STM, F-SUC, F-COLLCORE, F-SUC2, F-SUL1W, F-CB and F-STA2 (guarded hqf_apply), then fwd_repoint, then F-STM-REACH. On head 736058c458ee it gives plan_of_record/zz_qf2_s29forms.json 11618cec4513. s29/gates_qf2.sh results: schema FAIL (reach_homes); G0 11 errors (read g_forms/g0/g0_report.json; probably the same key); street_rule on the composed plan: 20 types with violations out of 73. The head comparison run in s29/g_head was still going.

### Forms added by me
- F-SUC2 (tools/form_suc2.py on epyc7): su_c x3, u_va and u_vb +17.28 x. u_va's physical_ft is the tied ft_ck/ft_rst pushdown, not the cws1 ft, so no seam event is needed. With F-SUC, all 3 su_c types and coll_core reach face_street 0 (out/street_fsuc2.json).
- OT_QC_PINKEEP RTL: branch claude/qc-forms-2-pinkeep-1113 @17e7e452ca on hub, stacked on aab1fcfe0c, NOT posted READY. qfd_dv_s8_station_tail1 g_pin becomes a keep_hierarchy qfd_dv_station_copy under the define, 0 cycles. Measured cause: yosys merges the identical pin registers of the 4 st_a regions, so u_u_r0.g_pin drives the r0/r1/r3 u_h9 SRAM inputs (-442/-159/-200, 27 endpoints). In the ORFS yosys a plain (* keep *) on the reg does NOT stop the merge (bench/keeptest on epyc7: 3 instances gave 4 DFF, not 12). NEXT: confirm on the fsta2 kit 1_synth netlist that g_pin has 4 x PW flops, then post READY. Plan form f_sta2.json = SWREG + PINKEEP on the st_a x9 types. The pipe tree tail1 already carries the patch.
- RTL READY posted 07:0x for claude/hard-qc-forms-1-rtl-1113@aab1fcfe0c (TLOADCAP + SWREG). Benches were re-run at that sha and pass with the expected mutant and wrong-N FAILs. Train 46: COORD reports it approved, with the merge lane landing 28be9ae16c. I did not check that merge.

### Proof builds (DO_NOT_COUNT, epyc9 pipe/runs/TAG/TYPE/chain.log)
| tag | type | state at handback |
|---|---|---|
| base | sle_stm_v2__cl7b3062fa | cts (pinned epyc4, HQF-PIPE) |
| base | cbn_q00__cl622f65d2 | gen, then place via ot-run AUTO_HOST |
| fsta | sle_st_a_v2 (SWREG) | place via ot-run, MEM 96 |
| fsta2 | sle_st_a_v2 (SWREG+PINKEEP) | rebind |
| fstm3 | sle_stm_v2 (ROM block + TLOADCAP + repoint + REACH stations) | rebind (watch the reach_homes schema) |
| fsuc2r | slw_su_c__cl92142dac (F-SUC + F-SUC2 + repoint) | rebind |
| fsucr | sle_su_c, coll_core | FAIL kit-rtl: bind EMIT slw_su_c__cl92142dac cws2_o "writer START raw reset rst_rl_145 has no registered wavefront driver" + RESET_ANCHOR rst_rl_6 411.6 > 405 |
| fsul1r | slw_su_l1__cla2a78701 | FAIL kit-rtl: EMIT slw_su_l1__clcc9d0155 reverse collector rst_n_t29->rst_rl_72 490.9 um > 405 |
| fcbr | cbn_q00__cl622f65d2 (F-CB) | FAIL kit-rtl: EMIT reverse collector rst_rl_122->121 428 um; RESET_ANCHOR cbn_q00__cldbcda913 |
| fstm (old) | | FAIL (dangling clk_t79 + first auto-host bug), superseded by fstm3 |

KEY FINDING for every core-moving form: a core move changes the derived taps, so the reset tree (anchors, collector hops, START raw reset) needs DIE-QC-100's bind_fix steps (reset_pad, then reset_repick, then tap_ident) BEFORE rebind_qc.sh. A plain re-bind of a moved-core plan fails EMIT on some type, and that kills kit-rtl for every type in the bind. I started reset_pad.py then reset_repick.py on the F-CB plan in the private tree (pipe/rp/, plan_of_record/zz_pad_out_qf2cb.json then zz_rp_out_qf2cb.json; repick alone refused: "cbn_q00__cldbcda913 reset tree got shallower 11 -> 10 (must pad)"). Do the same pad and repick for the su/su_l1 plans, then rebind.

### Findings
- su walls (a): F-SUC + F-SUC2 + F-COLLCORE + F-SUL1W bring face_street to 0 on su_c x3, coll_core and slw_su_l1 x2 (plan level). Not built yet, because of the reset-tree EMIT above.
- coll_core (b): 1 SRAM move. Its START sites and fwd taps are hand items (RULES-REACH-1). The repoint fixes 5 of its forwarded outputs.
- CB windows (c): core_conns give t00 (S end) <- na_i00 / nb_i00 (N face; nb comes from the quad above, cbn_q01 u_t12 S window x 1142-1231). t00.n_y -> y_o00 (S, to slw_hc0). t10.n_y / t01.n_y -> t11 -> y_o11 (E top, to cbx_q10). So the N->S transit is inherent in the quad's dataflow. Swapping or mirroring the tile rows trades 1,030 transit bits (na+nb) for 515 (y_o00) but adds +1 cycle on the max(na,nb)+y path (9 -> 10 stations) and needs the y_o11 and y_o00 windows moved: not recommended as a type form. What helps: F-CB strips, the CB fwd-clock repoint (2.0-2.8 mm -> 15-47 um), and the 150-160 ps tap windows as a DIE-CLOCK item (not a type form). Old-floor STA (epyc4 sta/sec_cbn_q00): <top-reg> -> cland_* ring dch -1.5..-2.9 ns (START fan, R-REACH-1), nb ring -> top-reg -1,326 on 514 endpoints, fab x stations -1,370.
- stm (d): two classes. ROM -> tload (TLOADCAP + ROM block). u_stream S-window reach (F-STM-REACH).
- st_a (e): SWREG covers 232 of the 602 failing endpoints (-465). PINKEEP covers g_pin (27, -442). Left: u_btab SRAM -> u_bt (160, -79), cland_rs_s1 ring (64, -96), r3.g_nb (64, -79), u_skn (14, -77). These are small, but every one is negative.
- Renderer: unchanged (epyc7 tools/tr.py from HARD-QC-FORMS-1). I viewed base and F-STM stm, base cbn_q00 and F-SUC sle_su_c, all plan-level. No build render exists yet.

### Next steps
1. For the su/su_l1/CB plans: reset_pad, then reset_repick (tap_ident if needed), then rebind_qc.sh, then run_q2.
2. F-STM-REACH: drop reach_homes, or merge the RULES-REACH schema first. Then rerun compose and gates, and compare with s29/g_head.
3. Watch fsta / fsta2 / fstm3 / fsuc2r / base runs. Pull renders (png on epyc7 hard-qc-forms-1/png), view them, and post RESULTs.
4. Post READY for claude/qc-forms-2-pinkeep-1113 after the synth flop-count check.
5. Deliver the s29 delta package to DIE-QC-100: forms/*.json + compose_qf2.sh + fwd_repoint.py + form_stm_reach.py + gate/street reports.

HANDBACK 2026-11-13 07:26 to HARD-QC-FORMS-1
