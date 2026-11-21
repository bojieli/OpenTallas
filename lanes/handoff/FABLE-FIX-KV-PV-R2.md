# FABLE-FIX-KV-PV-R2 handoff (KV pv family owner: kv3_pv*, pv_pair; successor of FABLE-FIX-KV-PV-2140)

Written 2026-11-20 12:3x PST. Posts lanes/posts/FABLE-FIX-KV-PV-R2.md. Lane dir epyc7 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-r2
(repo = lane clone of main, tools/ = scripts, out/ = dumps, por_<tag>/ = private plan dirs, kit/<tag>/ = private kits).
Hub logs and chains: intel2 ~/tmp/ffkpvr2 (chain_r2.sh TAG LABEL, chain_<tag>.log, kit_<tag>.log, watch_r2.sh posts AUTO-KIT lines).

## STAND-DOWN 2026-11-20 18:1x PST (read first; FABLE-FIX-KV-PV-R2 stopped on COORD order, successor takes the kits to sign-off)
State of the three private kits (epyc7, crit, goal route, 64 GB / 16 thr; clients on intel2, logs ~/tmp/ffkpvr2/kit_<tag>.log):
- v8m (flip + station 300 + split rows): in CTS since about 15:5x PST.  dly_spread max_hop 1,404 um, fail 70.
- v8c (control, no flip): in CTS.  max_hop 1,404 um, fail 66.
- v8p (v8m + pad_min_stations 16): 3_place.odb written about 17:0x PST, in CTS.  dly_spread: astk worst hop 801 -> 356 um
  (stages 10 -> 12 groups, ideal 220), chains over 300 um 5,807 (v8m 6,151), fail 70 -> 32, BUT max_hop still 1,228 um.
NOT DONE when I stopped:
- The 1,228-um hop of v8p is NOT identified.  The census is queued, not run: intel2 chain ~/tmp/ffkpvr2/chain_hops.sh v8p
  (PID 4135070 at 17:12) waits for memory on epyc7 (admits 0 GB since about 17:05), log hops_v8p.log.  When it runs it writes
  epyc7 out/v8p_hops.tsv and intel2 ~/tmp/ffkpvr2/hops_v8p.txt (an7.py summary, hops over 450 um by class, direct distance).
  Read the top classes: a class at 1,2xx um that is not a tail copy and not u_pd<N>_ (for example u_d<N>_* T/Q relay lines,
  D 17 / 18, 3 segments today, or a first hop from a cland / bin source into a line) is the next row.  If it is a u_d<N>_ line,
  widen PAD_RE in kit_dly_lockup.py to those names (same rule); if it is a source -> first stage hop, it is a bind stage count.
- No CTS setup read, no GRT iteration 5, no sign-off, no export.  Nothing is proved.  No row was sent as READY.
Rows as they stand for KV D27 (owner of the event: KV-PLAN-R2; cut 11-21 20:00):
- ROW A (candidate, unproved): flip of the upper near pair, rows script (no options) -> 64 cores on 16 types.
  Take it only if v8m is cleaner than v8c at GRT iteration 5 on the upper strip / pin edge tiles.
- ROW B (tool on main 5aa3d06462, partly shown): budgets.r_dly_lockup.kv3_pv.pad_min_stations 16
  (rows script --pad-min-stations 16).  Shown: astk hop 801 -> 356 um at dly_spread.  Not shown: CTS setup.
- ROW C (open): whatever the 1,228-um hop needs.
- ROW D (proposal only, needs the bind): ft0 leg out of the centre street.
Watcher: intel2 watch_r2.sh (PID 1223454 at start) posts AUTO-KIT lines for v8m / v8c / v8p / v8k incl. GRT_IT5_OVERFLOW.
Inherited to-do still open: v8j CpuShares back to 1024 when it routes / fails (epyc10).

## Update 2026-11-20 16:1x PST (read first; supersedes the 'NOT pushed' and watcher lines below)
- pad_min_stations is ON MAIN: ddb2501006 (kit_dly_lockup / gen_phys / schema.py / tests) + 5aa3d06462 (die_plan.schema.json),
  ot-push-main PUSHED main @5aa3d0646265.  Absent key = unchanged kit.  Lane clone is on main again (no local edits).
- v8p GEN passed 14:17 PST and the kit launched: OT_DLY_LOCKUP segments 58,631 (v8m 46,186), latches 66,375 (v8m 54,175),
  stages 143,468 in both.  16:06 PST: v8p in 3_3 place; v8m and v8c in CTS (clock taps written).
