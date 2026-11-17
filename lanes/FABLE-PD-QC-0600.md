# FABLE-PD-QC-0600: QC cb family (pilot cbn_q01) review, 2026-11-17 06:00 PST

Scope: technical PD only. Build read: attempt_xj (83205ba2de), post-CTS, placement parasitics, kit SDC and RC.
Probes ran through ot-run on epyc8 (units oth-ubuntu-3719083, -3741815, -3828353); builds were read-only.
Evidence: `epyc8:/srv/opentallas-scratch2/claude/fable-pd-qc-0600/` (`a_*.log` placement per stage, `a_hh_*.log` the
same for attempt_hh, `b_TT.log` / `b_FF.log` STA, `c.log` fanout).

## Verdict

1. tap_d[431] / [442] are not a new failure. The trunk buffers of 42 `b_d` registers never joined the strip, and the
   32-round change cannot make them join. Fix is one rule in the join test (section 1).
2. The station is not too long for one cycle. The same structure with a joined trunk has +325 ps or more. No extra
   cycle, no station or tap re-site.
3. `latch_except` is right for bit `tap[0]` only. The merged key is port-wide, and port-wide it fails hold on
   1,744 of 1,776 timed tap pins (TT; 1,702 at FF). **Do not launch the 18-type wave with `latch_except {qfd_tile_nk_a0c: [tap]}`.**

## 1. Root cause of tap_d[431] / [442] and the 245 ps first hop

Measured positions (um), identical in 3_3 GPL, 3_4, 3_5 and 4_1:

| cell | GPL (3_3) | after XSTN_SITE (3_4 .. 4_1) |
|---|---|---|
| `b_d[463]` (head) | 39.9, 1274.5 | 76.7, 1783.8 (moved into the strip) |
| `place164210` | 41.2, 1386.6 | 41.2, 1386.6 (never moved) |
| `place164209` | 39.3, 1663.5 | 39.3, 1663.5 (never moved) |
| `place164208` (2 loads) | 38.8, 1857.6 | 38.8, 1857.6 (never moved) |
| AND4 `_79119_` | 51.1, 1954.7 | 74.3, 1920.1 (moved) |

- At GPL the head sat south of tile t03 (y 1274) and the three `place*` buffers were a monotone relay north to the tap
  cone (y 1955). XSTN_SITE moved the head 510 um north, past its own first two relay buffers. The path now runs
  400 um south to `place164210` and back: 1,003 um built for 139 um direct. That first leg (b_d QN to `place164210`,
  three `wire*` buffers added by repair_design) is the 245 ps.
- Why the trunk did not join: `place164208` drives the AND4 and a second branch,
  `place164207` -> INV `_79043_` -> `u_ist_bc_o03_0/q[463]` (FIRM istation flop, y 2101). The join test looks at
  direct loads only. `place164207` fails it (its load is the INV, not a member, not a flop), the INV is never
  visited (it shares no net with a member), so `place164208` fails, and with it `place164209` and `place164210`.
  This is a deadlock, not a round limit.
- Why three ends passed: on `b_d[481]` the INV (`_79150_`) hangs directly on the trunk net beside the AND4, so it is
  visited, joins (its load is a flop), and the trunk follows. One extra buffer in front of the INV is the whole
  difference.
- Size of the class: 42 heads (`b_d[444..506]` of u_x_0_3), 81 stretched load paths (built > 2x direct and > 100 um
  over), all with this two-branch shape. attempt_hh had 256. Of these 42 heads, 4 are negative and 27 are below
  +100 ps; every other `b_d` head of the station is at +325 or more (`b_d[380..443]`: min +342, mean +437).
- The same trunk also makes `u_ist_bc_o03_0/q[463]` -14.0, `cap[3]` -19.5, `tap_d[436]` -9.9, `tap_d[437]` -8.5.
- The -47.5 -> -70.0 change is a reshuffle, not a new mechanism: launch clock +4.7, QN +4.4 (load 9.1 -> 11.6 fF),
  trunk +6.3 (head 17 um further east), gate cone +5.6, capture -1.4. Do not bisect it.
- QC-TYPES-R3 05:39 / 05:43 is wrong on two points: the chain is not fanout 1 (`place164208` has 2 loads), and
  the buffers were not placed by y rank (they are at their GPL coordinates to 0.1 um in every stage).

## 2. Is b_d -> buffer chain -> tap_d too long for one cycle? No.

