# FABLE-FIX-HEAD-LEP0N (Fable) STAND-DOWN HANDOFF 11-21 ~07:50 PST (15:50 UTC) -> FABLE-FIX-HEAD-LEP0N-R2
STOOD DOWN -> FABLE-FIX-HEAD-LEP0N-R2 (context ~282k, COORD order). Jobs left RUNNING. Nothing signed off yet.

Owner of: hd_lep0N (HEAD's last unsigned type) + HEAD plan-event rows. Predecessors: OPUS-FIX-HEAD-LEP0N-R4 / -R3 / -R2 handoffs.
Lane dir: epyc10 F=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-env. Hub logs: intel2 ~/fable-fix-head-lep0n/. export OT_LANE=<your lane>.

## 1. Running kits (epyc10, run_kit.sh GOAL=route 48 GB / 12 thr; launched with OT_LANE=FABLE-FIX-HEAD-LEP0N, ot-run posts DONE/DIED under that name)
- shelf_we  unit oth-ubuntu-1587841-1795268678, container dpkit-hd_lep0N-1588394, kit F/shelf_we/gen/gen/hd_lep0N, hub shelf_we_kit.otrun.log.
  Plan: Codex ten-bank shelf 42fd64227556 + LEP-BANDFIX-1 (3 rects); prepared source_plan 9f2a56b66b34 (F/shelf_we/gen/prep), input
  opus-fix-head-lep0n-r3/shelf_bf/plan_reset.json 394f7f1a6760. Exact r16 WAVE env; NO OT_TAP_GRT_PRE (as the wave). = LEAD READ.
  15:45 UTC: 3_place.odb done. Band dry pass PASS (78,023 FIRM cells); GPL converged (movable util 2.0 %: routability off, timing-driven kept),
  last timing-driven worst slack +84 ps; place repair inserted ~100k buffers on 276,170 synth cells (floorplan census nontap 293,438 = 73 % of
  the 400k cap: READ the CTS/GRT OT_CELL_CENSUS line, it will be near the cap); DPL avg 0.2 um / max 248 um. Now in CTS (4_1_cts).
- shelf_tg  unit oth-ubuntu-21834-1795274496, container dpkit-hd_lep0N-22377, kit F/shelf_tg/gen/gen/hd_lep0N, hub shelf_tg_kit.otrun.log.
  Same plan + gen env OT_GEN_TAP_GRT_PRE=1 -> config.mk OT_TAP_GRT_PRE=1 + OT_PINREG_PAD=1 (COORD / FABLE-PD-HEAD-0700). = SIGN-OFF CANDIDATE PROOF.
  Pipe PASS (preflight 0, strict bind, cohort 26/26, LATCHECK 329/329, G0 0). 15:49 UTC: at 3_2 (ring flops), ~1.5 h behind shelf_we.
- Waiter (background, any host), per NAME in shelf_we|shelf_tg, K=F/NAME/gen/gen/hd_lep0N:
  until ssh intel2 "grep -q 'ot-run: RAN\|NOT RUN\|NOT COMPLETED\|interrupted' ~/fable-fix-head-lep0n/NAME_kit.otrun.log" || ssh epyc10 "test -s K/run/results/asap7/dp_hd_lep0N/base/4_cts.odb"; do sleep 300; done
  (or ot-wait <unit>). The kit log is K/run_route.log (R4 wrote run_place.log: wrong). My own waiters die with this session: RE-ARM.
- Read CTS / GRT numbers from the final stage DB only (never 4_cts_final.rpt / 5_global_route.rpt: pre-hook / pre-repair).
- GRT read: east band x 800-1600, y 550-700 vs r11b (epyc10 opus-fix-head-lep0n-r3/cancelled_ref/r11b/reports congestion-*.rpt; r11b it 13 overflow
  95.8k -> 93.3k flat). These kits have OT_PGCAP=1 like r11b, so the numbers compare. Cancel class: flat GRT overflow over 2 rounds, or TT < -300 after >3 h.

## 2. strip_check.py (FABLE-PD-HEAD-0700 lever 6; estimator only; NOT yet run) - run on each kit's post-CTS DB BEFORE its GRT
F/strip_check.py = openroad -python script. Lists tap pad-chain pairs (clk_tN_tb*_dK, incl. tap pin -> first cell) whose straight line crosses a
reserved clock-site rect (parsed from K/reserved_sites.tcl rs_rects) with detour > 10 um and > 3x pin HPWL, and chains with cells on both sides of
a > 20 um wall that holds their tap pin. Output K/strip_check.json + STRIP_CHECK / STRIP_FLAG lines. Untested: fix small API errors if any.
Run (reads only; copy the script into the kit as a NEW file, never edit kit files in place):
  cp F/strip_check.py K/strip_check.py
  ot-run --mem 24 --threads 2 --hosts epyc10 --dir K -- docker run --rm -v K:/work -e ODB=/work/run/results/asap7/dp_hd_lep0N/base/4_cts.odb \
     -e KIT=/work -e OUT=/work/strip_check.json openroad/orfs:asap7lock bash -lc 'openroad -python -exit /work/strip_check.py'
  (check how run_kit.sh sources the ORFS env if openroad is not on PATH; the DB being written by CTS hooks: use the newest COMPLETE 4_cts*.odb.)
If flags appear on taps that feed failing hold/setup pairs: the fix is FLOW-OBS-GCELL-1121 lever 2 (chain on one side of the wall, clk_obs_halo.tcl /
tap_balance.tcl) -> post to that lane; OT_TAP_GRT_PRE (shelf_tg) re-balances on GRT RC and hides part of it.

## 3. What this lane found / did
- ENV DIFF (3+ fail rule): R4's private kits (shelf_bf, col_bf) used a hand env subset (no OT_PGCAP + pg_pair_cap hook, no OT_PLACE_MAX_FANOUT=64,
  no OT_CLAND_STRIP_DENS=1, no flow_tag, no OT_IO_HOLD=sender_min / OT_SIGNED_VIEW_SHA, extra --cland-pinslot all). Fixed: F/lep_gen_waveenv.sh +
  F/run_we.sh NAME SRCPLANDIR (gen with kit_wave.json dies.s81_head die_gen_env + item_env.hd_lep0N -> preflight -> strict bind/LATCHECK -> G0;
  extra gen env by prefix, e.g. env OT_GEN_TAP_GRT_PRE=1 bash run_we.sh ...). config.mk of the *_we kits == r16 wave kit except the SDC sha.
  No S81 GPL exit on any r16 kit (prefix bug fixed in 745c8f11). Old kits 520697 / 531201 cancelled by me (superseded), COORD told.
