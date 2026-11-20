# FABLE-FIX-KV-PV-2140 handoff (KV pv family owner; newest first)

## Status 2026-11-20 06:40Z: form C built and on main, rows posted for D25f, proof kits in gen. NOTHING PROVED YET.
Lane dir epyc10 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-2140 (repo = lane clone, tools/ = kit patch scripts, kit/ = private kits).
Hub scripts + logs intel2 ~/tmp/ffkpv2140 (chain_formc2.sh TAG TREE HOST; chain2_<tag>.log; kit_<tag>.log).
Opus lane (posts as FABLE-FIX-KV-PV) base: epyc10 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-1119/compose (tree2 / bind2 dense +843 old tools;
tree4c / bind4c = D25e form with TRUNK-CHAIN tools, bind RED only on the 2 kv3_hgi_v1 EMIT errors of the control).

### Decision: hold form C (lockup at every tap-group boundary of the pad delay lines, RTL, launch tap, 0 cycles)
- Facts (v8b, checked): 159,831 delay-line flops, 142,464 zero-logic transfers; 47,549 cross-tap FF hold ends = 37.6k inside
  ot_dp_dly instances + 4.3k tail copy -> core pin (-135.1 join_go) + 1.0k trunk -> tail + about 2k core-launched.
  Kit charges 74.9 ps per tap crossing (no CRPR), die tree delivers 163 ps spread; pv core taps are early 0 with 210-228 ps insertion,
  so every core input pin needs 100-140 ps of hold (lib) and has -80..-115 ps setup: lockup is the fitting form there.
- Tool kit_dly_lockup.py (main 29d0a6105e4c): trunks split into <= 8-stage segments, tail copies one group per stage (K is sized from
  the trunk end -> pin route), ot_dp_lk u_fl_* on each boundary, on delay inputs fed by another delay, on outputs read by a hard core.
  kv3_pv_v8: dense form 63,429 latches, D25e form 54,196.  Not latched: core-launched ends, port inputs, logic readers.
- Flow side: dly_spread.tcl OT_DLY_SPREAD_SEG=1 (latch-delimited stations, latch at launch station), tail_copy_anchor.tcl (latch = repeater,
  <copy>_sg<j>), OT_TAP_CHAIN_AFFINITY=1 radius 400 group 24, OT_TAP_CAP_RECHECK=0 (the recheck sheds single flops and would split a segment).
- Plan key budgets.r_dly_lockup {type base: {seg, tail_groups}} (gen_phys applies the pass on the staged bound RTL).
- Rows for KV-D23-COMPOSE D25f: lanes/handoff/FABLE-FIX-KV-PV-2140-rows_C.py (posted 22:1x PST).

### Known defects / open
- gen on the 33 MB post-pass RTL as kit-rtl INPUT did not finish in 37 min (stuck before the kit dir is written; suspected
  install_bound_native_reset / early RTL scans).  So the pass must run AFTER those steps: the plan-key path stages first (as written);
  v8j (gen only, main tools + private plan copy por_v8j with rows C) measures that path.  If v8j gen is slow too, find the scan and fix.
- Cells +10 % (539k -> about 600k).  Lever: per-copy K by route in the bind (fewer tail stages), not fewer latches.
- Core-launched hold ends (pair ts -> join 613, T?Q? r.b -> ist / d# about 800, ...) are left to the pre-GRT repair; a launch-clock
  latch on a core tap is NOT a lockup (v8b dry ECO: -946).  port_in 4,448 is a die seam item.
- Not yet shown in a kit: yosys / LEC with 54k latches, tail_copy_anchor + dly_spread SEG in the real flow, tap chain join rate
  (read OT_TAP_CHAIN groups/joined), flop -> latch same-tap hold, latch -> capture setup (T/2 - 75 ps window budget).

### Kits (private, timing-only, DO_NOT_COUNT; goal route, 64 GB, 16 thr, .keep_stage_odbs, ONE session)
- v8h = bind2 (dense, old tools: still has the -675 TRUNK-CHAIN class) + C.   v8i = bind4c (TRUNK-CHAIN fixed) + C: the proof kit.
- Status: `bash tools/kstat.sh kit/<tag>/gen/kv3_pv_v8` on the kit host.  Acceptance: OT_TAIL_SITE merged 0 (v8i), OT_PREGRT_FF_HOLD class
  before cross_tap near the core-launched count (about 2k), post-CTS FF hold >= 0 after repair, TT setup >= -42 routed, 1 CTS pass.
- Opus kits: v8f (form A read), v8g (form B ECO, parallel form), v8e (TRUNK-CHAIN control; its chain stopped at NO_V8_WRAPPER, asked to relaunch).

### Next
1. Read v8h / v8i at synth, place (OT_TAIL_SITE, OT_DLY_SPREAD), CTS (taps, hop latches), pre-GRT FF hold classes; fix form defects the same hour.
2. D25f applies -> wave launches the 16 pv types with C; one lane per failing class.  Sign-off + export (AGIdock /archive, rtx-pro
   ~/signed-export-1114) only from wave kits on the applied plan; the private kits never count.
3. Phase 2 if the core-launched class does not close by repair: capture-side latch (transparent-high on the capture tap) at the core output.
