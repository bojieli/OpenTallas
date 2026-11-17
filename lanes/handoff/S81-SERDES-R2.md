# S81-SERDES-R2 handoff (Opus; successor of S81-SERDES-R (Fable, weekly limit to 11-22))

L = /srv/opentallas-scratch2/claude/fable-fix-s81-serdes (per host). Launch logs: intel2 ~/s81-serdes-r2/ (mine), ~/s81-serdes-r/ (predecessor).
Probes: E8 L/probes_serdes_r_1116 (h_worst.tcl, run_worst.sh TAG KIT ODB, h_parse.py, stage_hold_packet.py).
Gate: DRC 0, routed TT >= -42, internal FF >= 0; visual review before sign-off; export AGIdock /archive/opentallas-signed-1114 + rtx-pro.

## 18:4x PST state
- H (serdes__t13, E2): route running (unit oth-ubuntu-2519465, GRT). Pre-GRT FF hold repair after wns +2.27, setup still -147.62 (clk_t29 txl r[1]->q insertion skew, not t17/t26). Expect routed TT fail; H2 is the form fix.
- H2 (E8 L/H2/serdes__t13/gen/serdes__t13): north-strip tap rows (north_rows.tcl, OT_NORTH_TAPS t24,t17,t18,t27,t28,t29,t30,t23, y>1195): 288 strip FF moved to north taps, 549 near FF moved off. CTS running (unit oth-ubuntu-3807941). it2: clk_t17 407 (was 785).
- J4 (serdes__t14, E8 L/J4/serdes__t14/gen/serdes__t14): CTS exit 0 (pre-repair FF -353.02, 2303 ep, info). Approved HOLD-SDC be1 packet staged (J4_hold_packet_stage.json, sdc sha 3e0c65ac59ce8d4f, checker clean, backup J4_before_hold_packet). Route running (unit oth-ubuntu-3941217, J4_run_route.out). Post-CTS TT/FF census running (unit oth-ubuntu-3952985 -> probes J4_cts/).
- G3 (serdes__t1__clb45db5be, E8): CTS running (unit oth-ubuntu-3768458) on existing 48 ports. t48: per S81-DIE-R row clk_t48 = second sink on clk_t13 leaf (t13 window, pair <= 0.2 ps, common <= 1.81 ps TT); G3 pose (570 native FF over 1014 um) does not fit one t48 pin, so t48 not used in G3.

## Next
1. J4 census -> classes; J4 routed TT/FF -> if pass: visual review, sign-off, export.
2. H2 CTS -> census (run_worst.sh H2_cts) -> stage hold packet already present (H kit copy) -> route.
3. G3 CTS -> census -> hold packet -> route.

## 18:5x PST findings
- J4 post-CTS census (E8 L/probes_serdes_r_1116/J4_cts/, placement RC): TT worst -506.42, 614 endpoints < -42. Classes:
  - 394 = u_rm.g_rd[k].g_local.rpq / wp_g (clk_t12, insertion 539 ps; rm.mem 4096 FF at x~1733) -> u_rm.g_rd[k].q (clk_t14/t15, 297/~370 ps) at x 2350-2715. Data 983 ps = ~300 logic + 14 BUFx6f (~650 ps, 650-950 um). q's only load is u_bout_coll_o0 at x~2879 (east face). STRUCTURAL: rd.q placed too far east + t12 deep tree + -116 early source latency. H has rd.q beside mem (x~1080) and no such class.
  - 352 = io_pma_rck internal (-486.8 rck_transport q -> syn.am_ok; -101 u_chn -> lpl_w data).
  - FF worst -353.02: 400 = u_enc.d -> u_enc.d/ch_q split across clk_t22 (295 ps) / clk_t23 (656 ps).
  => J4 route (running) is information only; J family needs a J5 form: rd.q + its mux on the t12/mem side (rpq->q short) or an added rd.q->bout_coll stage, enc on one tap.
