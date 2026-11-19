# FABLE-FIX-S81-LEAF handoff (owner of ot_s81sl_leaf__t*, started 11-18 23:0x PST)

Lane dir: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf (bin/ scripts, repo/ lane clone, proof/, t25a7 t27d8e t69d8e = kit copies with my STA outputs).
Support lane: S81-LEAF-D8E-1118. Plan rows go to S81-DIE-R3 (D8h).

## Cause (measured, TT, placement RC, 4_cts.odb after the kit TT repair, frame = tt_setup_repair.tcl measure)
Kits: t25__cl431c660f a7 (-778.07, 7,981 ends below -42), t27 a7 (-526.93, 1,172), t69 (-221.80, 142). All D8e df7446e48ba9.

1. FAMILY: synthesis folds the plan stations of the bound module. The bound RTL holds one cst_hi register set per lane
   (16) and 4 hig groups x 2 stages, as plain regs of the one bound module; replica_keep / OT_KEEP_WIRES only covers
   replicated modules. yosys opt_merge keeps 1 of 4 (equal data, lanes equal mod 4): hig 8,200 -> 2,048 flops,
   lane cst_hi 4,112 -> 1,040, on both t25 and t27. The surviving lane-9 flop drives the lane 1 / 5 / 13 macro pins:
   t27 r0[20] 693 ps wire at 2.2 ns slew on one net, slack -271. Ends in this class: t27 about 553 of 1,172,
   t69 65 of 142, t25 about 2,700 of 7,981. Not a lane-order bug (RTL wiring is per lane).
   Fix: lane clone commit 79248fe9e9 (replica_keep.station_regs + gen_phys): keep on every bound register an
   istations.tcl is_place fragment names. No cycle change. NOT pushed until the proof kit reads at GRT TT.
2. t25__cl431c660f only: clock.tap_mode "explicit" with 9 grid taps, all on the W / S edge (the sibling cl55642d17 and
   69 other leaves are "grid+explicit" with 25+ taps). OT_TAP_CHECK: clk 1448, clk_t3 1804, clk_t6 1463, clk_t2 981 ps
   against the 450 target; cores sit at 450. Launch clocks 840..1750 ps, capture -70..360 ps. This is most of -775.90.
   ROW for D8h: t25__cl431c660f clock.tap_mode grid+explicit with added_taps like cl55642d17 (OT_TAP_CHECK asks pitch <= 148 um).
3. Local classes left on t27 after 1: vp g_wr1 x_wa_q -> wdo_q, 28 logic stages on 92 um, -217 (252 ends);
   vp driver dv_q -> m_q / src regs, about 700 um control wire, -527 / -405 (about 140 ends); dodd_q -> cf memory, -197 (186 ends).
   Re-measure on the proof kit before deciding (some vp src regs fold too: 944 -> 506).
4. NS face bank cannot fit (t40 sid5S, t52, t53clb, t54 x2, t61, t62, t72, t75): stride 2. S81-DIE-R3 sets stride 1
   family-wide in D8g. Open: a face_flops.tcl fallback (stride 2 where it fits, else stride 1 for that flop) if t25
   congestion returns.

## Running
- Proof kit: epyc10 .../proof/t27keep (t27 a7 seed + 70 keep entries in config.mk), goal grt, ot-run from intel2,
  log intel2 ~/.local/state/fable-fix-s81-leaf/t27keep.otrun.log, unit oth-ubuntu-55774-1795072731. Read TT with
  bin/leaf_tcl.sh <kit> 4_cts.odb <tag> leaf_cls.tcl and bin/cls_sum.py; GRT TT from 5_global_route.tt.rpt / OT_GRT_FRAMES.

## Next
- Proof passes (cst_hi class gone at GRT TT): `python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-push-main` in repo/.
- Post the t25cl431 tap row to S81-DIE-R3. Read t24__cl81374cd8 HPWL divergence (not read yet).
- Then the classes of item 3 (RTL / plan), sign-off and export.

## 11-19 00:5x PST state
- Fold commit is f25c6f0633+trailers (amended; Fixes-Items leaf + kv_leaf) in epyc10 .../fable-fix-s81-leaf/repo. PUSH RULE (COORD): only when
  BOTH t27keep GRT TT reads fine AND S81-DIE-R3 has posted D8g APPLIED. Push = cd repo && python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-push-main