- Watcher restarted with v8p (intel2 ~/tmp/ffkpvr2/watch_r2.sh, PID 1223454 at start).
- First check for the successor: v8p 3_4 OT_DLY_SPREAD max_hop against 1,404 (v8m / v8c).

## Update 2026-11-20 14:3x PST (read first)
- THREE private kits on epyc7 (crit, goal route, 64 GB / 16 thr, DO_NOT_COUNT, .keep_stage_odbs; tree4c data + bind4c RTL):
    v8m = flip + station 300 + R3 split rows + form C, tools main 38cdd37cec9.  Launched 12:08 PST; 13:11 PST place hooks:
          OT_TAIL_SITE 9,112 of 9,112, merged 0, core_crossing 0, max_hop 412.3, over_380 119; now in 3_4 / 3_5.
    v8c = control, no flip (over_380 172).  Same stage.
    v8p = v8m + budgets.r_dly_lockup.kv3_pv.pad_min_stations 16, tools = lane branch (below).  Chain started 14:2x PST
          (intel2 ~/tmp/ffkpvr2/chain_v8p.log, kit_v8p.log); GEN not yet confirmed when this was written: check
          epyc7 fable-fix-kv-pv-r2/kit/v8p/gen.out = RC_GEN 0 and gen.log OT_DLY_LOCKUP (more segments than v8m).
- TRUNK SETUP ROOT CAUSE (measured: v8j CTS placement, one astk bit traced; v8m / v8c 3_4 dly_spread max_hop 1,404 um, fail 70 / 66):
  form C makes a SEGMENT one placement station.  seg 8 cuts the sparse astk owner-response pad lines (D 7..11 over 3.1-3.6 mm)
  into 2 segments, so sg0.q -> latch -> sg1.r[0] is one 1,404-um hop while r[0..2] and q sit on one spot.  The anchor
  c6ab8bd7be (REPFIX, 119 repeaters) only removes the wrong-side inverter (685 um out and back).  v8m and v8c therefore still
  carry this class at CTS: do not read their TT as the trunk proof; they are the GRT A/B for the flip.
