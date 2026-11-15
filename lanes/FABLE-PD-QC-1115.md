# FABLE-PD-QC-1115: cbn_q11 5_1_grt no-progress cancel, cb clock-entry advisories

2026-11-15 11:45 PST, FABLE-PD-QC-1115. Read-only; nothing launched, stopped or changed.
Subject kit: intel2:/srv/opentallas-scratch2/claude/pg-aware-1/proof/cbn_c/cbn_q11__cl5cc92dfe (PG-AWARE-1 proof form, kit
generated 11-14 03:58, run restarted from floorplan 11-14 20:05). Read: 5_1_grt.tmp.log, run_route.log, pregrt_ff_hold.log,
hold_gate.log, 4_1_cts.log, congestion-{5,10,15,20}.rpt, layout_review (place), io.tcl, macro LEF, clock_entry_lef.json,
m8_grant.json, config.mk. MEASURED = read or computed from those files today. INFERENCE is marked.
One DB read: 4_cts.odb of the kit, copied to epyc8:/srv/opentallas-scratch2/claude/fable-pd-qc-1115/ and read through ot-run
(3 runs, 24 GB request, about 1 min each; `q.tcl`, `q.out`, `q2.out`, `q3.out` there; the odb copy is removed).

## 0. Answers

1. **5_1_grt was not in any repair loop. It was inside FastRoute `global_route` itself and never finished the first global
   route.** No repair_design, repair_timing, hold repair, antenna or incremental GRT ran in this stage. The
   "repair_Violations 19 rows, best 0, last 0" that the watchdog read is the detailed-placement legalizer table of
   `macro_ff_pre_grt.tcl` (19 rows, 14397 -> 0 at iteration 83), which ends 6 minutes into the stage. It is the wrong metric.
   The router ran 4 congestion rounds (15 + 11 + 20 + 9 extra iterations, each round restarted after it removed the clock NDR
   from more nets) and the overflow did not fall: 16,943 -> 17,595 -> 17,735 -> 21,563 (MEASURED, section 1.2).
   Cause is design (placement), made long by flow: 74% of the overflow is inside macro `u_bound.u_t22`, where a 369-bit
   one-cycle pipe hop (`u_d3_u_t_2_2_t_out.r[0]` in the W strip to its next stage in the middle channel, MEASURED from the
   DB) is routed straight across the tile on rows with zero horizontal capacity; the rest is the collective-landing logic
   of i22 / i32 packed in the SW corner and at the foot of the middle channel. There is no end condition other than 30 iterations per round times an open number of rounds.
2. **This kit could not have reached sign-off even with a clean route.** MEASURED: setup WNS -1116.6 ps at CTS and unchanged
   after hold repair (gate -42); pre-GRT hold repair took 19,612 s (5.4 h), added 44,401 cells and left 1,864 cross-tap
   endpoints at -174.07 ps. The kit is also stale: place log `OT_NK_ANCHOR latches 6148 pipe_regs 0` (the pre-07:55 input
   chain; TYPE-QCCB-GEN expects about 5888). 12.6 h of the 14.7 h run were spent after CTS.
3. **clock_entry_clear (4) is by design and does no routing damage.** The 4 entries are `clk_c0..c3`, interior M7 die spine
   taps placed on top of each tile's `ck` pin. Route length is a via stack, no detour is possible. `clk_c*` nets: 0 overflow
   gcells at iteration 20 (4 at iteration 5 of the last round). One number needs a generator check: the M7 pin sits 0.50 um
   beside the `ck` pin and 0.35 um outside the M7 window opened in the LEF (section 1.4). Not proven harmful.
4. **clock_pin_geometry (M7, not M8) does no measured damage.** The `fclk_in_*` entries are vertical M7 pins 2.66 um inside
   the S edge; M8 is the horizontal layer with 51% die reserve on this type. Clock nets are 501 of 74,881 net entries in the
   overflow list (0.7%) and all of them are in the SW corner / channel foot clumps. The real clock damage there is that the
   router removed the NDR from 13 clock nets (taps t2, t6, t8, t11, t12, t13, t15, t19 and both fclk i22 roots) to make room.
   That is a consequence of the clump, not of the pin layer.
5. **cbf_q11 "place RC=0 but no 3_place.odb" is copy-back, not design.** Not examined further (section 4).

