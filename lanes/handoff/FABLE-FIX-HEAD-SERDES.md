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

## CODEX active continuation 11-16 22:4x PST
- sd9c GRT TT repair terminal FLOW ERROR GRT-0228 (usage65535 limit4000 at2790,82) after1230iterations; plateau TT~-95.7 /3605ends. FF+0.24/0overflow before repair is retained. No blindretry/DRT.
- sd9d a3 retained, E8 same kit. CTS TT repair kept -15.70; pregrt FF all pass8921hold buffers ->+5ps, xt pass3573ends running. Note private -setup_margin60 constrains FF scene setup, NOT measured TT; cannot claim TT protection until GRT read. No new cycle vs sd9c.
- NEW sd9e (private, defaultoff, not adopted): NF15d2 exact89rrl+66srl wrapper + existing OT_S81_RM_STAGED, with RPC32 read-select replicas retained by source claude/head-rm-stage-rpc-1116 @2ed6548bbb5. +1coreRXedge (833ps) vs sd9c/sd9d, unchanged2pmaRXedges DKREG1/DOREG1. Adds1088FF (512write-data+512read-stage+64write-enable), same8x512 FIFO/64Bcycle boundaries. Model BEFORE RTL and exactness are committed in results/head_rmstage_1116/;4cases223488comparisons PASS, no-stage55872 and stale-slice130 mutants DETECTED. Normal gate GREEN3/3 main800d3f3a9c4 after MQ_SPARSE memory closure fixed initial INFRA; READY posted, coordinator approval pending.
- sd9e GEN initially found canonical NF15d2 wave_prepare.json published_wrappers.hd_serdes.sha256 stale2cad3c61 vs actualpublished8a2e0eed; HEAD parent owns corrected NF15d3 publication. Failed a1/a2 dirs retained as sd9e_genfail_a1_prepared_plan and sd9e_genfail_a2_stale_wrapper_receipt. Private candidate receipt declares candidate plan digest + actual published wrapper, then stock exporter independently regenerated/token-compared exact wrapper: PASS. No immutable tree edit.
- sd9e E10 generation unit oth-ubuntu-3374582-1794897606 exit0; kit source guard0 mismatches, reset/bootstrap SHA51265c8e86cf identical, PREFLIGHT PASS0. Private plan sets rem_q group fixedclk_t8, followersOFF, same macroshape; measuredhold505aabb and sd9d pregrt margin hook staged prospectively before any job.
- sd9e floorplan/render LOOKED before launch: fulloutline+southern400um zoom; Chien below SRAMpair with20um channels, no overlap/wall. Review+PNG at sd9e_lane/results/geom_review/sd9e_pre_route_review.json and sd9e_floorplan.png (replicas E7/E8/E10). At place/GRT inspect RM staging distances and encoder grouping.
- sd9e GRT-goal RUNNING via intel2 ot-run client784568; LOAD-SPILL chose localhost in intel2 context = tolerant-swine/intel2, unit oth-ubuntu-787742-1794897979. Active kit absolute /srv/opentallas-scratch2/claude/fable-fix-head-serdes/sd9e_lane/sd9e/gen/hd_serdes; log run_grt.log on intel2; ot-run client log ~/fable-fix-head-serdes-logs/sd9e_grt.log. Source+output-backcopy host E10, replicas E7/E8. No restart; next read GRT classes/throughput and LOOK image before DRT. No actual LEC or physicalqualification claim.
- CORRECTION to the 22:4x setup-margin caution: full runner/header confirms TLIBS=TC_LIB_FILES is supplied alongside BC PLIBS, with TC/tt and BC/ff scenes (TT hold false, FF setup false). The60ps setup margin DOES protect actual TT in this coupled scene. The earlier FF-only inference from log tail was wrong. sd9d hold stage completed12,741hold cells, internalFF+4.94, TT setup-15.70 unchanged. No source change needed.
