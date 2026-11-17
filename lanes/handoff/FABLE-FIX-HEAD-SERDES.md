# FABLE-FIX-HEAD-SERDES handoff (Fable; owner of HEAD type hd_serdes through sign-off + export)
Logs: intel2 ~/fable-fix-head-serdes-logs/. Lane dir: epyc8 /srv/opentallas-scratch2/claude/fable-fix-head-serdes/sd9d_lane (meas/, sd9d/). Clone: epyc10 /srv/opentallas-scratch2/claude/fable-fix-head-serdes/repo.
Gates: DRC 0, routed TT >= -42, internal FF hold >= 0. 0 added cycles vs sd9c (+2 RX DKREG1/DOREG1 as sd9c). Core shapes untouched.

## 11-16 21:15 PST (05:15 UTC 11-17)
- sd9c first GRT (unit oth-ubuntu-4115587-1794884149) ended exit 2 with NO 5_1_grt.odb: GRT 0 overflow (the last capacity-0 tap gcell cleared in
  iterations 21-30; GRT-0273 dropped the NDR on 8 tap nets), GRT hold ws -30.20/39 added 0, then flow error
  `OT_VCLK_MEASURED_HOLD: pin-register mean unavailable (samples 1669 missing 0 clocks 2)`. Cause: pma_rx[*] native pad inputs (pma_rck) walked
  as vclk boundary inputs. No DRT was spent. Log kept: kit run_route.log.sd9c_a1_grt_exit2.
- FIX branch claude/head-vclk-native-pad-1116 @505aabb1157dc71e982f3810f1343cdc5bfafa9b (2 files), normal gate GREEN 9/9 on main d1fa289b1cb,
  READY posted 21:1x. r420 coherence b56e08e96e1 IS in origin/main.
- sd9c kit (epyc8 /srv/opentallas-scratch2/claude/head-sd9a/gen/hd_serdes): vclk_measured_hold.tcl replaced copy+mv (old in
  source_gen_replaced/), tt_setup_repair.on both -> grt (CTS TT repair is already in the kept 4_cts.odb), resume.json start=grt,
  record sd9c_r1_resume_record.json. GRT resume (GOAL=grt, never DRT): unit oth-ubuntu-1348301-1794891703, kit log run_grt_r1.log,
  client ~/fable-fix-head-serdes-logs/sd9c_grt_r1.log. NEXT: read rem_q at GRT (meas.sh below).
- sd9c 4_cts.odb read (meas/cts, placement RC, TT wns -15.70 = u_rm rp_g2 -> mem, pma_rck): u_enc.rem_q = 300 flops in x 1247..1384,
  y 161..254; 167 on clk_t10, 133 on clk_t8. 31 endpoints below +60 ps TT have an HB4 directly on the D pin; rem_q worst -11.79
  (rem_q[272] -> rem_q[136], hold61573 on D). Prediction of FABLE-PD-HEAD-2045 holds: sd9c misses on rem_q.
- SUCCESSOR sd9d (epyc8 .../sd9d_lane/sd9d/gen/hd_serdes, script sd9d_lane/gen_sd9d.sh, flow tag head-serdes-sd9d):
  1. plan copy: u_chn 1548.0,109.44 (as sd9c) + clock.tap_group {"re": "(?:^|[/.])(u_enc)[/.]rem_q"} -> OT_TAP_GROUP_RE (all rem_q on one tap);
  2. pregrt_ff_hold.tcl: repair_timing -hold gets -setup_margin from config.mk OT_PREGRT_HOLD_SETUP_MARGIN = 60 (TT scene);
  3. vclk_measured_hold.tcl = branch 505aabb; reset_tree.tcl = sd9c coherent tree (sha 5be86bfb2b5a). Gen copies in source_gen_replaced/.
  Launched GOAL=grt: unit oth-ubuntu-1453022-1794892337, kit log run_grt.log, client ~/fable-fix-head-serdes-logs/sd9d_grt.log.
  NEXT: at GRT run meas.sh (rem_q slack, taps in remq_taps.tsv = one tap, HB4-on-D count), LOOK place + grt renders, then
  `ot-run ... bash gen/run_route.sh route` with resume.json start=route; after DRT: sign-off, one HEI insert pass if internal FF < 0 (TP2 recipe,
  epyc7 hold1/run_route_signoff.sh), export (ffht_export.sh pattern) to AGIdock + rtx-pro, tell HEAD-DIE-R.
- Tap gcell: no separate change. tap_pg.tsv shows no clean PG cause (flagged taps t4/t7/t12/t16 have no M5/M7 stripe within a gcell); GRT itself
  ends at 0 overflow after the NDR drop. If DRT fails at a tap pin, it is the plan item of the review (tap landing sites, HEAD-DIE-R).
