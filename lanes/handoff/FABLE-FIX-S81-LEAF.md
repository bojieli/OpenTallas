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

## Kill / waiter rule (COORD 11-19 02:0x)
Never pattern-kill. `ps -o pid,ppid,cmd -p <PID>`, confirm, kill that one PID (or ot-run --cancel). Waiters match a PID file, never a command-line grep.
PID files: epyc10 taps1000/fix.pid = 3046128 (reach_fix cap 1000). Proof kits: watch the report file / FAIL_* marker and the ot-run unit, not pgrep.

## 11-19 02:1x PST: proofs
- t27keep: GRT SIGKILLed 01:23 by the epyc10 plan guard (kills.log, MemAvailable < 5 percent), relaunched from 4_cts.odb (intel2 t27keep.otrun2.log). INFRA, not design.
- t27stb (third kit, COORD 02:0x): copy of t27keep at 3_place + `export OT_TAP_GRT_PRE = 1` (tapbal_grt.tcl + subtree_balance.tcl GRT-RC pre-pass), goal grt,
  intel2 t27stb.otrun.log. config.mk mtime kept (touch -r) so the kit resumes from place. Compare with t27keep: bin/leaf_tcl.sh <kit copy> 4_cts.odb <tag> leaf_clk.tcl,
  then bin/tap_skew.py leafclk_<tag>.tsv (in-tap span per tap) and the TT numbers.
  Baseline, control t27 a7 at CTS, TT, placement RC: 29 taps, in-tap span max 166 ps, median 37; 7 taps >= 100 ps, 3 in 60..100, 19 < 60;
  worst clk_t14 (median sink 159 ps earlier than the latest), clk_t9 139, clk_t10 119.
- t27relay: in place.

## 11-19 02:5x PST: HPWL gate finding (the t24 / t37 / kv_leaf t3 class) + proof states
- t27relay FAILED the PLACE-HPWL gate at 1.39 (limit 1.3). t27keep passed the same gate at 1.275. Both ratios are 100 % pre-repair spreading
  (segments 1.390 x 1.000 and 1.275 x 1.000): HPWL is flat at 4.33e6 from iteration 0 to overflow 0.41, then rises to 6.0e6 while overflow falls to 0.19,
  and GPL exits one row after the non-virtual repair. The run minimum is at iteration 80, overflow 0.77. Nothing grows after convergence.
  A 300-flop netlist change moved the ratio across the limit, so on leaf the gate is a coin flip (t24 1.36 / 1.47, t37 1.38-1.40, kv_leaf t3 1.32).
  History: 1e569598d0c + test_hpwl_growth_takes_the_repair_step_out deliberately count spreading before the repair; strategy said no ratio change. NOT changed by me.
  Evidence run: t27relay relaunched with OT_GPL_HPWL_RATIO = 0 in its private config.mk (intel2 t27relay.otrun2.log); compare its CTS / GRT TT with t27keep.
  If timing is as good, propose: gate advisory on leaf (academic profile: only DRC / setup / hold / latency block) or growth measured from the first row at overflow <= 0.30.
- Bench CFP: cfp1_legal and cfp2_legal PASS on 3 seeds each (59,959 checks, 0 errors); hqx2, cfp0_eq, dense control, mutant still running. Form A stays only if the dense control passes.
- All three kits re-run global place on relaunch (run_kit does not skip to GRT).

## 11-19 03:1x PST: PLACE-HPWL gate fix PUSHED (COORD ruling: measurement bug)
main bfc57007db14 (from lane clone epyc10 .../fable-fix-s81-leaf/repo2, separate from repo/ so the fold commit stays unpushed).
Growth counted from the first row at overflow <= 0.30 or the first non-virtual repair; ratio 1.3 unchanged. t27 kits read 1.165 (was 1.39 / 1.275);
t47 still STOP at 2.22. Trailer Fixes-Items: s81/ot_s81sl_leaf__*, s81/ot_s81sl_kv_leaf__*.
Note: that trailer relaunches the family before D8g: the 14 face-bank rows will fail again on stride 2 until D8g applies (told COORD).
Fold commit (repo/, f25c... amended with trailers): still NOT pushed; rule unchanged (t27keep GRT TT + D8g APPLIED).

## 11-19 03:4x PST: loop-gap classes answered
- t58 place "RuntimeError: reentrant call inside" (class 28712c48d9): the job got signal 15 (stopped) and ot-job crashed in its own stop handler
  (print to buffered stderr inside a signal handler). Not a design fail. Fix on main ca589f7daf0b (os.write in the handler); hosts need the ot-job install.
  Who sent the SIGTERM at 00:27 PST on epyc8 is NOT identified. t58 already relaunched (a6).
- t54__cl706d9749 PLACE-HPWL 1.61 (a12, epyc2, 01:51): same measurement class. Fixed gate on its real 3_3_place_gp.log: 1.111, OK
  (HPWL flat 5.5e6 down to overflow 0.49, 8.0e6 at the first converged row 0.2446, exit 8.883e6; no non-virtual repair in the log). Cleared by bfc57007db14.

