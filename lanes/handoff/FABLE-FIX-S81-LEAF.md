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