- Measure tool (read-only on the kit): sd9d_lane/meas/meas.sh KIT OUT ODBNAME grt|placement via ot-run --stage both paths.
- OPEN: the setup-margin knob is a kit edit only; port it to tools/die_plan/pregrt_ff_hold.py (default 0) once sd9d proves it.
  HEAD-DIE-R plan event must carry u_chn 1548.0,109.44 + coherent wrapper + clock.tap_group for hd_serdes.

## 11-17 01:00 PST (09:00 UTC) -- state after the limit pause
- r448 claude/head-vclk-native-pad-1116@505aabb1157 IS in origin/main. Measured-hold fix proven on both kits (samples 1125, FF mean 386.8, band PASS).
- sd9c GRT resume (exit 6) and sd9d a3 (exit 6): GRT 0 overflow, GRT hold ws +0.24 (+122 cells), 5_1_grt.odb written, then the kit's
  GRT-stage TT repair died with a TOOL error after repair_design had buffered 1218 nets inside the same incremental route session
  (sd9c `GRT-0228 Horizontal edge usage ... 65535`, sd9d `RSZ-0074 Failed to build tree from global routes ... net41592`); FALLBACK kept
  the unrepaired DB, so the gate reads setup_est -166.87 (sd9c) / -169.19 (sd9d), SETUP_TRIAGE FAIL. No DRT spent on either.
  Mid-repair wns before the crash: sd9c -95.2, sd9d -87.8, both on u_rm.mem[*][*] (pma_rck domain, tree insertion 1148 ps, 84 density taps).
- sd9d attempts: a1 (group on nearest tap clk_t10 -> tap full at cap 1000) and a2 stopped by me at CTS: OT_TAP_GROUP_RE also arms
  ct_follow (reset relays u_rrl_* re-hung, 3 far sinks on clk_t15: tree 208-474, tap mean 220 vs 450). a3 = config.mk
  OT_TAP_GROUP_FIXED = u_enc:clk_t8 + OT_TAP_FOLLOW_RE = (empty), resumed from 3_place.odb (resume.json start=cts). Tap counts = sd9c except
  clk_t8 756 / clk_t10 738; tap means 396..460 class as sd9c. Logs of a1/a2 kept in the kit (run_grt.log.sd9d_a1_*, _a2_*).
- sd9d GRT DB measured (meas/sd9d_grt, GRT RC + OT_RC_SIGNAL, UNREPAIRED): rem_q 300/300 on clk_t8; worst rem_q[107]->rem_q[187] -153.5 with
  CRPR +56.0 (tap window recovered), launch 506.6 / capture 488.9, no hold cell on the path; data 961 ps (QN 188.6 ps, XNOR2x2 88-105 ps =
  unsized loads at GRT RC). Families below 0 (unrepaired): u_rm.mem 2676 (-169.2), rem_q 246 (-153.5), u_rm.r_d recovery 105 (-132.5, reset
  fanout slew 326 ps), u_syn bm thq/d/gm/dz ~600 (-128..-106), enc pp1/pp0 221 (-103). HB4 on D with TT slack < 0: 69 (112 below +60):
  the setup-margin 60 at placement RC does not stop them (slack there is far above 60); the audit must run at GRT RC.
- Placement-RC TT (-15.70) is NOT a predictor here: GRT RC with the routed signal C reads ~150 ps worse before TT repair. The GRT-stage
  TT repair is the step that decides this type.
- Renders LOOKED (sd9d place/layout.png + grt/congestion.png): 3 cores clustered in the south logic strip, PHY region clear, no overlap; logic sits
  in tight round blobs at 100 % GRT usage (10036 gcells > 90 %), strip background 70-80 %. PASS-COND for route; the blobs are the likely cause of
  the GRT-RC data-path loss (advisory: spread the enc/u_rm/u_syn clusters).
- RUNNING: private TT repair of sd9d 5_1_grt.odb with the incremental route closed/re-opened between repair_design and repair_timing
  (meas/ttfix.sh -> meas/sd9d_ttfix/{ttfix.log,5_1_grt.tt.odb,route.guide.tt}; E8 unit oth-ubuntu-4083674-1794905285, client
  ~/fable-fix-head-serdes-logs/ttfix_sd9d.log). NEXT: if it completes, measure (meas.sh with the .tt.odb), and if TT >= about -25 install it as
  5_1_grt.odb + route.guide in the sd9d kit (kit idle; copy+mv), resume.json start=route, GOAL=route; port the fix to
  tools/die_plan/tt_setup_repair.tcl on a branch. If wns stays near -88 on u_rm.mem: that family (pma_rck rp_g2 -> mem write enable, 3072+
  loads) needs its own structural form (enable register per mem row group / placement bound of u_rm next to its taps), 0 cycles preferred.