## 1. Measured

### 1.1 Timeline of the run (file times, PST)

| step | from - to | time | result |
|---|---|---|---|
| floorplan .. detailed place | 11-14 20:05 - 21:18 | 1.2 h | 351,794 instances, 4 macros, place smells: fanout_spread 1026 um, local_density 0.854 |
| CTS + tap balance | 21:18 - 22:09 | 0.9 h | tap mean insertion 188..335 ps (spread 147, target 250), 18 empty taps |
| pre-GRT FF hold | 22:09 - 03:39 | 5.4 h (19,612 s) | hold endpoints 14,742 -> 1,864, WNS -230.3 -> -174.1 ps, +44,401 cells (358,527 -> 402,928) |
| 5_1_grt: legalize + PG keepout | 03:39 - 03:45 | 350 s | 14,397 violations -> 0 at iteration 83 (the 19-row table) |
| 5_1_grt: pin access | 03:45 - 04:04 | 1,110 s | ok |
| 5_1_grt: global_route | 04:04 - 10:45 | 6.7 h | cancelled in round 4 iteration 9, never converged |

Round 1 was slow: its iteration 10 report is stamped 07:45 (3.7 h for 10 iterations), iteration 15 08:31.

### 1.2 Overflow by round (congestion-N.rpt, last writer of each file)

| report | round | gcells over | overflow | inside t22 interior | W strip x<86 | middle channel | zero-capacity gcells |
|---|---|---|---|---|---|---|---|
| congestion-10 | 1 | 12,561 | 16,943 | 11,949 | 2,091 | 2,100 | 9,390 |
| congestion-15 | 1 | 12,729 | 17,595 | 12,678 | 2,550 | 1,782 | 9,289 |
| congestion-20 | 3 | 12,222 | 17,735 | 13,075 | 2,371 | 1,571 | 9,172 |
| congestion-5 | 4 | 14,264 | 21,563 | 16,349 | 2,222 | 2,425 | 9,572 |

Macros t32, t23, t33 together: under 150 overflow in every report. Middle horizontal channel and N strip: 0.

### 1.3 Where and which nets (congestion-20)

- 14,976 distinct nets touch an overflowed gcell. About 7,400 are `u_bound.u_cland_bc_i22 / i32` nets (ring, dsel, sd_c)
  inside x 20-704, y 1-170; about 4,900 are `u_bound.u_cland_na_i22` nets inside x 62-142, y 0-106. Those are the two
  placement clumps of the density render: SW corner (x < 86, y < 250) and the foot of the middle channel (x 600-700, y < 170).
- Inside the t22 interior: 9,785 gcells over, of which 8,934 are horizontal with capacity 0 (usage 1 to 3). 572 nets; the
  long ones are about 630 repair-named nets (`net127xxx..net130xxx`) plus `u_cland_bc_i22/net*`, each crossing from the W
  face of t22 (x 87-98) to x 384-389 at y 830-1160, and a band along the bottom edge of t22 (y 72-100, 838 gcells).
- Macro view (qfd_tile_nk_a0c.lef): OBS is full on M1-M5, detailed on M6 (90,279 rects) and M7 (44,307); signal pins 2,056
  on the W face and 527 on the E face (M4), `ck` interior on M5. So over a tile the only horizontal resources are the M6
  gaps and M8, and M8 has 31,752 tracks of which the type owns 10,819 (free_frac 0.34, die reserve 16,229, PG 4,704).
  PG-AWARE-1 adds 3,300 temporary M6 obstructions on top. Rows with 0 horizontal capacity over the tile are the result.
- MEASURED from 4_cts.odb (`q3.out`): 369 two-pin nets have a BUFx16 driver at x 80-83 and a BUFx16 sink at x 546-548,
  y 937-997, a 463-um straight hop over t22. Traced back (2 to 4 `wire*` repeaters) every one starts at a register
  `u_bound.u_d3_u_t_2_2_t_out.r[0][*]` placed at x 74-77, y 900-1000 in the W strip; traced forward every one ends, through
  one INVx3/INVx4 at x 600-665, on the D pin of the next `u_d3_u_t_*_2_t_out.r[*][*]` register in the middle channel. So it
  is one bus: stage 0 of the t22 `t_out` delay pipe sits W of the tile and stage 1 sits E of it, about 580 um apart, one
  cycle, with the tile in between. 14 more crossers are `u_cland_na_i22` / `u_cland_bc_i22` BUFx16 nets going E to W.
