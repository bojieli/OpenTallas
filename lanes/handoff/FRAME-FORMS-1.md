# FRAME-FORMS-1 handoff (S81 frame family col_h9/col_h10; Fable lane; COORD) -- started 2026-11-13 06:15 PST

## Scope
- DIEVIEW-S81-1113 F1: 216 frame tiles / 26 kit items / 0 signed off. ONE template re-pack under R-STREET-1/2/4 (cores move/rotate,
  never reshaped), applied to all 26 items as template + per-item deltas; plan delta; G0/G0C; strict bind; lane latency; 2 private
  place/GRT/route proofs; ONE S81 frame event READY (adopted after 11-15 04:00). Coordinate with S81-FORMS-1 and HARD-S81-DSDV-1.

## Worktree / files
- epyc7 /srv/opentallas-scratch2/claude/wt/frame-forms-1 (own clone of hub:OpenTallas), branch claude/frame-forms-1-1113.
- Work dir epyc7 /srv/opentallas-scratch2/claude/frame-forms-1/ (insp1.py, rframe.py type renders, base_png/).
- Base plan: wave plan src_s81_main_7073a6b4a5/physical/die_plan/s81/plan_h2_2249.json sha 18c864518844 (ready12b-A).

## State
- 06:2x: read DIEVIEW F1, RULEBOOK R-STREET/R-REACH, METHODOLOGY 12. Rendered the 26 base types (base_png/). Clone running.

## Resumed after FRAME-FORMS-2 HANDBACK (07:26). Work moved to epyc4 (epyc7 was at load 168).
- epyc4 worktree /srv/opentallas-scratch3/claude/wt/frame-forms-1, branch claude/frame-forms-1-1113 (on origin, b74d4c6515,
  off main 5eefdbe2fa). Work dir epyc4 /srv/opentallas-scratch3/claude/frame-forms-1/ (w/plan_A.json = ready12b-A 18c864518844).
- Tools in the branch: events/s81_frame_spine_1113/ (frame_spine_seed.py = the template, park_taps.py, cp_frame.py, finalize.py,
  run_types.sh, README.md).
- TEMPLATE "FRAME-SPINE" (differs from FF-2's FT1 sketch; FT1 was not coded): the east strip becomes a centre spine. W pair at
  x 17.28, E pair at x 859.68; each pair's 7 cfg ROMs stand beside it in 3 abutted columns (3+3+1, 19 um slot under every ROM
  S pin face); centre street 59 um holds the type clock tap. Row street: station + payload at the spine mouth, bs centred
  between the two S pin groups 51.84 under the elements, seq in the street 43.2 under the element, bn 46 above the N pins.
  bf group keeps its x (W half-group -21.6 so the front-roots faces get 43.2), its ROMs/seq/station in one band 43.2 below it.
  Nodes: E zone beside the bf group + row-street outer ends, by connectivity and station reach.
- RESULT so far (2 reps: col_h9_r2 clce45cab5 pv06a1adf6, col_h9_r1 cl49d7a23e pv047ea3b3): core_place applied, EQ ok, every
  station keeps its register count, R-STREET hard kinds 37 -> 0 and 51 -> 0 (street / wall / outline_street / face_street /
  station_alley); left: 18 sliver + 4 outline_sliver WARN per type (ROM S-pin slots, base bf half gap, W margin 17.28).
  route_supply p99 5.9 -> 3.6 and 5.3 -> 3.5. Renders: epyc4 work dir cp1/png.
- OPEN: (1) 13 r0 items (cf 281x69, E/W windows, ft lanes) are seeded but cf has no site and node sites are short; (2) 2
  col_h10_r1 items (two bf groups) do not fit vertically (need 1430 of 1227) and need a variant; (3) all-type run, chain
  (G0/G0C, strict bind, latency), 2 proofs: not started.

## 07:5x-08:xx state
- Template fixes after the first runs (all in branch b74d4c6515): ROM signal pins are on the S face, so ROM columns abut at
  3.0 um sideways (pitch 41.04, 0.108 grid) and keep a 19 um slot under each ROM; the tool wants abut (< 4.32) or >= 43.2
  wherever >= 16 pins face a gap, so bn stands 46 um above the element, seq 43.2 below it, station | payload 43.2 apart.
  core_place quirks handled in cp_frame.py / finalize.py: base outline overlaps 0.54 / 0.89 um; the type clock tap rode with a
  core (restored to base 725.76, 613.44; it is free in the centre street); core taps set to base + core displacement.