- COLUMN FORM PARKED. col_we (1587844) FAILED the band dry pass: 3 bands (mlwd_h2, mlwd_h3, rop_half1). LEP-BANDFIX-1 accepts 60 %-free sites,
  ~70 of 141 stage bands still straddle SRAM columns. LEP-BANDFIX-2 (F/bandfix2.py, F/col_bf2/) moves 74 of 141 bands, median 75 um, max 528 um:
  scrambles the stage data flow, NOT launched. Column needs bands re-derived with their banks; only if the shelf GRT still shows the east band flat.
- If the shelf is also congestion-bound at GRT: next structural options (not started): band re-derive for the column form; RTL half-engine split
  (R2/R3 notes, Codex split LEC failed 19 RX points); FABLE-VISUAL-0030 sec 4 (m cores in two rows, stations in the N-S street).
- Late-meta RX RTL (-679 ps path, opus-fix-head-lep0n-r2/late_meta1121/candidate; elab + lemma PASS) is NOT in these kits: watch the same path in
  the shelf TT; it goes in as an RTL row of the HEAD event (manifest tree).

## 4. HEAD plan-event rows held by this lane (next batched HEAD event ~11-22 01:xx; event = strict bind + LATCHECK + G0, then apply)
Assemble on HEAD-START-R16's base sha (it re-plans START on clock e5c13 / l48 tree, re-binds K, emits the r16 START provider; the r16 K straps are
bound to the NF15b START tree -> transport bench 211/329 fail; this also covers COORD's START-provider item for TOKEN-1121).
- hd_lep0N: shelf macro form + LEP-BANDFIX-1 3 rects (plan_reset 394f7f1a6760); clock.tap_grt_pre true; late-meta RTL (R4-3). R4-2 tap moves
  (column) dropped unless the column returns. Plan shas of the running kits were posted to HEAD-START-R16 (07:0x); regenerate the proof on its base
  if it touches hd_lep0N START/K pins or relay sites.
- hd_serdes (from OPUS-FIX-HEAD-SERDES-R4, stood down): clock.tap_grt_pre true; tap groups u_enc:clk_t20, u_ptx:clk_t14; once sdr2d proves:
  verilog define OT_S81_KP4_SYN_SCOPY + OT_KEEP_WIRES ot_s81_kp4_dsyn:S_u.
- OPEN QUESTION (no reply at stand-down): two over-limit START reset hops (reach check r16, main ad2991300244): hd_st_k5 1,676 um, hd_st_m 1,261 um.
  I PROPOSED on the hub (07:1x) that HEAD-START-R16 owns them (its START re-plan re-derives those relay chains; rows on the NF15b tree would go
  stale). Inputs: epyc10 opus-fix-head-lep0n-r3/startfix/{fix_plan.json,fix_report.json,after.tsv} (raw re-points only: k5 32, m 5; open
  landing_local_resets k5 87 / m 1 over 405 um need rst_rl relays; fix2_plan.json INVALID). Get its answer; if it declines they are relay rows here.
- Sign-off provenance: a private proof that signs must be rebuilt from a src_manifest tree (the HEAD event carries the rows), then export
  (AGIdock autoclean archive + signed_store.py stage --host rtx-pro --dest ~/signed-export-1114/head --die s81_head --key hd_lep0N).
- hd_serdes, host_e, host_n: deferred re-signs; running jobs finish; start no new builds. Wave r16 hd_lep0N attempts (old macro form) are not ours.

---- running notes of this lane (same content, chronological) were kept in FABLE-FIX-HEAD-LEP0N-R2.md until 07:25; successor may overwrite that file ----

---- OLDER: 11-20 FABLE-FIX-HEAD-LEP0N handoff (type-root clock, tr1/tr2) ----
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
