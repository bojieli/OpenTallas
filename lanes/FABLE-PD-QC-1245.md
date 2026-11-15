# FABLE-PD-QC-1245: structural review of QC plan event S4q5 (hc band area)

2026-11-15 13:30 PST, FABLE-PD-QC-1245. Read-only on plans and kits. One job launched: a G0 of S4q5 with the treeA tools
into my own directory (section 5). Nothing stopped or changed.
Subject: epyc9:/srv/opentallas-scratch2/claude/die-qc-103/treeA/physical/die_plan/qwen_compute/plan_of_record/
zz_s29_qc103_s4q5.json (+ .cland_bin_sites / .clock_merge / .kit_pricing), built by die-qc-103/hc_area.py from
zz_s29_qc103_s4q3c.json. Scripts and outputs: epyc9:/srv/opentallas-scratch2/claude/fable-pd-qc-1245/ (a1..a5.py, a2.out, a3.out).
MEASURED = read or computed today from those files / the named kit. INFERENCE is marked.

## 0. Verdict

**S4q5 as built must not adopt, and it does not fix the one hc1 congestion that was measured.** Two independent reasons:

1. The transform changed 115 numbers (18 outlines, 96 origins, the die height) and nothing else. Every coordinate that
   depends on the hc height or on the y of the 96 moved partitions is stale: hc N-face clock/landing pins, face-reach
   stations, clock taps, the die start tree (1,294 nodes), the feed / CA table, the bump field, one channel rect (F2, F3).
2. The GRT failure of slw_hc1 is a pin-face landing hotspot at the S face, 100 % of the overflow in the bottom 40 um of a
   717-um block at 12 % area utilization. A taller block adds area at the N end, 700 um from the hotspot (F1).

Recommended: fix the `u_cland_b_hw_i` strip first (budget keys, no geometry, rides the rows delta), pilot hc1/hc0 at the
current height, and build S4q5 only if the pilot still needs area; then build it as a regenerate, last in the stack (F8).

## 1. Ranked findings