- RUNNING: Opus sub-agent FRAME-FORMS-1-VOL on epyc4 (scope: 132 pv types of col_h9_r2 x5, col_h10_r2 x4, col_h9_r1 x2):
  all-type run + merge + finalize, added_tap_recentre, chain, G0/G0C, strict bind, lane latency, 2 private proofs
  (col_h9_r2 clce45cab5, col_h9_r1 cl49d7a23e). It appends lines under "## VOL sub-agent" below.
- r0 (13 items, 72 tiles) NOT in this event. Measured with the template as is (epyc4 work dir r0dev/, why0.py prints the
  blocking rule): col_h9_r0: only two blockers. (a) cf (280.8 x 69.12, 1,170 N + 1,179 S pins) has no site: at its base
  spot it collides with the E pair. (b) on p1-p3 the bf group may not move: ft0 bit sites stand at (1142.6, 980.6+) and
  (473-475, 1150+) beside the base bf cores. Variant that keeps bf at its base y 950.4: row street channel 34.56 -> 21.6
  (S street 129.6), M0 47.52. cf site in the E zone beside bf (x 1144.37, abutted to the E half-group), 43.2 streets N and S,
  clear of the E-face window span: p1-p3 (window y 740-980) cf y 984.96, node rows y 864 and 1097.3 (6 nodes) + 6 row-street
  end sites = 12; p4-p6 (window y 981-1221) cf y 885.6, only 3 node sites above it + 6 = 9 of 12: three nodes still need a
  home. W pair stands 17.28 off the W face inside the W window span (xo_o0 1104 bits): face_street; moving the W unit +25.92
  leaves a 33 um centre street, so the W window rows need their own answer. col_h10_r0 (bf in the middle, 6 ROM groups, 4
  stations): the template applies mechanically but leaves 23 street + 2 face_street + 4 outline_street (bn / t3 at the N face
  under the N window, second bfp group c5/s5 and t3 unassigned).
- col_h10_r1 (2 items, 12 tiles): two bf groups + two rows need 1430 um of 1227: no fit; needs a variant without the bf ROM
  band (ROMs beside the bf groups) or a different unit order.

