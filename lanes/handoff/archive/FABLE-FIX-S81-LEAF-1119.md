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

## 11-19 03:5x PST resume after the limit (no successor change found: hub posts, lane dirs and repo2 are as I left them)
All on epyc10 under proof/, launched with rt ot-run --priority proof; logs intel2 ~/.local/state/fable-fix-s81-leaf/:
- t27keep (otrun3) and t27relay (otrun2, HPWL gate off): back in global place (each relaunch redoes place). No CTS/GRT TT yet since the 00:5x CTS read.
- t27stb (subtree balance): otrun2 died at place, earlyoom SIGTERM (make 241); relaunched otrun3.
- Tap A/B: first launch FAILED at kit_topology KIT_TOPOLOGY_BIND_STALE (I passed my private plan as --native-plan); fixed in bin/gen_private.sh
  (native plan = the D8e plan of record) and relaunched: proof/ab/{a16,b16,a21,b21}, logs ab_*.otrun2.log. Goal cts. Compare with bin/leaf_tcl.sh + bin/tap_skew.py.
  (a) = taps1000 rows; (b) = tapsB (radius 75 um = sink region W+H <= 300, assign nearest = no spill; far-cluster merge NOT implemented).
- Fence trial: proof/t27fence = t27keep from floorplan + place_regions.tcl (main 1fd3d8bd5139) hand-installed, one region vpglue
  (vp driver / src / yrow / cf / hsi / g_wr1 flops, util 0.35, centred on the two leaf-store SRAMs). On t27, not t69 (same logic, kit at hand). Log t27fence.otrun.log.
  Known limit: yosys gate names are anonymous, so the regex takes the cone flops only. GLUE lane: 0.55 failed DPL-0033 on a small cone.
- CFX bench: legal 3/3, dense 3/3, hqx2 2/2 + dense PASS; cfx0_eq and ctl_mut_hq pending (proof/bench_cfx/summary.log). Then commit vp.sv + tb + script in repo2 and push.