## 11-19 02:3x PST: COORD ruling, option 2
PUSH THE FOLD FIX AS SOON AS S81-DIE-R3 POSTS D8g APPLIED (CTS evidence is enough; GRT TT no longer gates it):
  epyc10: cd /srv/opentallas-scratch2/claude/fable-fix-s81-leaf/repo && git stash is FORBIDDEN; repo/ has an UNCOMMITTED vp.sv CFP edit + bench script:
  revert or commit those separately first (git checkout -- rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv if form A is dropped), then
  python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-push-main
Proof kits run with proof priority: path regex fable-fix-s81-leaf/proof/ is in epyc10 /var/tmp/ot-heavy/prio_proof.re; new launches use
  python3 -I rt/current/tools/fleet/ot-run --priority proof. t27keep = intel2 t27keep.otrun3.log (queued, covered by the regex), t27stb = t27stb.otrun2.log.
If the guard kills one again: post the kills.log line to FLEET-OPS-R (bug).

## 11-19 02:4x PST: tap rows posted, form A dropped
- Tap rows (cap 1,000): lanes/handoff/S81-LEAF-TAP-ROWS-cap1000.json (76 types, clock keys only); full plan epyc10 taps1000/plan_leaf_taps.json (500ee1bb2f49).
  Result: violating types 78 -> 24; radius 78 -> 3; over cap 51 -> 24 (residual: mostly 1-4 taps AT 1,000). t47 unchanged by the tool (11 taps over, max 1,809) = open.
  S81-DIE-R3 builds the t28 proof kit (t28: grid 16 taps -> grid+explicit +100).
- Form A (CFP) DROPPED: dense control FAIL (158 errors), legal PASS. repo/ is clean (only the fold commit); patch + bench kept in epyc10 dropped_formA/.
  Form B (+1 cycle) is the only vp form now; the cf path needs its own +cycle form (not designed).

## 11-19 03:1x PST: t47 tool fix pushed; CFX form written, bench pending
- reach_fix reset retry: main f72013a6506a. t47 / t75 rows added to lanes/handoff/S81-LEAF-TAP-ROWS-cap1000.json (78 types now; those two carry
  whole_keys = the full clock block incl. landing reset re-selection). Evidence epyc10 taps47b/.
- CFX (+1 cycle coefficient form): UNCOMMITTED in epyc10 repo2/ (vp.sv + test/tb_vp_cfx.sv + test/run_vp_cfx_bench.sh); patch copy epyc10 cfx_vp.patch.
  Contract: hc_post write-back + 1 clk, all other outputs same cycle, every stream. Bind K: vp hc_post write-back latency + 1 (define OT_S81SL_VP_CFX / param CFX).
  First bench run was killed by the memory guard (compile); relaunched -j 4 with output under proof/bench_cfx (proof-priority path),
  intel2 cfx_bench.otrun2.log. Commit + push only after summary.log shows cfx_* PASS and ctl_mut_hq FAIL. As-built patch tool NOT written.

## 11-19 03:1x PST: why pushed flow fixes do not reach S81 kits yet
gen.py phys runs from the DIE SOURCE TREE (wave spec src = kw45/src_s81_pin_3c913dbdfb23_d8e_1117_work), and the kit copies gp_noconverge.py, kit_ln_copies.py etc.
from there, not from rt/<sha>. That tree has neither bfc57007db14 (HPWL gate) nor cf90bd19b2 (t56 relay no-op). So t13 / serdes t2 / t12 HPWL stops and the
t56 kit_rtl error keep repeating until the S81 die source is refreshed from main (D8g compose or ot-src-refresh). Same will hold for the fold fix (gen_phys.py).
serdes__t2 a13 real log through the fixed gate: 1.001, OK. t13 a18 / serdes t12 a10 logs not retrievable (ran on localhost, sealed job dir deleted).

## 11-19 03:5x PST: FOLD FIX PUSHED (D8g APPLIED seen 03:1x)
Pushed with --no-test: the touched-file set has 7 failures that are identical on plain main in the same sparse checkout
(6 = rtl/common missing from the cone, 1 = test_gen_phys_cap_budget broken on main by a2e83fc189). test_replica_keep passes.
Reaches kits only when the S81 live tree carries main tools (S81-DIE-R3: D8g2 publish).
CFX bench: legal x3, dense x3, hqx2 x2 PASS so far (proof/bench_cfx/summary.log); commit + push when the mutant control line is in.
A/B taps (COORD 03:3x): form (b) solve running epyc10 tapsB/ (radius 75, assign nearest, t21 + t16; fix.pid); private kit chain script bin/gen_private.sh
(kit-rtl -> prepare-stations -> gen phys from a plandir of symlinks + private plan), NOT run yet. Glue fence recipe for t69: waiting for FABLE-FIX-S81-GLUE.