- The M8 die-reserve pattern is 36 reserved / 18 free tracks (m8_grant die_runs), 2.88 um closed then 1.44 um open, so 5 of
  every 7.5 gcell rows over a tile have no horizontal track. The bus enters at its own y; vertical capacity over the tile is
  3 to 6 per gcell, so it cannot shift to the open rows at the entry. INFERENCE for the last clause (from the capacity /
  usage pairs `Vertical 6/7..6/10` at the W edge), the rest MEASURED.
- Soft area is not short: movable cell area 34,569 um2 in about 975,000 um2 of non-macro core (3.5%). The 0.854 density is
  local. `fclk_in_bc_i22` pin (138.9, 2.7) to its sink centroid (45.0, 141.5) is 232.7 um for 4,256 sinks; the same number
  for `fclk_in_bc_i32` is 46.9 um. The bc_i22 landing logic is not under its pins (S strip under t22, 69 um tall); it went
  to the corner.

### 1.4 Clock entries

- `clk_c0` pin M7 (315.872, 648.032), size 0.032 x 0.768. Tile t22 at (86.4, 69.132) R0, `ck` M5 rect 228.948-228.996 x
  578.64-579.12, absolute centre (315.372, 648.012). Offset +0.500 um in x. For the MY tile t23: pin 314.848, `ck` centre
  315.348, offset -0.500 um. Same 0.5 um in the wave advisories of cbf_q01 and cbf_q11.
- clock_entry_lef.json: OBS opened at M6 228.897-229.115 x 578.692-578.852 and M7 228.944-229.104 x 578.432-579.328
  (tile-relative). The pin at relative x 229.456-229.488 is 0.35 um outside the M7 window and the M6 jog to reach `ck`
  leaves the M6 window by 0.34 um. Whether detailed route passes there depends on the detailed M6/M7 OBS rects around it;
  GRT (0.57-um gcells) cannot show it. INFERENCE: possible DRT pin-access cost, not a GRT cause.
- CTS log: `OT_TAP_CORE u_bound.u_t22/ck tap clk_c0 pin -483 + internal 818 = effective 335 ps (target 250, window 20) WARN`
  on all 4 tiles. The kit's tap check uses the liberty maximum 818, not the signed mean 733.25 (733.25 - 483.25 = 250).
  TYPE-QCCB-GEN (queue 13600) already ruled the rows correct; the WARN text is the stale diagnostic. No row change.
- In this proof kit the preflight `clock_entry_clear` did not compute at all ("no plan contents (pass --plan-dir)").
- Hold left after repair: first rows of pregrt_ff_hold_open.tsv are `u_pc_nk_u_t_2_3_tap.q[*]` (launch clk_t67) ->
  `u_lk_nk_u_t_2_3_tap/q[*]` latch D (capture clk_t66) at -174 ps; class cross_tap 1,864, all other classes 0.

## 2. Fix / levers, with owner