## 11-19 04:0x PST: tap A/B cannot be built privately; fence region confirmed
- Tap A/B kits (proof/ab/*): second launch got through kit-rtl and prepare-stations, then gen phys REFUSED all four:
  "physical collector_tree differs from captured bound reset identity; preserve original IDs/edges/coordinates".
  New taps renumber / re-site the reset collector tree, and the bound RTL carries the old tree. So ANY tap-row change needs a new bind before a kit exists.
  The A/B (and the t28 proof) can only be built by S81-DIE-R3 after binding a plan with the rows (D8h or a private bind). Private chain stopped here; do not retry.
- t27fence: region read by 3_3 = 3,359 cells, 972 um2, util 0.33, box (757.7 588.2)-(854.7 685.2); bank flops NOT in it (netlist: 3,314 matching flops, 1,224 bank flops excluded).
- CFX bench: cfx0_eq prints FAIL 4,315 errors = 4,315 write-backs: that run (CFX 0 vs CFX 0) is a control in this tb (the tb demands the + 1 shift), not a defect. Mutant ctl_mut_hq pending.

## OWNER LINE (repeat in every hourly post; COORD 03:5x)
OWNER FABLE-FIX-S81-LEAF owns s81sl_leaf__t* and s81sl_kv_leaf__t* (all), listed by name, with the blocker per group.

## 11-19 04:3x PST: CFX pushed; reset keying finding (prototype, NOT pushed)
- CFX on main e828eac08886 (bench all PASS, both controls FAIL as they must). As-built patch + plan switch still to do.
- Reset tree vs taps: reset_tree.py solves ONE relay tree whose leaves are the clock taps (consumer_taps -> _taps = tap grid / added_taps), one rst_n_t<k> per tap k;
  collector outs are rst_n_t{consumer_count + k}; face / corner / START sites avoid the tap points (_plan_taps); gen_phys.install_bound_native_reset compares
  RT.for_type(plan) with the tree captured at bind and refuses any difference. So every added tap = new leaf + shifted indices + moved sites.
- Prototype (epyc10 reset_key_proto.patch against main, test reset_key_test.py; working copy repo3/, UNCOMMITTED): type.reset.consumer_sites_um = frozen
  [[name, x, y], ...] of the bound plan (bin/freeze_reset.py writes it); reset_tree._taps returns it. Result on t16 with +200 taps (main tools on the D8e tree):
  "the current solve equals the captured bound reset tree ... 25 collectors = bound RTL" (without the key: refused). The run then stopped on an unrelated
  STALE-CORE-VIEW gate (main tools vs D8e views), so NO kit was generated.
  Freezing only consumer_taps() is NOT enough (tried: identity still differs; siting reads _plan_taps and the tree records n_clock_taps).
  Open before a push: _taps is also read by clock_landings.py:515 and the n_clock_taps / clock_ports counts; kit reset_taps.tcl must give flops of a new clock tap
  the nearest reset leaf; reach_fix should write the key when it adds taps; full kit to CTS.

## 11-19 04:1x PST readings
- t27fence FAILED at detailed placement, DPL-0033 (placement check lists vp driver / src flops), region util 0.33; GPL exit HPWL 1.036 x (best of all kits).
  Same class as glue kit H. My region also held the vp OUTPUT register flops (driver_hw_d_q, x_qd_q, ...) that belong at far cores: wrong set. Not relaunched unchanged.
- t27relay (proxy forms A + B, HPWL gate off) at CTS after TT repair: wns -407.25 (before -426.92). WORSE than t27keep -230.33. Not explained yet;
  read its classes with bin/leaf_tcl.sh + cls_sum.py before concluding anything about form B. Both t27keep and t27relay are in GRT now; t27stb in CTS.
- Reset key (COORD 04:0x, three items): implemented in epyc10 repo3/ (UNCOMMITTED): reset_tree._taps = frozen view, _clock_taps = real taps; clock_landings reads
  _clock_taps; gen_phys emits rt_consumer_taps_um (nearest reset leaf, existing reset_taps.tcl path) when the key is set; reach_fix writes the key before it appends taps;
  schema + json; test_reset_consumer_sites.py (6 tests pass). End-to-end check on t16 running: bin/rk_check.sh -> tapsK/result.txt (FIX_RC, GEN_RC), proof/ab/b16/gen3.log.
  Push after that check shows the tool wrote the key and gen passed the reset identity.

## 11-19 04:5x PST: RESET-KEY pushed (see post). Proof = S81-DIE-R3 t16 generation with main tools; then regenerate tap rows with the patched reach_fix
(they then carry reset.consumer_sites_um and need no bind). Pitfall found: the key must hold EXACT floats (rounding 901.8000000000001 -> 901.8 broke the identity).

## 11-19 07:5x PST (COORD 07:50 items a, b, c)
(a) reach_fix re-records clock.reset_tree_anchor for every changed type: main 0d74b55b8937. Real run on D8e t47 / t75 (epyc10 taps47c/): both applied,
    anchor re-recorded (t47 5 relays, 4 moved; t75 6 relays, 6 moved), no error. D8h already carries S81-DIE-R3 own anchor fix (plan h3); my rows file is NOT regenerated.
    t16 reset-key generation: identity passes on the D8e tree with main tools (04:5x); a full kit still needs a tree whose views match main tools (D8g2 / D8h).
(b) Lever 8 repeating values (my STA on the wave 4_cts.odb, TT, placement RC; epyc10 proof/l8_t60, proof/l8_t74):
    about -1,115 (t60 -1115.15; t31 same value): u_vsw/o_f -> u_vs/sw_fi (and o_d[*] -> sw_ri[*], 64 ends, -1090): core vsw output straight into core vs input,
      596 um, NO station (cst_swr is depth 0 in the bound RTL: plain wire), launch at 633 ps inside vsw, arrival 2,076. Fix = one station on the swr link (plan
      internal_stations core:vsw.o -> core:vs.sw_ri, +1 cycle, bind K), as t25 / t27 have (u_cst_swr_gd_s_0).
    about -840 (t74 -844.55; t2 / t6 -837): vp write port XR stage, u_vp.g_wr1.u_w.g_xr.sw_a_q[0] -> wdo_q[*][*] (246 ends on t74, median -647): the address
      register decodes into the 2 x 128 write-data registers; start and end 35 um apart but 1,570 ps of data path, plus 180 ps launch-late clock (641 vs 462).
      Path detail not printed yet (run report_checks -to that endpoint).
(c) Face bank: 0 rows FAILED with that text in kit_wave_stages.tsv now (the 10 are D8e / D8f stride-2 rows, superseded). Structural fix pushed anyway:
    main 0ccfdf3d150d, face_flops.tcl falls back to row stride 1 for a register the comb cannot hold (stop remains if stride 1 does not fit).
OWNER: FABLE-FIX-S81-LEAF owns s81sl_leaf__t* and s81sl_kv_leaf__t* (all).

## 11-19 08:4x PST: D8i handoff items
- SWR station rows: lanes/handoff/S81-LEAF-SWR-STATION-ROWS.json (36 types: 34 x 1 station, t4 and t60 x 2; all hops <= 374 um). Generator epyc10 bin/swr_rows.py on the live
  D8g plan; full plan epyc10 swr/plan_swr.json. Class swr (CS_SWR_D 0 -> len(regs_um)), + that many cycles on sw_vi / sw_ri / sw_fi, bind K.
  Finding: 22 of the 36 are 471..980 um pin to pin (t60 980) and had NO station: the old R3 rows used stale pin points. Sites checked only against hard cores + 12 um.
  NOT run: schema validate (import error in my call), G0, bind, any kit. kv_leaf__t2 has no vsw / vs core: skipped.
- VPW SLR overlay: main 59024a5e802 (tools/die_plan/s81_vpw_slr_overlay.py + test + tb). Apply to the die source tree in D8i, then rebind. 0 cycles, no latency change.
  Lock-step on the live D8g source: PASS 59,991 checks 0 errors; XR 0 control FAIL 53,438 errors. No physical result; no Fixes-Items trailer on purpose.
- Correction: the "180 ps late launch clock" on the -840 path was my misreading (I compared the launch Q arrival with the capture clock). Launch CLK 550, capture CLK 541,
  same tap clk_t2, CRPR 79. Nothing for S81-CLOCK-WINDOW-1119 from this path.

## 11-19 09:2x PST: CBC checker was blind for core-to-core legs (all dies)
Cause: cbc_pass.relay_rows ran relay_depth on plan_branch.json in its WORK dir without --repo / --plan-dir -> trace finds no child sources, no pin files ->
0 paths measured on every type, "0 relay rows", rc 0 (epyc8 cbc-rules-1119/runs/s81_d8g4/relay_depth.json: 395 types, 0 paths). With the tree + plan dir leaf t60 alone:
37 paths, 5 rows, +7 stages. Fix main 01360b438a05 (cbc_pass args; relay_depth RELAY-DEPTH-BLIND warning / exit 3; schema.py -I import). --no-test push (known tools-only reason).
Running: (a) full S81 D8g relay_depth recount, epyc10 rd/s81_d8g_all.json (+ .log, rd/all.pid); (b) private G0, epyc10 proof/g0 (plandir of symlinks + plan_swr.json):
g0_swr (D8g + 36 station rows) and g0_ctl (D8g), status.txt, via ot-run (intel2 g0_swr.otrun.log). Compare ERROR sets; expect 0 new.
QC / KV / HEAD CBC counts need a re-run by CBC-RULES-1119 with main >= 01360b438a05.

## 11-19 10:1x PST: G0 on the SWR rows + full S81 recount
- Private G0 (check.py --street-rule warn, D8g tree, plandir of symlinks): D8g + 36 SWR station rows = 2 errors, 11,287 warnings; D8g control = 2 errors, 11,289 warnings;
  the 2 errors are identical (cuts at 10500 s_0S_L0 0.67, 10750 s_6S_L0 0.63). Rows are G0-clean. epyc10 proof/g0/{g0_swr,g0_ctl}/g0_report.json.
- Full S81 D8g relay_depth recount with the tree + plan dir (epyc10 rd/s81_d8g_all.json): 395 types, 71,796 paths measured (was 0), 74 types with rows, 360 rows, +362 stages,
  375 unfixed. By family: col_h9_r0_p2 72 rows, p5 72, p1 36, p4 36; col_h10_r0_p1 36, p4 30; col_h10_r1 24; leaf 32 rows on 12 types; gunit 19; eng 3.
  Unfixed: leaf 88, col_h9_r1 60, col_h9_r2 60, dsdv_slice_c1x_C 54, col_h10_r1 36, col_h10_r2 12. 18 types still BLIND (bk_sel__t2, slice_station__t51, svc_hi_*pvso_entry, ...).
- SECOND GAP, NOT FIXED: on the 36 leaf types of my SWR rows the tool lists the vsw -> vs link on only 5 (rows t21 / t60, unfixed t27 / t71 "neither end is a bound leaf
  (sub-cores)", flight-only kv_leaf t1); 31 are not listed at all although pin to pin is 203..794 um (t31 591, t10 / t74 695, t4 794). Suspect: plan core inst u_lf.u_vsw vs
  bound instance u_u_lf<N>_u_vsw name mapping in core_conns_from_bind.trace / relay_depth leaf_rel. Next step: compare trace paths of t60 (works) and t31 (missing).

## 11-19 10:5x PST: CORRECTION (my error) + D8i hand-off files
- The "36 types without a vsw -> vs station" was WRONG. 31 of them already have one: the plan declares it as core:u_lf.u_vs.sw_ri|core:u_lf.u_vsw (I only searched the
  core:u_lf.u_vsw.o_*|core:u_lf.u_vs form) and the bound RTL carries the cst_swr stage. Only 5 lack it: kv_leaf__t1, leaf t21, t27, t60 (2 stations), t71.
  So "22 types 471..980 um unstationed" is withdrawn, and there is NO second trace-mapping gap on leaf: the tool was right not to list those 31.
  t31 has the station; its -1,116 was attributed by matching value only and is NOT explained (t60 was measured). The old file is epyc10 swr/S81-LEAF-SWR-STATION-ROWS.WRONG36.json.
- D8i files on the hub: lanes/handoff/S81-LEAF-SWR-STATION-ROWS.json (5 types, 6 stations) and lanes/handoff/S81-D8I-RELAY-DEPTH-ROWS.json (73 types, 354 rows, +354 stages;
  apply with relay_depth.py merge; the vs.sw_* rows of t21 / t60 are left to the station rows). Merged plan: epyc10 proof/g0/plandir/plan_d8i_rows2.json.
  G0 on it: running (intel2 g0_d8i2.otrun.log; epyc10 proof/g0/status_d8i2.txt, g0_d8i2/g0_report.json); control = g0_ctl (2 errors). g0_d8i (first, with the wrong 36) is void.
- Trace-mapping task (COORD): the S81 leaf vsw case is not a mapping bug. Still to do: the QC flattened-tile case (48 blind types) and the 18 S81 blind types; then four-die re-runs.

## 11-19 ~13:3x PST: mapping fix pushed, four-die recount, next = netlist-level trace
- main dcd56363d450 (lane commit 05e32381863): core_conns_from_bind indexed-name tier (QC u_t02 = u_u_t_0_2, LEF pins must all be ports, unique pair) and
  relay_depth.leaf_rel takes the bound leaf from trace core_insts (S81 leaf replica-index names u_u_lf4_u_vn_u_b). test_core_conns_indexed_tile.py.
- Recount (lane dirs <host>:/srv/opentallas-scratch2/claude/fable-fix-s81-leaf/rc/<die>/{relay_depth.json,summary.json}; script rc_tools/recount.py TOOLS SRC PLAN RTLDIRS WORK):
  S81 D8g (epyc10) 561 rows / 120 types / +643 stages, unfixed 173, 18 blind (was 360 / 74 / 375). QC N4.6c (epyc9) 13,393 traced, 202 measured, 0 rows, 49 blind
  (tile links stop at qfd_c_xstn fabric leaves; 20 types had no bound file by my stager). KV D25c (epyc10 rc/kv, baseline rc/kv_base) 543 rows / 34 types / +762, same
  with and without the fix, 10 blind. HEAD NF15f (epyc9 rc/head, recount_head.py) 0 traced, 7 blind (u_core wrappers).
- D8i hand-off now: lanes/handoff/S81-D8I-RELAY-DEPTH-ROWS.json = 117 types, 551 rows, +631 stages; S81-LEAF-SWR-STATION-ROWS.json = 5 types, 6 stations.
  G0 of the 354-row set was clean vs control (2 = 2 errors). G0 of the 551-row set: running (intel2 g0_d8i3.otrun.log; epyc10 proof/g0/status_d8i3.txt, plan plandir/plan_d8i_rows3.json).
- Netlist-level trace (COORD task, scope: wrapper hierarchy + simple buffer/flop chains): the bind asbuilt.json does NOT help: it holds the nested wrappers as
  blackboxes (dsdv_bk_sel_vmtx: 0 cells). Plan: read each type kit s own synthesized netlist (cores are instances there), walk core output pin -> BUF/INV/DFF -> core
  input pin in OpenROAD tcl (bin/leaf_tcl.sh style), emit rows in the core_conns paths format so relay_depth measures them. Not started beyond this finding.
- Proof kits: t27keep and t27stb still in GRT (relaunched after guard kills), t27relay stopped at FAIL_PLACE_HPWL.gate139 (not yet checked which gate version ran). No GRT TT read yet.
- Open after that: one read of t31 worst CTS path (-1,116 unexplained).

## 11-19 ~14:0x PST: OPUS SUCCESSOR took over (Fable weekly limit). Read handoff + posts; live jobs checked, none duplicated.
- Live on epyc10 (all FABLE-FIX-S81-LEAF, do not relaunch): t28wide (face-bank fix proof, in 3_5 detail place), t27keep (GRT extra iter), t27relay
  (relaunched 19:49 UTC, passed place, now GRT extra iter; the 09:47 FAIL_PLACE_HPWL.gate139 file is from the earlier run), t27stb (4_2 tapbal_grt:
  GRT took 4h33 with congestion, single-thread subtree_balance since 16:47 UTC at 100% CPU = busy, not hung).
- svc_rs netlist trace: svc_hi_dsdv_svc_rs__t2 standalone (core_conns_from_netlist, 10 GB RSS, 4 min): 72/72 cores found, 0 core-to-core links.
  Every core input bit ends at logic 77,040 / constant 7,144 / top port 3,344 / clock-landing submodule 3,264. Same class as HEAD hd_ctl: no wire to
  stage, no row. (The lane's earlier svc_rd.json 0 was this, not a tool miss.) t4..t6 are the same module, not re-run. epyc10 nl/svc_cn_t2.{json,log}.
- QC crossing-station types (cbf/cbn/cbx, N4.6c plan zz_s29_qc103_s4q9n46c.json, live_qwen_compute tree): newest kit netlists staged to epyc9
  nl/qc/<type>/ (SOURCE file per type; N3..N46C generations, older netlists vs N4.6c pins). relay_depth --netlist-dir: 14 types now MEASURED
  (were blind): 177 core-to-core paths (all 177 from the netlist), 0 rows, 0 unfixed. 42 links over 405 um by flight (max 2,592 um cbn_q00__cldbcda913 cl_nb_i00.q -> u_t00.n_b),
  each already has >= ceil(L/405)-1 flops on the netlist chain (tool stages_existing), so no row. Still blind: cbn_q00__cl622f65d2, cbx_q10__cl94a12200 (no synthesized kit found on 6 hosts);
  cbf_q00_s2, cbf_q11 have no bound file in the stager. Report epyc9 nl/qc_cb_rd.{json,log}; script epyc9 bin/qc_cb_nl.sh.
- t31 worst CTS path (ot_s81sl_leaf__t31 attempt 12, epyc2 kw43 3fa87b84b18, FAIL_POSTCTS setup_est -913, CTS WNS -1,263): u_vp.g_wr1.u_w
  g_xr.sw_a_q[0] -> wmw_q[0][0], same clk_t10 tree (skew +68 ps in favour). Data 2,160 ps: 5 logic gates (AND5/AOI211/AND5/OA211/OR5, ~240 ps),
  the rest ~40 repeaters with 11 long-wire hops (slew 150..270, ~650 ps wire RC). Cause = the WRP write-port decode (ot_s81sl_vp.sv g_wr1, 0-cycle,
  5-writer priority select) spans the leaf from the sw pin flops to the bank write flops. Not a reach/station row: it is intra-RTL distance.
  Fix candidates: a register on sw_a/sw_m after g_xr near the bank (+1 cycle on the vs write lane, priced) or place g_xr pin flops at the bank.
  The -1,116 number is a different attempt; the class is the same path family.

## 11-19 17:5x PST: kit check after the limit (Opus successor)
- t28wide (face-bank fix b482c7548f18): PLACE-HPWL gate OK, 1.003 x converged minimum (2.0632e7 um). CTS done 22:31 UTC: WNS -265 ps, TNS -32,537 ps.
  GRT started, 3 h in at extra iteration 4/30 (congested like t27). No TT read yet. The NS face-bank stop on t28 is proven fixed through CTS.
- t27keep: GRT extra iteration 12/30. t27relay: GRT clock-leaf repeat pass (48 of 2,580 branch nets over the rule). t27stb: tapbal_grt still writing (log 01:37 UTC). No t27 TT read yet.
- svc_rs: closed, 0 links (see 14:0x). Next: TT read of t28 and t27 when GRT ends; watch GRT runtime (t27stb GRT took 4h33).

## 11-19 18:3x PST: S81-VPW-WREG (t31 fix, COORD-approved +1 cycle)
- main 6496be9f9175: tools/die_plan/s81_vpw_wreg_overlay.py + test + fixtures/s81_vp_xr/tb_vpw_wreg.sv. Bare-name define OT_S81SL_VP_WREG -> vpw parameter WREG.
  A register on sw_a/sw_m alone would shift the sw writer against its data and the other 4 writers, so WREG registers every decoded bank-port value
  (wv, wcol, wa, wm, wdo, xl/xh selects) plus xwd_i once: vpw(t) = ref(t-1) on every output. vp module, lane HI/HO stations, hc_post timeline, reset unchanged.
- Bench (10 tests PASS): +1 with the define on XR and SLR forms; same cycle without it; shift-0-with-define and shift-1-without both FAIL; xwd-not-delayed mutant FAILS.
- Plan rows: lanes/handoff/S81-VPW-WREG-ROWS.json (75 ot_s81sl_leaf__t* types, verilog_defines + latency delta). kv_leaf has no vp.
- t31 private proof: epyc10 proof/t31wreg (attempt-12 kit copy, kit vp patched + define in config.mk), synth has the p_* stage, running to CTS.
- GRT watch 02:20 UTC: t28 extra iteration 7/30, t27keep 18/30, t27relay clock-leaf repeat; t27stb FAIL_POSTCTS GRT-0232 (congestion too high) in the tapbal GRT, 13h47.
  t27 hotspot is local: 138..568 GRT cells at x 846-948, y 677-945, the channels between lane cores g_ln[7]/[8]/[9] and [6]/[11]; nets = vp g_hig HI group stations + vni stations.
  t28 iteration-5 overflow sits over its lane-core columns (x 184-526) with the same HI families plus ft stations. Same class on both; read t28 again at 15.

## 11-19 19:4x PST lever 5 (hot gcells) + t31 WREG CTS
- Hot gcells are not capacity-0: t27 1/668, t28 41/700 sampled. The rest are capacity 5-8 per 0.57-um gcell over lane/vn_a boxes, where only M6/M8 H and M7 V remain. Cause is demand: g_hig 1,025-bit HI station buses cross lane columns (t28 g_hig_2/3 s0 844/942 bits cross a lane; t27 g_hig_0/1 583/437). Post 1d2caa11 has the numbers and the proposed corridor fix for S81-DIE-R3.
- t31wreg CTS TT: WNS -1,044.6 (was -1,263), setup_est -912.7 unchanged (TT FAIL). New worst path: g_ln_8 cst_hi -> lane g_ln_12, 1,906 ps (HI fabric).
- No GRT launched after lever 5. t28/t27keep GRT left to finish. Stop list: no leaf tap pre-pass.
- Tools on epyc10 lane dir bin/: hotpts.py, hotmap.tcl, hotrun.sh, hotsum.py, hig.tcl, higrun.sh, lanegeo.py, vnface.py.

## 11-20 ~04:4x UTC: HI corridor forms (COORD: build A + B, also PRECHECK check)
- Cause: kit_istations sites each shared hi-quad bank at the bit-weighted centroid of member lane sites; on f2ec5ffc3bda it lands inside a lane/vn core (t28 5/8, t31 5/8, all 75 types 1-8/8).
- Tool main adc8824d+: tools/die_plan/s81_hi_corridor.py check|seed|apply|sites (6 tests).
- Work: epyc8 + epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf/hic. Plans: C (sites only) baad7711137e; A2 (lane gaps >= 30.24 + rigid apply + istation_clear + leaf_slot_clear + sites) 3e9118c2db3d (first A had a 2.16-um lane overlap -> KITFIT-OVERLAP, fixed); B via private core_place copy hic/cpx/core_place_hic.py (gate: link timing not worse than base), then sites.
- Builds on epyc9 (form_build9.sh X: hardlinked tree6base = GEOM-OPUS tree6 copy, build_tree_own.sh, kit_one_d8i.sh t28/t31): logs intel2 ~/lanes-opus-s81leaf/hic_build_{C,A2}.log. Next: run_kit.sh grt on each kit, compare GRT overflow/iterations + TT vs base t28 (congested) / t31 attempt 12.
- tree_A/build_A on epyc9 are dead (overlap); ot-delete refused (protected dir marker).

## 11-20 05:5x Opus successor -> FABLE-FIX-S81-LEAF-2140 (leaf family + SWR owner)
- SWR: main @2427590ce023 stage_lfcs_netlist --update SWR_D; netlist epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf/swr/die_b178_lfcs_swr.v (3340107e82f0); bench epyc10 .../swr/bench4 (3 PASS + negative control fails as expected); post 5383bea5 to S81-DIE-R3.
- Form C family: epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf/hic/plan_famC.json (750f33553a0e), types with a bank inside a core 78 -> 4 (clb66fa5cb, t35, t43, t45), 35 types have hop-refused rows, 72 still OVER on bits/track -> corridors (form A) needed.
- Form C t28/t31 build epyc9 hic/build_C: BIND_RC=0, rest in flight; intel2 ~/lanes-opus-s81leaf/grt_launch.sh C waits on its kits, then GRT.
- Form A3: bind fails on added tap clk_t38 (t28). Fix s81_hi_corridor.clear_added_taps to honour grid taps + all core halos.
- Form B: not buildable via core_place (t28 not applied).
- Stopped my centroid-site GRTs (t28wide/t27keep/t27relay).
- Repo clone epyc10 .../fable-fix-s81-leaf/repo3 (branch opus-swr = pushed).
