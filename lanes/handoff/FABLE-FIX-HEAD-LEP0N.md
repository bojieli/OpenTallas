# FABLE-FIX-HEAD-LEP0N handoff (Fable, started 2026-11-20 ~15:25 PST)

Task: own HEAD hd_lep0N (the 26th HEAD type) end to end to sign-off. 833 ps fixed; hold structural; setup by stages
(+cycles pre-approved); no outline growth. r14 (HEAD-R14, epyc7 unit oth-ubuntu-3749621-1795200539, kit epyc7
/srv/opentallas-scratch2/claude/head-crossing-1119/r14/lep_hop300/hd_lep0N) is NOT mine; never cancel it; if it signs
off it wins.

Lane dir: epyc7 /srv/opentallas-scratch2/claude/fable-fix-head-lep0n (L below). Lane clone L/repo (main 8e9cdd615c, nothing committed yet).

## Diagnosis (measured, r14 4_cts_pre_tt.odb, FF, before repair; L/census/{hold_ends,setup_ends}.tsv, census.log, L/cz.py)
- The window is the kit SDC: 56 of 251 tap ports (clk_t191..t246, 16,035 of 82,912 sinks) carry the default
  [-169.8, 0] (no priced offset); priced taps -31..+39 with a 20 ps band; core taps clk_c0..3 are 140..196 ps late
  (pin arrival 39 / 4 / -17 / 23 + 607 internal vs 450). Core ETM internal clock tree 501..607 ps (TT), input hold up to 602.6.
- Hold 25,787 ends: flop->flop cross-tap 13,428 (2,171 left once the modelled window is removed, worst -184);
  flop->core pin 2,290 (worst -389); ring inputs 8,464 (lepk -77, coll -35); port_out 855; same_tap 336.
  Reset fan: 907 removal ends, worst -261, all window; 0 on the setup side.
- Setup (TT, placement, pre-repair) 132 ends, worst -364; all cross taps; after the TT repair r14 read -171.65.

## Form: type-root clock in the kit (OWNER 11-20 #5); no lockups, no netlist change in build 1
- type_root.tcl (PRE_CTS, after clock_taps.tcl + reset_taps.tcl): every loaded clock source port's sinks move to
  net trtap_<port>_net behind buffer trtap_<port> (BUFx12, at the port XY, or at the sink centroid when the port is
  over a macro) whose input is the root net (port clk). Tap / core-tap ports stay as unloaded pins. Forwarded
  (generated) clocks re-sourced at clk.
- subtree_balance.tcl patched: a core clock pin listed in OT_CORE_TAPS is a sink at pin + insertion_ps (553.42), also
  under OT_STB_BLOCK_SINKS=fixed. Stock behaviour without OT_TYPE_ROOT=1 (base kept as subtree_balance_r14.tcl).
- type_root_balance.tcl (cts_post.tcl after leaf_affinity; tapbal_grt.tcl on GRT RC): balance port clk, then BIND:
  root latency late = OT_VCLK_TT - median insertion, early = late - W (169.8); FF = OT_VCLK_FF - median x FF/TT.
  Writes the session, /work/constraint.sdc, core_taps_ff.sdc, sdc_lint.json tap_offset_ps.clk, type_root_bind.log.
- tap_balance.tcl = wrapper forcing OT_TAP_REPORT_ONLY=1 (base tap_balance_base.tcl).
- Sources: L/src/. Kit: L/tr1/hd_lep0N = rsync of the r14 kit (results through 3_place) + the patches + resume.json
  start cts. sdc_lint PASS, kit_preflight PASS.

## Build 1 (tr1)
- Launched 15:5x PST: L/launch_tr1.sh -> ot-run --priority die 96 GB 16 thr, goal route. Client pid L/tr1.otrun.pid,
  log L/tr1.otrun.log; kit logs in L/tr1/hd_lep0N (run/logs/.../4_1_cts.log, pregrt_ff_hold.log, run_route.log).
- Read in order: OT_TYPE_ROOT (taps converted), CTS root net handling, OT_STB rounds, OT_TYPE_ROOT_BIND (insertion
  span + root latency), then OT_PREGRT_FF_HOLD class before (r14: 25,801 ends) and TT setup.
- Untested on a real DB before this launch: TritonCTS on a root net of ~251 buffer inputs, the balance run time
  (12 rounds), the bind file rewrites inside the container, sign-off reading the rewritten golden SDC.

## If build 1 fails
- CTS error in my hooks: fix in L/src, copy+mv into the kit, relaunch (resume.json already starts at cts; delete
  nothing: do-cts reruns because 4_cts.odb is absent / .kwrs_done lacks it).
- Residual cross-tree hold cells high: add the netlist lockup pass (clock.zl_lockup, intel2
  /srv/opentallas-scratch2/claude/lockup-station-1130-rows/lep_spec_nl.json); that needs a rebuild from synth.
- Die side (HEAD-R14 next event rows): hd_lep0N takes ONE clock root at port clk, delivered (insertion - 450) ps early
  (value in type_root_bind.log), as an early core tap / hard_core_latency contract; die STA --type-root for this type.