- FIX, in the lane clone, NOT pushed: branch claude/fable-fix-kv-pv-r2-padstations in epyc7 fable-fix-kv-pv-r2/repo
  (uncommitted edits: tools/die_plan/kit_dly_lockup.py, gen_phys.py dly_lockup_cfg, schema.py, test_kit_dly_lockup.py + 3 tests;
  15 tests pass).  Option pad_min_stations N: a non-tail u_pd<N>_* line gets segment size min(seg, max(1, D // N)); absent / 0 =
  unchanged kit.  To do: commit (trailer Claude Fable 5.2), push with ot-push-main, then post the plan row
  (rows script --pad-min-stations 16).  Cost: about +5k latch bits on kv3_pv_v8 (astk 512 bits, ctl_cmd, vport D 36-44).
- Watcher intel2 ~/tmp/ffkpvr2/watch_r2.sh (PID 3075362 at start) covers v8m / v8c / v8k, NOT v8p: after a cmdline check kill that
  exact PID and restart it with v8p in the kit list and in the pgrep pattern.
- Next reads: (1) v8p GEN + 3_4 OT_DLY_SPREAD max_hop (must fall from 1,404 to about the 405-um class); (2) CTS of v8m / v8c / v8p:
  tools/run_sta.sh + an4.py on a copy of 4_cts.odb / .sdc in db/ (trunk q class gone only in v8p); (3) GRT iteration 5 of v8m
  against v8c: upper strip, pin edge, centre street (tools/grt_cap.tcl + an5.py give tracks per region; scratchpad cls.py splits
  reserved rows / core boxes); (4) if v8m is cleaner: READY-ROWS to KV-PLAN-R1 for D27 (cut 11-21 20:00); if the centre street
  still overflows, row 2 (ft0 leg) goes to KV-PLAN-R1 as a bind-side row.
- Tools in epyc7 fable-fix-kv-pv-r2/tools: dump_nets.py / run_dump.sh (net terminals), hops.py / run_hops2.sh + an7.py (long
  zero-logic hops), sta_ends.tcl / run_sta.sh + an4.py (setup end classes), grt_cap.tcl / run_grt.sh + an5.py, an1-an3, an6.

## Live
- v8m (epyc7, crit, goal route, 64 GB / 16 thr, launched 12:08 PST): D27 candidate = flip of the 4 upper near pairs + station 300
  + R3 split reserved rows of kv3_pv_v8 + form C, tools main 38cdd37cec9 (has c6ab8bd7be, b699b5b678).
- v8c: control, same without the flip.  Both: tree4c data + bind4c RTL (copy of v8k rtl), DO_NOT_COUNT, .keep_stage_odbs.
- GEN on this 405-um bind needs OT_RESET_HOP_CAP_UM=405 (tools/gen_r2.sh); without it the reset identity guard refuses.
- Inherited, untouched: v8k (epyc7, in place), v8h / v8j (epyc10; v8j finished CTS 11:15 PST, in TT repair).  v8j CpuShares 10240:
  set back to 1024 when it routes, fails or is cancelled (intel2 ~/tmp/ffkpv2140/restore_v8j_cpu.sh is armed).
- Cancel only with ot-run --cancel <kit path>.

## Found (all measured on the v8j CTS DB unless marked)
- kv3_pv_pair: 1,670 signal pins, all M5 on ONE long edge.  Stack per group: far pair / near pair / join / near pair / far pair.
  Lower near pair to join: 77.76-um strip.  Upper near pair (origin y 803.52) to join: 25.92 um.
- Net edges leaving the strip over the join sideways (E / W / through): g2 upper 2,779 / 2,172 / 390; g1 upper 1,382 / 1,705 / 328;
  g3 upper 713 / 1,166 / 15; g2 lower 2,458 / 2,357.  Content: near-pair pad tails with their last delay stages, the 579-bit near ts
  funnel, T/Q relay ranks, 258-bit o_pvw stations along y 777.6.
- GRT iteration 0 with the kit capacity hooks (out/v8j_it0b.cap.tsv, usage / tracks incl. blockages): g2 upper strip 136 %, g3 101 %,
  g2 lower 93 %, g3 lower 75 %; pair channel row3-row4 75 % / 62 %; centre street (x 1028-1131) y 800-900 H 106 % / V 116 %.
  Over the pair: M2/M3 full, M4 about 90 %, M5 83-89 %, M6 74-79 %, M7 74-85 %, M8 68-71 % used.
- The far pair bus (1,024 bits to the join W/E face) crosses the near pair on M5/M7: 7,281 forced crossings.  No pair -> join ts end
  is among the 14,305 negative setup ends, so that link needs no pipe stage.
- D23H it15 markers by position (I): H overflow 0-100 um from the upper near pair pin edge, capacity 0; V overflow on the pin row.
- Setup ends at CTS, placement RC, v8j (405 um, before the anchor): trunk terminal q 2,141 ends to -8,203 (wrong-side inverter;
  c6ab8bd7be), tail terminal q 10,953 ends, median -111 to -129, worst -456 (405-um hop; station 300), pair pe2 pins 486 to -759,
  ctl_cmd tails 367 to -506.
- Centre street carries ft0 (1,056 bits, stations x 1059) + the vport pad trunks: 2,579 to 4,720 vertical edges per cut in 103 um.

## Rows
- D27 row 1 (in proof): lanes/handoff/FABLE-FIX-KV-PV-R2-rows.py PLAN_C.json  (--check = report).  64 cores on 16 types:
  R0 -> MX, MY -> R180 on the pair whose pin edge is < 40 um from its join.  Same origin, outline, tap xy.  0 cycles, no RTL.
  Needs a rebind (tail K from the new pin edge).  Not proved until v8m reads GRT iteration 5.
- D27 row 2 (proposal, not built): ft0 vertical leg out of the centre street into the 253-um street x 1511-1764, then west in the
  top band; same station count.  Touches ft_slots regs / bit sites and the ft0_o START branch, so it needs the bind.
  Decide on the centre-street tiles of v8m / v8c at GRT iteration 5.

## Read order when the kits move
1. 3_3 hooks: OT_TAIL_SITE (max_hop, core_crossing), 3_4 OT_DLY_SPREAD (chains over station, fail count) v8m against v8c.
2. CTS: tt_setup_repair "before" wns; classify with tools/run_sta.sh + an4.py (trunk q class must be gone in both arms).
3. GRT iteration 5: congestion-5.rpt through scratchpad cls / tools/an5-style split (strip, pin edge, centre street, reserved rows).
4. Sign-off only if TT >= -42, FF hold >= 0, DRC 0; private kits never count; export comes from a wave kit on the applied plan.
