# S81-SERDES-DPL CODEX handoff

## Completed
- Source guard `55b26f86497` on inherited `claude/fable-fix-s81-serdes-1116`: explicit `ct_group_owned` survives both `ct_follow` passes, ordinary unowned followers retain their second-pass behavior. Focused16/16 PASS, guard-removal mutant reproduces original split.
- Production-shape t14 ready94 clock cohort CLASS PASS; record `978eeface1f` at `results/physical/s81_serdes_ready94_cohort_1116/result.json`. Nominal current policy0 setup/25hold TT +267.961ps. Matched strict60 sensitivity: oldC -947.280151 -> cohort94r3 +207.961487ps, gain1155.241638ps. No whole-type signoff; globalFF screen -485.47/2185 and other classes remain.
- Actual preCTS assignment proof preserves12 source/collector locations/status/nonclock-pin maps. Only q94/state clocks clk_t23 -> clk_t7; fixed ready/fault alreadyclk_t7. Review `a688a92c978`, image epyc7 `fable-fix-s81-serdes/reset_probe/anchor/cohort94.png`.
- Typed t14 row/trace: `lanes/handoff/S81-SERDES-DPL-clock-cohort-{rows,trace}.json`. Source guard required before row adoption. Actual CTS private kit epyc7 `fable-fix-s81-serdes/cohort94r3/serdes__t14/gen`, unit oth-ubuntu-3120658-1794854996 exited0. Its generated `clock_taps.tcl` preserves original landing_exports footer; canonical file alone is not a kit replacement.
- Previous cohort94 partial-replica/preflight and dropped-export CTS-0114 failures retained, not overwritten. R3 successor corrected construction.

## t13 geometry and authority cone
- Actual C3_3 lock_sync1 FIRM at(1656.720,1222.290) intersects u_ptx macro ending1222.560, exactly CORE north. DPL evicts stages to opposite sides, causing1192um sync wire and -660.73.
- SAME-OUTLINE fix sent plan owner: translate BOTH PMAs y-27um, preserving shapes/outline/Nface anchor; TX/RX gap stays10.8, lowerRX gap to otherhardmacros263.508. Move io_pma_rck padclock y1090.8->1063.8; regenerated macro-referenced pads/flops/clock sites follow. Exact canonical row `lanes/handoff/S81-SERDES-DPL-t13-pma-pair-dn27-rows.json`; image epyc7 `reset_probe/anchor/t13_pma_dn27.png`. FrozenF2s3 untouched.
- Private anchor-aware helper `reset_probe/anchor/reset_anchor_local.tcl` (not yet production source): on moved-PMA preview compacts49 authority-only cells, area6.75054um2, preserves FIRMlock_sync1;34cell pin/net/fixed-site identity PASS, off identity PASS, original macro-collision negative control caught. Pocket[1651.86,1211.76]-[1661.58,1221.48]. Probe/log `t13_anchor_probe_r2.{tcl,log}`.
- Remaining authority delivery to rs_r1 is1249.498um (other branches1064..1168um). Local cone fix alone is NOT reset closure. Minimum3 intermediate RCK resetrelease stages are needed for4<=405um segments if that route is chosen, boot-only+3RCK; coordinate RTL/model/golden before change. Existing RST_RETIME/TREE2 do not cover the whole1.25mm span. No RTL changes by this worker.

## Native RM / other failures
- RM worker `/root/s81_cores/serdes/rm_select` owns RPC8. Private native perbank clock row `reset_probe/anchor/native_clock_rows.json` selects65 regs/bank onC, expected68 afterRPC8 (includes3 rpq copies). Existing source guard required. Private centroid placement script `native_reset.tcl` currently bank5 only, not qualified/integrated.
- Actual C native readclock scope538 regs (RPC8=>562), bbox x1724..2841,y341..459. Global readcontrol sits x1724..1765 while bankunion2081..2549; blindly grouping all is not compact. Need control+fanin/buffer locality before broader cohort. Global rt_c/rrst_nc -> rpq recovery must retain original reset contract and be measured.
- Clock-dominated additional candidates: t13 relay119->121 -504.75; t1clb45 relay51->52/state -1086.91. Their type-specific cohort rows still require review/measurement.
- DATA-dominated sideband failures sent SerDes parent and S81 plan owner: t1clfe origin/s2->reader_start_ft1_i/g_x6 Q-to-D2104.28ps (-1406.90); t15cla3d relay115->cland_fstart_ft0_o Q-to-D2009.46ps (-1415.22). Same-tap grouping cannot fix them. Existing reset/reader owner must add real registered/local-copy transport and price offsets.

## Targeted STA reuse
- Exact current-policy loader `reset_probe/anchor/ready94_sta_nominal.tcl` (find_timing_paths), original source-frame report `ready94_sta_r3.log`; sensitivity loader/log `ready94_sta_u60.tcl`, `ready94_sta_{baseline,r3}_u60.log`.
- Loads exact kit TC_LIB_FILES, original constraint.sdc, propagated clocks and calibrated placementRC, no repair/write. For E use vector wildcard pins `*u_rxf_q*/QN` -> `*u_face_p_d*/D`; one target check per new form. Do not edit kit uncertainty; METHODOLOGY6.1 current owner policy is setup0/hold25.