- G3 CTS 1st attempt exit 2: OT_RCK_AM_COHORT group 0 "far" (leaf_affinity radius 30 um from the majority leaf driver; FFs themselves compact, same as J4). Patched G3 kit rck_am_cohort.tcl (orig .G3_before_near): on "far" try each member leaf, nearest driver to centroid first, same clock/gating/cap checks, radius OT_RCK_AM_UM (default 60 um). Relaunched (unit oth-ubuntu-3991120, ~/s81-serdes-r2/g3-cts2.out; run dir G3 kit/r2_run_here because intel2 holds a stale G3 kit copy at the same path).
  G3 tap balance (1st attempt) already shows clk_t14 927 ps with 6129 sinks, t9 895, t13 777: expect a cross-tap TT/FF census like J4.
- Best candidate: H2 (H TT limiter was only cross-tap insertion skew).

## 19:0x PST
- H2 CTS exit 0: tap spread 233 ps (193..425; empty taps t23 t24 t31 t34 t6). Post-CTS census (probes H2_cts/): TT worst -150.06, only 15 endpoints < -42 (H: 24, worst -147.62): the clk_t29 txl class is GONE. Remaining: 12 reset-relay half-cycle hops u_rrl_N/q (fall) -> u_rrl_M/state (rise) across taps (rrl_33 t4 -> rrl_38 t11 -150.1: launch insertion 297 vs capture 182, hop wire ~350 ps), 9 rck u_rxf_q[532..] -> u_face_am3.parts -81.0, rck_transport -> am_ok -21. FF worst -260.01 (rck lpl_r.o -> u_chn 283, face_q_d -> rm.mem 92; ft*_i port class advisory).
- H2 hold packet (inherited from H, sdc f364d75fa1d07751, checker clean). H2 route launched E8 (unit oth-ubuntu-4059268, ~/s81-serdes-r2/h2-route.out).
- J5 (E8 L/J5/serdes__t14/gen/serdes__t14) = J4 + rdq_local.tcl (POST_GLOBAL_PLACE wrapper: runs rck_transport_mid.tcl, then puts each u_rm.g_rd[k].q at its D-side mux driver like H). Place+CTS launched (unit oth-ubuntu-4079683, j5-cts.out).
- Next for H family: if routed rrl hops still < -42, H3 = capture relay cohort on the launch tap (OT_TAP_GROUP_FIXED) or a tighter half-cycle hop (<= ~250 um).

## 19:2x PST - H3 (reset-relay boundary form)
- Cause (H2 census): every remaining TT relay failure is a half-cycle hop q(fall) -> next state(rise) of ot_dp_rrelay_nl that CROSSES taps (lck/cck 297/182 etc. + early source window) with a ~250-450 ps hop wire. Same-tap nl hops of 375 um pass. H2 bind has 127 hops; 34 nl hops cross taps (actual H2 CTS taps, probes H2_cts/clk_all.txt), 25 launchers.
- Form fix (cycle-neutral): launcher of a cross-tap hop = plain ot_dp_rrelay (posedge q, full-cycle hop). nl: state@k, q@k+0.5, next@k+1; plain: q@k, next@k+1 -> same latency, LATCHECK unchanged. Hold across taps on a >= 250 ps hop is easy; hold repair covers the rest.
- H3 = H2 kit + rtl/s81p_serdes__t13_bound.sv with u_rrl_{0,7,11,17,23,30,33,42,45,49,57,58,62,72,86,93,96,101,115,117,118,123,125,130,132} nl -> plain (orig .H2), resynth (OT_ALLOW_RESYNTH=1), goal cts. E8 L/H3/serdes__t13/gen/serdes__t13, ~/s81-serdes-r2/h3-cts.out. lec_async.sh not copied (LEC skipped, advisory).
- To count H3 the die bind generator must emit the same rule (owner: S81-DIE-R2 / reset plan). Posted.

## 19:3x PST
- G3 CTS exit 0 after the cohort fallback (group 0 nearest leaf clknet_leaf_434, worst member 30.2 um). Census (probes G3_cts/): TT -974.56, 1022 endpoints < -42; FF -645.75. Tap insertion 219..927 ps (t13 1163, t14 1240, t20 1146, t9 1189 max): rrl relay cross-tap hops -700..-975, rm rd.q class -717 (same as J4). G3 PARKED: no route. Its tap plan needs re-pitching (OT_TAP_CHECK says <= 117 um) plus the J5/H3 fixes before it is worth another CTS.
- J5 at GPL (3_3); H3 at synth. H route E2 + H2 route E8 + J4 route E8 running.
- Order to close: H2 routed numbers -> if only rrl class remains, H3 is the sign-off candidate (needs the bind rule adopted).