| path (TT, post-CTS) | data path | slack |
|---|---|---|
| `b_d[481]` -> 4 buffers -> AND4 / AO21 / AOI221 -> `tap_d[465]` (joined) | 411 ps | +353.9 |
| `b_d[463]` -> 9 buffers -> same gates -> `tap_d[431]` (stranded) | 837 ps | -70.0 |

- Buffers alone: 161 ps joined, 547 ps stranded. Gates are the same (192 to 198 ps).
- Geometry after siting: strip 60 x 250 um (x 19..78, y 1766..2016), tap row y 1866..1966, istation y 2100. Worst
  hop inside the strip is about 310 um; `b_d` to the istation is 300 to 370 um direct. At the measured 67 ps per
  110 um wire stage that is at most 225 ps of buffers.
- Expected after the fix: `tap_d[431]` / `[442]` about +300 (547 -> about 160 ps of buffers), istation branch about
  +390.
- Launch `b_d` is on clk_t105 (264 ps), capture `tap_d` on clk_t108 (215 to 221 ps): 45 ps against setup. Not
  needed for the gate; optional.

## 3. latch_except, read at both corners

In-memory ECO on the 4_1_cts database: each core `tap` pin moved from the latch Q net to the latch D net.

| | TT setup | TT hold | FF setup | FF hold |
|---|---|---|---|---|
| `tap[0]`, with latch (4 pins) | -117.9 .. -65.9 | +398.7 .. +448.7 | -52.2 .. -1.8 | +395.7 .. +444.4 |
| `tap[0]`, no latch | +294.7 .. +338.3 | t02 +11.1, t03 +6.8, t12 -13.8, t13 +28.3 | +361.6 .. +406.3 | t02 +8.6, t03 +7.7, t12 -14.0, t13 +29.7 |
| `tap[1..507]`, with latch | none negative, median +368 | min +286.1 | none negative, median +350 | min +323.4 |
| `tap[1..507]`, no latch | +703 or more | 1,743 of 1,772 negative, min -130.7 | +719 or more | 1,701 negative, min -87.9 |

- `tap[0]` (the `go` bit) has its own core arc: library setup 216.8 / hold 641.8 (TT), against 672.1 / 709.7 for the
  other bits. Its window is 261 to 624 ps after the edge; the other bits' window is 329 to 1,079 ps and needs the
  latch.
- Confirmed for `tap[0]`, refuted for the port. r541 matches the port name only (`port not in set(...)`), so the
  planned row drops all 508 latches per tile.
- `tap[0]` without the latch is marginal on hold (t12 -14 at both corners). Pad the 4 nets by 120 to 170 ps TT
  (3 HB4, lever 3's number): setup +125 or more, hold +106 or more at TT.
- 256 tap pins are constants (`xo` low halves) and are untimed after the ECO. The n_a / n_b / rst_n latch pins have
  no negative setup or hold at either corner.

## 4. Ranked fixes

1. **Join test through buffers** (`tools/die_plan/core_input_chain.tcl`, CB-XSTN join loop): a cell joins when every
   terminal load reached through buffers / inverters (`nc_load_insts`) is a member or a flop; the pass-through cells
   join with it. Clears 81 stretched paths on 42 heads; all six setup ends of this class go positive.
2. **Bit-level `latch_except`** (`tap[0]` only) plus the 120 to 170 ps pad on those 4 nets (`hold_pad_hb4.tcl`).
   Needed before the 18-type wave.
3. **Make the check see this class.** `OT_NK_HEADHOP_RESITE ... path_over_3x_direct_after 0` printed 0 while 81
   stretched paths existed. Count every `b_d`-rooted buffer tree to all its terminal loads and stop at 3_4, before
   repair_design, when the count is not 0.
4. R3's prototype (epyc2 `qc-types-r/xj_proto`, re-space 1-load chains): let it finish as a cross-check. It stops at
   the 2-load `place164208`, which is already near the cone, so it should close these ends; fix 1 is still the one
   to merge, because it also moves the istation branch.
5. Optional: `b_d` and `tap_d` of one station on the same clock tap (+45 ps).

With 1 and 2 the pilot has no negative post-CTS TT setup end: all ten violated ends today are in these two classes.
Routed setup is still unread (R3's `xj_route` is running).

## 5. Stop list

1. A +1 cycle station, a station or tap re-site, or a core reshape for `b_d` -> `tap_d`.
2. More join rounds (32 -> more).
3. The wave with port-wide `latch_except [tap]`.
4. Setup repair, sizing, or waiting for the routed read on these ends: the wire is 1,000 um for 140.
5. Moving the `b_d` head next to the AND4 (R3 05:39): the head is already 139 um from it.
6. Bisecting the -47.5 -> -70 change.