- Proof t27keep at CTS, TT, placement RC, after the kit TT repair (my STA on a side copy t27keep_cts): wns -230.33 (control -526.93),
  ends below -42: 648 (control 1,172). cst_hi -> lane macro class: 0 ends (control about 553). x_wa_q -> wdo_q: 0 (control 252).
  OT_ISTATIONS placed 15,228 flops (control 6,036). GRT was running at 00:56 PST.
- What is left on t27keep is one class, the vp controller glue with 600-800 um legs: driver_dodd_q -> cf / yrow native_memory 336 ends (-227),
  vp src -> vp src 122 (-220), vp src -> cf 54, u_rr rst_n -> hog / hig stations 18 (-170, 824 um), leafdn pad -> u_rr 14, u_rrl q -> state 11.
  Next fix candidate: the vp glue has no region and dodd (one flop) writes the cf memory across the leaf.
- Reach: fold is leaf + kv_leaf only (posts REACH, KVLEAF). Buckets of the 15 FAILED rows: 14 face bank (D8g stride 1), t56 = stale tool in the pinned D8e tree (main cf90bd19b2).

## 11-19 01:2x PST state (three things in flight)
1. Fold push: unchanged rule (t27keep GRT TT + D8g APPLIED). t27keep in GRT since 00:54.
2. vp relay-stage form (class left after the fold fix):
   - RTL: repo/ (epyc10 lane clone, UNCOMMITTED edit) rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv gets param CFP (define OT_S81SL_VP_CFPIPE):
     cf is written CFP edges later from yrow_d[CFP-1] with the row select delayed CFP edges. 0 cycles at every output for legal streams
     (no overlapping POSTs, the SR contract); CFP <= YA + 1. Bench test/run_vp_cfp_bench.sh -> epyc10 .../bench_cfp/summary.log
     (ot-run log intel2 ~/.local/state/fable-fix-s81-leaf/cfp_bench.otrun.log). Expect cfp*_legal PASS, ctl_mut_sel FAIL, ctl_dense may differ.
   - NORM / SU command path (cd_c -> n_pre / m_* / s_d, 122 + ends, 683 um): needs +1 cycle = the g_sre part of the existing SR form
     (OT_S81SL_VP_SRAMREG, DIE-S81-85 11-09, benched, never switched on at the die). Latency through bind K: NORM n_go / m_v / n_pre + 1, SU s_v / s_d + 1.
   - As-built: the S81 as-built base is older than main and bind names depend on source positions; apply like tools/die_plan/s81_vp_cfr_asbuilt_patch.py
     (tokens keep line and column). NOT written yet.
   - Proof 2: epyc10 proof/t27relay = t27keep + bin/relay_proxy.py on the bound module (physical proxy only: cf write from yrow_d[1] with select + 2,
     one register on e_cd and its NORM select). Goal grt. Log intel2 .../t27relay.otrun.log.
3. Tap re-derive (COORD 01:1x, PRECHECK TAP-CAP 11 types + t25cl431): plan tool exists, tools/die_plan/reach_fix.py fix --classes 1,2 --cap 1500 --assign kit.
   Running on the whole family against the D8e plan (read-only) -> epyc10 taps/plan_leaf_taps.json, event_leaf_taps.json, fix_leaf.tsv, fix_leaf.log.
   t28 / t29 are plain tap_mode grid with 16 taps (c2 12 taps over, max 7,156 sinks; t29 3 over, 3,156). t27 is not a tap-cap type, so a tap proof needs
   a kit regenerated from the new plan (kit-rtl wrapper carries the tap ports): that is the die lane event_kits recipe, not a hand patch.

## 11-19 01:5x PST: COORD r713 rulings
- Tap re-derive at cap 1,000 (not 1,500). Cap-1500 run killed; cap-1000 run -> epyc10 taps1000/ (plan_leaf_taps.json, event_leaf_taps.json, fix_leaf.tsv, fix_leaf.log).
  Post the rows per outline; S81-DIE-R3 builds the t28 tap proof kit with its event-kit recipe. Do NOT replicate the gen chain privately.
- Close by construction (+cycles) is the default: form B (+1 cycle, bind K) is the default. Form A (CFP, 0 cycles) is kept ONLY if its bench passes on ALL
  streams (the dense / overlapping-POST control too) and it is not slower at GRT; else drop it and revert the uncommitted vp.sv edit in repo/.
  If A is dropped, the cf path needs a +cycle form: candidate = one more group HI station (existing CS_HI_GS depth, sited store-side) so cf sits at the store,
  hc_post write-back + 1 through bind K. Not designed in detail yet.
- Kill slip: my pgrep -f pattern matched my own ssh shell (only my own reach_fix run + shell died). Use ps | grep "[r]each_fix" form.