## 19:4x PST - H3 replaced by H3p
- H3 (hand-edited bound.sv, 25 relays) STOPPED by me (unit oth-ubuntu-4181890, exact cmdline checked) after synth: hand edit left rtl/bound_reset.json bound_rtl_sha256 stale. Tree L/H3 superseded (delete later via ot_delete_guard; contains root-owned docker files).
- H3p = H2 kit + the sanctioned tool tools/die_plan/bound_reset_edit.py --plain (copy at E8 L/probes_serdes_r_1116/die_plan_tools/): all 90 ot_dp_rrelay_nl -> ot_dp_rrelay, relay_lockup removed from the tree, depth map unchanged (134 relays), hashes restaged (H3p_plain_edit.json, bound sha e55e8d12...). Resynth -> CTS running E8 (~/s81-serdes-r2/h3p-cts.out). lec_async.sh kept.
- Die-bind side: this is plan event "relay_lockup.types minus the serdes types" (results/die_s81_85_serdes_plainrelay_1109). Asked S81-DIE-R2 to apply it to s81 reset.relay_lockup so the bind emits plain relays for serdes types.

- 19:3x J5 rdq_local: 512 rd.q moved (mean 755.1 um, max 980.0 um), 5967 D-side buffers, 0 skipped.

## 19:5x PST (resumed after limit; Codex 19:51 handoff read)
- H2 post-GRT (5_1_grt, in-flow repair): setup ws -57.76 / tns -71.35, 3 violations, ALL the reset-relay hop u_rrl_33/q (fall) -> u_rrl_38/state (rise); hold ws -5.38 = port path ft2_i -> u_ft_ft2_o_0 (advisory), internal FF hold +0.17 after GRT hold repair (+19 buffers); overflow 0, antenna 0. DRV: boot_release.released_n slew. H (E2) same picture (-58.63). => per COORD, H3p is the sign-off form. H2/H DRT continue as information.
- H3p at place (3_1); Codex real LEC on H3p live E8 unit oth-ubuntu-439937 (probes H3p_real_lec/). J5 CTS done; Codex J5 census live E8 unit oth-ubuntu-546825 (probes J5_cts/).

## 20:1x PST - J5 PARKED
- J5 post-CTS census (probes J5_cts/): TT -1138.95, 817 ep < -42; FF -521.7. Moving rd.q to its mux put the whole span on rd.q -> u_bout_coll_o0 (399 ep, -1139), and rd.q landed on clk_t28 whose tree is deep (launch arrival 1206 ps vs t15 capture 996); also rt_d -> rd.q -242 (240 ep), txl t21 -> t28 FF -482.
- Conclusion: the J floorplan puts rm.mem ~1150 um from the east output face; one register cannot split that span with these trees. J family needs a floorplan move of rm toward the output face or an added rd.q -> bout_coll stage (RTL). Not pursued now; H3p is the sign-off form.

## 20:4x PST - H3p attempt 1 failed at GPL, resumed
- H3p synth+floorplan OK, 3_3 GPL hook failed: "OT_BOOT_RELEASE expected3 kept stages, found 2" (serdes_boot_release_local.tcl, sourced by post_global_boot3.tcl). Fresh Yosys names stage2's DFF u_boot_release.released_n (rq kept only as a net alias); the older selector matched only g_stage[k].rq. The newer H_boot_selector_public.tcl already handles this (reproduced: it finds 0 1 2 on H3p 3_2_place_iop.odb).
- Fix (kit copy+mv, orig .H3p_before_alias): the same released_n -> stage2 rule in serdes_boot_release_local.tcl. Resumed at place (resume.json start place, reuse synth/floorplan), ~/s81-serdes-r2/h3p-cts.out. This is a flow-family bug for any SerDes t13 kit that resynthesizes; worth a source fix in tools (serdes_boot_release_local.tcl).