| # | lever | numbers | owner |
|---|---|---|---|
| L1 | NOPROG-WATCHDOG metric for 5_1_grt: read the GRT round count (`GRT-0102 Start extra iteration 1/30` restarts) and the overflow total of the newest congestion-N.rpt, not the legalizer table. Flag when a later round's total is not below 0.9 x the first one. This is a watchdog reading fix, not a new stop inside the flow. | here: flagged at 08:31 (17,595 vs 16,943) instead of 10:45, 2.2 h and 37 GB earlier | KIT-OPS-5 |
| L2 | cb generator: give each collective landing (`u_cland_na_i*`, `u_cland_bc_i*`, `u_bin_*`) a placement region under its own pin span instead of free placement. For q11: bc_i22 pins start x 94.3, na_i22 x 4.8, nb_i22 x 184.4 on the S face; regions along the S strip (y 4-69, x 86-544 is 29,700 um2) and the W strip, density cap about 0.45. | clump today 0.854; cland nets are about 12,300 of the 14,976 overflow nets | GENBUG-IMPL (TYPE-QCCB-GEN for the cb specifics) |
| L3 | The t22 `t_out` delay pipe (`u_d3_u_t_2_2_t_out`, 369 bits) must not hop across the tile. Lay its stages around the tile through the middle horizontal channel (y 1227-1305, 77.8 um tall, 0 overflow today): r[0] at the top of the W strip (x < 86, y about 1200), one stage at the channel centre (x about 315, y about 1265), next stage at the middle vertical channel (x 545-690). Path about 1,100 um, so 3 stages at under 400 um each; if the pipe has fewer than 3 stages the latency row of t22 `t_out` grows by the difference (plan row, bind + LATCHECK). The `dly_spread.tcl` hook of S4q3b spreads stages on the straight line between the ends; it has to take a macro-avoiding path. Placement check for every cb kit: count of 2-pin nets longer than 300 um whose bbox lies over a macro, target 0. | 369 crossers; t22 interior carries 13,075 of 17,735 overflow | TYPE-QCCB-GEN / GENBUG-IMPL for the hook and the check; DIE-QC-103 for the stage count / latency row if it changes (S4q4) |
| L4 | Clock entry pin x: put `clk_cN` on the M7 track inside the opened window (tile-relative 228.944-229.104), or widen the OBS cut to the pin (229.456-229.488 plus one pitch). | 0.50 um offset on every cb type | GENBUG-IMPL |
| L5 | Do not spend hold repair on a kit that is far from setup: when CTS setup WNS is below -42 ps by more than, say, 500 ps, post it as a design result at CTS and skip pre-GRT hold. Advisory to COORD; it is a triage rule, owner rules on gates apply. | this run: -1116.6 ps known at 22:09, then 12.6 h | COORD decision, KIT-OPS-5 to implement |
| L6 | Preflight advisories: `clock_entry_clear` should pass an entry that lies on the tile's `ck` window (by-design spine tap) and fail only an entry over a macro with no opened window; `clock_pin_geometry` M7 for S/N-face fclk entries is the right layer here. Both lines are noise in every cb wave post today. | 4 + 101 lines per cb type | GENBUG-IMPL (kit_preflight.py) |

No plan row is proposed for the clock entries. L3 becomes an S4q4 row only if the t22 `t_out` pipe needs a stage added.
The same hop exists by symmetry wherever a tile's `t_out` leaves on the face away from its consumer; t23 (MY) shows 1
overflow gcell here, so in this type it is t22 only. Other cb types: not measured.

## 3. Stop list

- Do not relaunch or resume the proof kit `pg-aware-1/proof/cbn_c/cbn_q11__cl5cc92dfe` in any form: stale input chain
  (pipe_regs 0), setup -1116.6 ps, GRT not converging. Its evidence is in this file; the kit can go with the next cleanup.
- Do not retry GRT on it with more iterations, a larger congestion adjustment, or with PG track truth off as a "fix": the
  overflow rows have capacity 0, not capacity short by a few tracks.
- Any cb kit whose place log shows `OT_NK_ANCHOR ... pipe_regs 0` is the pre-07:55 kit: regenerate, do not resume.
- The S4Q3B wave kits of cbn_q11 (launched 10:56) may run; they are the first test of whether the clump and the tile
  crossing survive the new chain. Read their place smells (local_density, fanout_spread) before they enter hold repair.
- cbf_q11 INFRA copy-back: relaunch is fine, it is not a design failure.

## 4. Not checked

- Which tile-face pins `u_d3_u_t_2_2_t_out` belongs to and its stage count in the bound RTL: not read (the DB shows r[0]
  and one further stage).
- Whether S4Q3B `dly_spread` (warn mode) already moves this pipe: not read; the kit here predates it.
- epyc8 /srv/opentallas-scratch2 is at 99% (82-91 GB free) at 11:35; seen in passing, not acted on.
- Why round 1 needed 3.7 h for 10 iterations (FastRoute on 6.48 M gcells per layer with 773,328 blockages) was not profiled.
- The S4Q3B wave kits of cbn_q11 / cbf_q11: not read; no statement here about the current plan's placement.
- The cbf_q11 copy-back failure (intel1 attempt_12): not read.
- Detailed-route legality of the clk_cN entry (L4): no DRT run exists on this kit.
- The 1,864 cross-tap hold endpoints: only the first rows of the table were read; tap t66 / t67 insertions not compared.
- The -1116.6 ps setup path was not traced (TYPE-QCCB-GEN owns the -861 ps item).