## VOL sub-agent
- 08:04 T1 all-type run (epyc4 frame-forms-1/all1): 5/11 items ACCEPTED (cl49d7a23e 54, clf32cde8d 6, cl774acf45 5, clb8d86cd5 6, clce45cab5 43 = 114 types, hard street 5112->0); 6 REFUSED at base: 4 col_h10_r2 (applied False, link-length tviol 1/143/20) + col_h9_r2 cl87f3ff59 (tviol 185, SEED-MOVED) + clc9ad8f7e (SEED-MOVED u_e13w.u_view.u_c -> 1 street/type). Chain running.
- 08:12 T2 taps: core_place had CARRIED 152 added taps with their cores (e.g. clk_t20 1070 um west); restored to park_taps xy (all kit-legal, 0 legality moves; added_tap_legalize.py). added_tap_recentre: col_h9_r2 items 0 failing; col_h9_r1 BOTH items (60 types) fail clk_t21 radius 288.7/200 (x1.10 slack) from reset relay rst_rl_77 (1429.32,669.32), no legal single-tap move -> needs an added tap = design call: col_h9_r1 STOPPED (left at base). Chain re-run r2-only (3 items, 54 types).
- 08:23 T3 chain r2-only -> plan_frame_spine_571ca8f7c313 (epyc4 wt physical/die_plan/s81/): recentre 0 failing, collector republished on 11 types (cl774acf45, clb8d86cd5; depth 6=6, relays 121->148, reset taps 32->36), stage tables 0 lanes. Street final 216: in-scope accepted 2052 -> 0 hard. Strict bind + G0/G0C running on epyc4 (vol/).
- 08:39 T3 DONE plan_frame_spine_571ca8f7c313: G0 0 new err (74=base); G0C +4590/-1290 ERR all hard_cores lattice (origins off 8.64) + M4 pins off track (template lattice, design call); strict bind rc0 0 err; latency 873/873 PASS delta {}. Pushed claude/frame-forms-1-1113 8ffe40ee66. T4 proofs running (intel2 /srv/opentallas-scratch2/claude/frame-forms-1-vol/jobs/*/unit.log; clce45cab5 + substitute cl774acf45; cl49d7a23e not built: r1 stopped).
- 08:43 T4 BLOCKED (infra): private kit_wave proofs (clce45cab5, substitute cl774acf45) stopped at kit_rtl: ot-run-wave refuses epyc4 for scratch3 dirs (scratch3 = root md0, 137 GB free < 150 keep-free + 40 floor, ROOTSCR_1101). Killed my launcher PIDs; nothing started on epyc4. Needs: epyc4 root >= 190 GB free, or OK to use epyc4 scratch2 / another host. VOL sub-agent done.

## RESULT of the volume run and STOP state (FRAME-FORMS-1)
- NO READY posted. Branch claude/frame-forms-1-1113 @8ffe40ee66 holds the tools, reports and plan_frame_spine_571ca8f7c313
  (3 items only); it is evidence, not an adoptable event.
- CORRECTION: the cfg ROM (ot_rom_4096x72_m8) pins are on the W and E edges (x 0.01 and 38.03, 43 each, M4, y 0.78-4.81),
  not on the S face as I wrote above. The side-abutted ROM columns (3.0 um) of the committed template block those pins.
- G0C: 4590 new hard_cores errors on the 54 applied types (3294 origins off the 8.64 lattice, 1296 pins off track): the
  template must place on the 8.64 lattice (sub-lattice shift only via track_offset_um).
- Passed on the 3 applied items: R-STREET hard 2052 -> 0, G0 0 new, strict bind rc 0 (epyc4 work dir vol/out_fs), lane
  latency 873/873 PASS. 11 types got a republished reset collector tree (relays 121 -> 148, reset taps 32 -> 36).
- Failed at base: col_h10_r2 x4 + col_h9_r2 cl87f3ff59 (links over limit), col_h9_r2 clc9ad8f7e (1 street; bf W group pushed
  by a fixed rect), col_h9_r1 x2 (tap clk_t21 radius 289 > 200; far sink reset relay rst_rl_77 at 1429, 669).
- Proofs: none ran (epyc4 root has 137 GB free, launcher wants 190). Specs are staged on intel2
  /srv/opentallas-scratch2/claude/frame-forms-1-vol/.
- NEXT (successor or me): (1) get the ruling on sparse-pin 17.28 slots (queue line of this stamp); (2) re-grid
  frame_spine_seed.py to 8.64: W pair 17.28, ROM cols as 2 x 4 per pair with 17.28 slots, E pair re-derived, centre street
  >= 43.2 holding the tap at x 725.76; (3) fix per-item deltas above; (4) re-run all1 / vol chain scripts (in the branch);
  (5) proofs on a host with >= 190 GB free. epyc4 vol/ holds 56 GB of mine (bind tree) and can be deleted once re-run.
- Leftover: epyc7 /srv/opentallas-scratch2/claude/wt/frame-forms-1 (my first clone, no unique state) can be removed.

## After COORD ruling (sparse 17.28 slots OK; window-link exemption must be checked) -- re-grid in progress
- Work dir epyc4 /srv/opentallas-scratch3/claude/frame-forms-1/g8/ (ev/ = re-gridded tools, NOT yet in the branch; w/t11.txt =
  one type per in-scope item; cp11/ = current run; run11.log).
- Re-grid: all seeds on the 8.64 lattice, no seq flips (R0), ROM block = col A 4 + col B 3 ROMs with 22-25 um slots on the W/E
  pin faces, W pair x 17.28, E pair x 864.0, centre street 65 um (cols B at 639.36 / 743.04), row pitch 414.72 (S street
  146.88), bf band 112.32, M0 43.2, top 43.2. bn 20.5 um over the N pins (sparse slot). seq x 527.04 / 933.12.
- KEY FINDING: core_place only has the link model for single-type items (type name == core_conns key); for pv types it sees
  1 link, so "applied" on pv types does not prove reach. Judge reach on cl87f3ff59 / cl8b686b3e / clac068e56 (same layouts).
- WINDOW LINK CHECK (bound RTL, epyc4 vol/out_fs/rtl/col_h9_r2__t1__cl87f3ff59.sv): no data bit goes from a window to a core
  directly. frame_int_i0 -> u_bin (1 reg) -> u_lpad (4 reg) -> fields: [348:66]+[614:349] station xai/xbi, [1165:630] payload,
  [629:615] cci. Every element S pin is driven by its bank bs (register) + seq go_tag; line 3508. The 'bus' entries of
  core_conns on element / bs / bn / seq / node / station pins are ONE bit: rst_n = window bit [1166] -> bin 1 + pad 4 +
  u_d7_6 (7 reg) = 12 registers, then one net to every core reset pin of the tile (same structure in the base plan; each
  core has its own ot_rst_relay). So the bus-link exemption in cp_frame.py covers only that reset bit; its last hop is
  tile-wide in base and new alike (half-span sum about 1160 um base, 1260 um new). The planned rs relay station keeps 4 regs.
- OPEN LIST (COORD ruling, event scope cut): "frame reset fan-out to R-REACH reset stations, next event". Not in this event.
  The READY lists the reset net as the ONLY window-link exemption, with the hop table above, and says reach was judged on
  the 3 single-type items (cl87f3ff59, cl8b686b3e, clac068e56) that share the pv layouts.

## State after the confirm run (branch claude/frame-forms-1-1113 @9b19ffb56a)
- Confirm run epyc4 g8/cp4 (measured): cl87f3ff59 (901 links), cl8b686b3e (1019), clac068e56 (280) and the col_h9_r1 rep all
  applied with 0 over-length links, 0 seeds moved. Street errors: only sparse-slot classes, plus "node over a bank at 25.92"
  (2 cases), which the last commit removes by moving the bank to pair x + 276.48 (not yet re-measured: VOL2 task 0 checks it).
- Rulings in force: sparse faces (< 3 pins/um) may face a 17.28+ slot; bank over element N pins 20.5 um and station beside a
  ROM 19.4 um accepted; reset-only exemptions (window reset bit, u_cf.rs); bf col3 pair +26 um; 7th E-pair cfg ROM in the
  street corner because the seq read loop is fixed at 2 edges inside the signed core (no station possible).
- RUNNING: (1) Opus VOL2 on epyc4: rep gate, 132 pv types, taps (col_h9_r1 clk_t21), chain, G0/G0C, strict bind (reuses
  vol/bsrc_fs), latency, 2 proofs via ot-run (intel1 / epyc4); it appends under "## VOL2 sub-agent". (2) Opus R0 sub-agent in
  epyc4 r0v/: the r0 HUB FORM (approved second form: full-height east zone for cf, stations, nodes; cfg ROM placement being
  sized), first on col_h9_r0 p4-p6 (4 items).
- With DIE-S81-89 (queue REQUEST, numbers there): ft0 re-plan for col_h9_r0 p1-p3 and col_h10_r0 p1, height for col_h10_r0 p4
  and col_h10_r1.
- READY scope (COORD): the 11 items now; the 15 others open with owners (me: r0 hub form; DIE-S81-89: ft0 and height).
- Lesson: a wait loop `while pgrep -f X` inside `bash -c "...X..."` matches itself; it cost 3.7 h. Wait on a DONE file.

## VOL2 sub-agent
- 13:36 T0 rep gate PASS (epyc4 frame-forms-1/vol2/rep11, tools @9b19ffb56a): 11/11 applied True, 0 SEED-MOVED, 0 need_more_regs, tviol 0 (single-type cl87f3ff59/cl8b686b3e/clac068e56 links 901/1019/280), street 255 hard all in accepted sparse classes (rom_x/bn_elemN/bn_rom/node_x 17.28), 0 findings; node-over-bank 25.92 gone. Starting all-type seeds/shards (vol2/all2).

## CODEX notes 2026-11-13 13:49 PST
- Collected VOL2 all11 shards:132 types all applied True, no timing/equivalence/schema errors. Private next chain started via ot-run E4 unitoth-ubuntu-3122597-1794606241; intel2 clientPID3884133, log~/codex-s81-log/frame_next.log.
- Existing vol2/collect_codex.py,next_codex.sh merge/finalize then chain.132 types restored120 die-owned taps (0 illegal) and1848 core taps. Tap recenter still CPU-active; no P&R launched before review.
- r0 hub form and ft0/growth open tasks retained; no POR/wave switch.