| # | finding | mark | owner |
|---|---|---|---|
| F1 | hc1 congestion is not density-driven. Kit epyc10 `.../s29q103S3R/items/slw_hc1__cl68f9248e__cl144ee7b3/attempt_3` (the GRT kit of the lever-5 evidence): 421,650 instances, `Design area 52940 um^2 12% utilization`, GRT total usage 12.83 %. Final congestion.rpt: 6,147 gcells, overflow 40,527 = V 35,007 + H 5,520; **all of it at y < 40 um**, x 100-380 (the block is 613 x 717). 89 % of the net entries are `u_bound.u_cland_b_hw_i` (162,235 of about 182,000), next `b_hw_i` pins 12,185. That is the collective landing of the 1,573-bit `b_hw_i` bus packed against its S-face pin window (x 4.3-409.3). Place smells agree: the 20 local_density offenders (0.75-0.79) are at y 9-19, x 129-369. Router dropped the clock NDR on 20 nets there (clk_t1..t16, fclk_in_b_hw_i). | MEASURED | DIE-QC-103 (budget keys), QC-CB-GEN-1115 (cland region rule, same class as cbn_q11 L2) |
| F1b | "0.78-0.86 cells/um2" is a count, not a utilization. hc1 and hc0 (sle_hc0 cl05696ed1 S4Q2 a5: 405,541 instances, `51577 um^2 12%`) are both at 12 % cell area. Growing 717 -> 1028 takes them to 8.5 %. No global routing resource is short (M6-M8 usage 1.5-4.5 %). | MEASURED | DIE-QC-103, COORD (rule C reading) |
| F1c | hc0 is a different picture: its 20 density offenders (0.84) are spread over y 109-699, x 29-616, not at a face. No GRT report exists for an hc0 kit on epyc10, so its mechanism is not measured. Clumps of 0.84 inside a 12 % block are placement clumps (stations / landing rings / ft groups), which more height does not dissolve either. | MEASURED location, INFERENCE cause | DIE-QC-103 |
| F2 | hc types keep the old N face. In the 18 hc type records: 62 N-face landing-contract pins at y 715.70 (`fclk_in_rsf_i`, `fclk_in_rsn_i`, `cland_fstart_in_*`, `fclk_in_cland_dn_0`), 12 edge-clock taps, 19 `internal_stations.to_um` at y 717.12, 8 writer-start stages, collector tree outs/relays, all 311 um below the new face at 1028.16. The cb row above was moved, so each of the 48 + 48 hc -> cb and 36 cb -> hc landing clock / start edges (`max_hop_um 405`) now has its hc pin 311 um inside the block. Clock taps stay `glue_00` y 180.4 / `glue_01` y 536.7 (quarter points of 717): the top of the block is 492 um from the nearest tap against `tap_radius_um 200`. `reset.tap_um` and count straps stay at y 360.9. sink_bins and reset_tree_anchor are sha-pinned to the old shape. | MEASURED | DIE-QC-103 |
| F3 | Die-level clock data did not move with the 96 partitions. `clock.landing_network.start_tree.provider`: 1,294 of 3,388 nodes and 1,378 of 3,700 edges have absolute rects at y >= 15465.6 and are now 311.04 um below their partitions (the lowest ones lie inside the hc band); 12 edges band -> above and 34 below -> band change length. `regions_s29.json` carries `plan_sha256_16 ce6958cf1db5b7cd` of the old plan. `feed_s29.json`: 12 feed edges `sl_*_hc0 -> c_*_tn_00` cross the band top, so all 96 upper regions arrive later. `ca_s29.json` (K / DEPTH on 2,525 crossings, 290 ps/mm) was not recomputed. | MEASURED | DIE-QC-103, CLKSITE-QC-SNAP-1115 (clock sites of the 18 hc types and the moved start-tree nodes) |
| F4 | The die-worst CA margin is exactly on the band top: `sl_*_hc3__cwn3__0` (hc3 -> c_*_tn_10), 7 crossings at m_lo 107.1 ps, depth 8, phys 5. 311 um x 290 ps/mm = 90 ps on the feed path to the cb rows; the relative shift on these crossings is about 45 ps if arrival is priced centre to centre (hc +155 um, cb +311 um). m_lo becomes about 62 or 152 ps depending on sign. | margin MEASURED, shift INFERENCE | DIE-QC-103 (rerun region_form, read `worst_margin_lo_ps`) |
| F5 | Lanes that gain cycles (prediction for LATCHECK). Face-reach rows price xh.n_d -> N face: hc0 1352 um, hc1 1273, hc2 1209, 3 FIRM stations each. Plus 311: hc0 1663 / 4 hops = 416 um > 405, so **cw_n0 needs a 4th station: +1 cycle on the 12 `sl_*_hc0__cwn0` lanes**. hc1 1584 / 4 = 396 um (9 um under the limit, stations must be re-spread; today's `regs_um` stop at y 559, leaving a 469-um last hop). hc2 1520 / 4 = 380, no change. hc3 has no face-reach row (source assumed near N). ft `rsn` / `rsf` through hc0 (N -> E, 5 / 4 stations): about 1,410 / 6 = 235 um and 1,030 / 5 = 206 um after re-spread, +0. All hc <-> st/ctl lanes (S face) and hc <-> hc lanes (E/W windows y 4-278): unchanged, +0. | row lengths MEASURED, hop arithmetic and ft lengths INFERENCE | DIE-QC-103 |
| F5b | The +1 lands on cw_n0 only, while cw_n1..3 into the same cb row stay. Whether K absorbs it or the bc_i group needs pads is for LATCHECK after `gen.py latency --inplace`; without that step the bind fails on the stale table (QC-SC-ROWS lesson, 101 x KIT_ISTATION_LATENCY). | INFERENCE | DIE-QC-103 |
| F6 | The G0 "running for S4q5 and S4q3c" did not run. Both `g0_s4q5` and `g0_s4q3c` end in 1 schema error `$.budgets: unknown key 'r_dly_spread'`, 0 checks, `None types`: `g0_run7.sh` runs check.py of **tree7**, whose schema.py does not know the key (treeA does). The log tail prints a literal `rc=$?`. | MEASURED | DIE-QC-103 |
| F7 | Abutment and tiling are intact. 377 partitions, 0 overlaps, none outside the die; band 14748.48-15776.64, cb rows from 15776.64 to 25954.56. No port connects a moved partition to an unmoved one outside the band (no A <-> L port), so serdes / coll / west strip are untouched. E/W/S pin windows of hc types are all at y < 280 um or on x, so hc <-> hc, hc <-> st/ctl and (in x) hc <-> cb data pins still face each other. | MEASURED | none |
| F7b | PG / bumps: 311.04 = 36 x 8.64, the M8/M9 die grid stays in phase over the moved tiles. 311.04 mod 75 = 11.04 um: the 75-um bump lattice does not. `die.pg.bumps.fields[a0_p75].rects_um[1]` is still [1495.24, 15388.36, 31216.32, 25643.52]; it must become y 15699.40-25954.56 and the lattice must be anchored to the field rect, not the die origin, or every A0 tile above the band sees its bumps 11.04 um off the QC-PG-4 solve. The top 311 um of the die is outside any p75 field today. `die.channels[2]` still ends at y 25643.52. `clock.spine.root_um` y 12821.76 is no longer the die centre (12977.28): keep it, it sits in unmoved ground. | rects and arithmetic MEASURED, lattice anchor INFERENCE | DIE-QC-103 |

## 2. What actually fixes hc1 (F1), with numbers

- The landing of `b_hw_i` needs depth, not block height. 1,573 bits enter on 405 um of S face (3.9 bits/um) and their
  ring / dsel logic sits in the first 20-40 um: V overflow 19,282 at y 0-20 and 15,725 at y 20-40.
- The plan has the knob: `budgets.cland_strip_rows_types` gives `sle_hc1` / `slw_hc1` 4, plus `cland_strip_density` /
  `cland_strip_density_types`. Give the b_hw_i landing a strip about 100-120 um deep under its own pin span with a density
  cap about 0.45 (same form as FABLE-PD-QC-1115 L2 for the cb landings). 12 % utilization leaves 88 % of the block free.
- Same check for hc0 / hc2 / hc3 (`b_hw_i` 1,573-1,574 bits on 272-495 um of S face).
- Cost: budget keys only, no outline, no die clock regen, only the hc types re-kit. Pilot: one slw_hc1 and one sle_hc0 to
  5_1_grt at the current 717 height; pass = GRT overflow 0 without NDR drops on clk_t*.
- If the pilot passes, S4q5 is not needed for routing. If the owner target of 0.6 cells/um2 stands as a rule regardless,
  S4q5 goes ahead, but as section 3.

## 3. If S4q5 is built: do it as a regenerate

After the outline / origin / die edits, in one event:
1. hc types: regenerate landing contract and edge-clock pins on the new N face, writer/reader start stages, collector
   tree, face-reach stations (4 for hc0, 3 re-spread for hc1/hc2), ft station sites, taps (3 taps at 1028 um:
   y 171 / 514 / 857, or tap_mode density re-run), reset tap, straps, sink_bins, reset_tree_anchor.
2. Die: shift every absolute start-tree / relay rect at y >= 15465.6 by +311.04 and re-solve the 46 edges touching the
   band; rerun region_form (regions sha, feed arrivals, ca table); move the upper p75 bump field and channel 3.
3. `gen.py latency --inplace`, then G0 with treeA, bind, LATCHECK.
4. Kits invalidated: the 18 hc types only. The 96 moved cb partitions keep their type records byte-equal (MEASURED: the
   diff touches no cb type), so no cb re-kit.

## 4. Stacking and order (one rebind per class, no serial geometry binds)

1. **Rows delta now, one bind:** S4q4c (fw / st_b / su_c / fe rows, QC-FWST) + QC-SC-ROWS sc rows + x_ctl_i row + fe gap
   rows (x_fw_p1_o, sle_fe_v2 st_wi) + reset consumer_localization + the hc cland strip keys of section 2, and the S4q3d
   st_a_v1 master renames if CORE-ROWS has them by then (do not wait for them). All are additive rows / budget keys on
   disjoint types, no outline change. One `gen.py latency --inplace`, one bind + LATCHECK, one G0. DIE-QC-103 already has
   S4Q3BSAB in bind (sc A+B on S4q3b); rebase that on S4q4c rather than adopting it and S4q4c one after the other.
   Open item to read first: `g0_s4q4c.log` says G0 FAIL 2 errors, 460 warnings (19:35 UTC); not examined here.
2. **hc1 / hc0 pilot** on that delta (section 2), in parallel with step 3 preparation.
3. **S4q5 last, alone,** only if step 2 says area is still needed, built per section 3 on top of the rows delta. It is the
   only geometry event; putting it last means the die clock / start tree / CA regen happens once.
Reason for rows before geometry: rows change no coordinate that S4q5 regenerates, while S4q5 first would force the
start-tree and CA regen, then a second latency pass when the rows arrive.

## 5. G0 of S4q5 with the right tools

Launched 13:10 PST through ot-run (4 GB, 1 thread, epyc9): `treeA/tools/die_plan/check.py ... zz_s29_qc103_s4q5.json
--out /srv/opentallas-scratch2/claude/fable-pd-qc-1245/g0_s4q5A`, log `g0_s4q5A.log` beside it, timeout 90 min. Still
running at 13:30 (the sc G0 on the same host took over 30 min). DIE-QC-103 reads `g0_s4q5A/g0_report.json` when it lands;
I expect reach / landing errors from F2 and F3, not a clean pass. Nobody else waits on it.

## 6. Stop list

- Do not adopt, bind or post READY for `zz_s29_qc103_s4q5.json` as built.
- Do not quote g0_s4q5 / g0_s4q3c (tree7) as a G0 result; do not use g0_run7.sh for plans carrying `r_dly_spread`.
- Do not lift the WAVE-HOLDS keys `sl?_hc0*` / `sl?_hc1*` on an S4q5 adoption alone: a taller hc1 with the same b_hw_i
  landing has the same S-face overflow. Lift on the cland strip change (pilot GRT clean) or on a regenerated S4q5 with it.
- Do not relaunch hc0 / hc1 kits unchanged (stands from FABLE-CLOSURE), and do not retry slw_hc1 with more GRT
  iterations or a higher congestion adjustment: 20 clock nets already lost their NDR in that strip.
- Do not adopt S4q4c, the sc rows and S4q3d as three serial binds; one rows delta.
- Do not shift the bump field or start-tree rects by hand without rerunning region_form and the QC-PG lattice check.

## 7. Not checked

- hc0 routing: no GRT report for any hc0 kit was found on epyc10; other hosts not searched. Only one hc1 kit (S3R plan,
  before the S4 rows) was mapped; whether `delta_hc1_strip_1111` rows were active in it was not read.
- How bind / gen derive hc N-face pins: if a generator rebuilds landing_contract and internal_stations from the outline
  at bind time, part of F2 heals itself; the plan record as stored does not. The treeA G0 (section 5) will show which.
- The sign of the CA margin shift (F4) and the L <-> H crossings' margins after hc arrival moves 45 ps.
- hc3 cw_n3 source position (no face-reach row), and the exact ft in-face x of rsn / rsf (lengths in F5 are from pin x).
- Whether the p75 bump lattice is anchored to the field rect or the die origin (F7b).
- The 2 G0 errors of S4q4c and the state of the S4Q3BSAB bind (latcheck log at 20:52 UTC says the bind had not finished
  emitting).
- No DB was opened; all kit evidence is from logs, congestion reports and smells.json.

## 8. Update 13:50 PST: treeA G0 of S4q5 finished (MEASURED)

`epyc9:/srv/opentallas-scratch2/claude/fable-pd-qc-1245/g0_s4q5A/g0_report.json`: G0 FAIL, 135 errors, 474 warnings.
- 133 x `clock_landings` (new with S4q5, confirms F3): 36 x `cland_mon_{ready,fault,clk}__c_*_tn_00: actual endpoint hop
  exceeds 405` (E slices 414.1-416.1 um, W slices 478.9-487.6 um; the hc0 -> cb tn_00 monitor edges across the band top),
  the rest `start tree: boundary pin geometry mismatch`.
- 2 x `faces` (`sl_W5_fw.W` / `coll_f4.E`: 72 pins in the 10-um window at 11749.70, 7.20/um > 6): baseline, identical to
  the 2 errors of g0_s4q4c, not caused by S4q5. This also answers the open item in section 4: S4q4c G0 has only these 2.
- G0 does NOT flag the stale hc N-face landing pins, face-reach stations or taps of F2 (0 findings on them), nor the
  bump field / channel rect of F7b. A clean G0 after fixing the start tree would still leave F2 and F7b open: check them
  by the listed coordinates, not by G0.
- New warnings against S4q4c: geometry +10, complete +4 (not read line by line).
