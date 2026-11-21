# FABLE-FIX-HEAD-LEP0N handoff (Fable; started 2026-11-20 15:25 PST; written for a successor 17:25 PST)

Task: own HEAD hd_lep0N (26th HEAD type) to sign-off and export (AGIdock + rtx-pro ~/signed-export-1114). 833 ps fixed;
hold structural; setup by stages; no outline growth. r14 (HEAD-R14, epyc7 unit oth-ubuntu-3749621-1795200539, kit
/srv/opentallas-scratch2/claude/head-crossing-1119/r14/lep_hop300/hd_lep0N) is NOT ours: never cancel; if it signs off it wins.

Lane dir: epyc7 L = /srv/opentallas-scratch2/claude/fable-fix-head-lep0n. Sources L/src. Lane clone L/repo (nothing committed, nothing pushed).

## Diagnosis (measured on r14 4_cts_pre_tt.odb, FF, before repair: L/census/*.tsv, census.log, L/cz.py)
- Window = kit SDC: 56 of 251 tap ports (clk_t191..t246, 16,035 of 82,912 sinks) at default [-169.8, 0]; priced taps
  -31..+39 (20 ps band); core taps 140..196 ps late (pin 142 ps of leg + 607 internal vs 450). Core ETM clock tree 501..607.
- Hold 25,787 ends: flop->flop cross-tap 13,428 (2,171 left when only the modelled window is removed, worst -184);
  flop->core pin 2,290 (worst -389); ring inputs 8,464 (lepk -77, coll -35); port_out 855; same_tap 336.
  Reset fan 907 removal ends, worst -261, all window. Setup (TT, placement, pre-repair) 132 ends, worst -364, all cross-tap.
- Global place: r14 placed with the S81 early exit (-overflow 0.25, iter 339; avg displacement 0.7 um, max 238). Signed
  HEAD kits: NF13a / NF15d2r1 without it; NF15f_r3 and kw_r9 types signed WITH it. OT_GRT_ALLOW_CONGESTION was never in
  a signed HEAD config.mk. Fix d98908b665 is on origin/main (checked 17:20).

## Form built: type-root clock in the kit (OWNER 11-20 #5)
- type_root.tcl (PRE_CTS after clock_taps + reset_taps): each loaded clock source port's sinks -> net trtap_<port>_net
  behind buffer trtap_<port> (BUFx12 at the port XY) on the root net (port clk). Other tap ports stay as unloaded pins.
  Generated (forwarded) clocks re-sourced at clk (golden SDC edited the same way).
- subtree_balance.tcl patched (base = subtree_balance_r14.tcl): OT_CORE_TAPS pins are sinks at pin + insertion_ps (553.42).
- type_root_balance.tcl (cts_post after leaf_affinity; tapbal_grt on GRT RC): balance port clk, then bind the root latency:
  late = OT_VCLK_TT - median insertion, early = late - W; FF by ratio OT_VCLK_FF/OT_VCLK_TT. Rewrites session,
  constraint.sdc, core_taps_ff.sdc, sdc_lint.json tap_offset_ps.clk, type_root_bind.log.
- tap_balance.tcl = report-only wrapper (base tap_balance_base.tcl).
- Kit assembly: L/src/assemble2.sh <name> (rsync of the r14 kit through 3_place + patches + resume.json start cts).

## tr1 (L/tr1/hd_lep0N; client pid L/tr1.otrun.pid, log L/tr1.otrun.log; goal route; RUNNING, in GRT stage 17:25)
- Works mechanically: 251 tap buffers, 82,924 clock pins, CTS root tree on 251 sinks; balance p1..p99 263 -> 23 ps,
  3,567 pads. FF hold gate before repair: -154.42 on 12,363 ends (r14: -388.93 on 25,803). TT setup after the
  placement-RC repair -190.90 (r14 -171.65).
- DEFECTS: (1) insertion 2,365 ps: the TritonCTS root H-tree has path depth 38 and 1,929 um average sink wire. Not a
  sign-off form. (2) One SRAM (g_tx[3] bank[2]) 306 ps early: macro subtrees were "fixed". (3) My rsync excluded
  pregrt_ff_hold.tcl, so the pre-GRT hold build fell back (file restored 17:22; the in-flow GRT repair takes the debt).
  (4) config.mk pins OT_SIGNOFF_SDC_SHA bd28827c9f779cfc while the golden SDC is rewritten: unknown effect at sign-off.
- Let it run; read hold cells, GRT TT, the GRT-RC bind line, and whether sign-off accepts the rewritten SDC.

## tr1b (L/tr1b/hd_lep0N; pid L/tr1b.otrun.pid, log L/tr1b.otrun.log; goal cts; RUNNING)
- Same as tr1 + CTS_BUF_DISTANCE = 200 + macro subtrees balanced (OT_STB_BLOCK_SINKS sink). Read: "Path depth" of net clk,
  OT_STB before / done, OT_TYPE_ROOT_BIND median. Target: insertion under ~900 ps. If good, continue it with goal route
  (same resume.json; do-cts is then in the done list).

## Next (successor)
1. tr2 = the sign-off candidate: regen hd_lep0N from the HEAD plan (r13r NOMCAP source, HEAD-R14 plan delta at epyc9
   head-crossing-1119/r14/lep_hop300/r13r_lep_plan_delta.json) on a runtime at or after d98908b665 (stock global place),
   from synth, with the type-root files and the tr1b trunk setting if it holds. This is also the HEAD tools re-pin proof
   COORD asked for (HEAD tools 904 commits behind): post the gen runtime sha with the result.
2. FABLE-CLOSURE-1730 lever 7 (price the 56 default taps on the r14 form) applies as the cheaper arm, not built here: it
   needs die spine arrivals for clk_t191..t246 as plan clock.tap_offset rows (HEAD-R14 / die clock tool). It removes
   the default-window ends (about 10,700) but keeps the priced spread (2,690 priced->priced ends) and the late cores
   (2,290 ends, -389), which need the core taps re-timed to pin + 553. Build it as an r14 fork if the rows exist.
3. Lockups (intel2 /srv/opentallas-scratch2/claude/lockup-station-1130-rows/lep_spec_nl.json) only if tr2 still shows
   a large flop-pair class; they need a rebuild from synth.
4. Move type_root*.tcl and the subtree_balance patch into tools/die_plan (main's subtree_balance.tcl differs from the kit
   copy; port the three hunks), with a plan key (clock.type_root) and gen hooks; push only after a kit signs off.
5. Die rows for HEAD-R14: hd_lep0N takes one root at port clk, delivered (insertion - 450) early, value in
   type_root_bind.log; die STA --type-root for this type.
