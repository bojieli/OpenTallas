# FABLE-PD-DRT-1350: DRT-0255 beyond the M7-pin-under-strap case -- PD review (2026-11-15)

Scope: read-only. Route logs of epyc7/8/9 (the hosts FABLE-CLOSURE-1310 could not read), 4 kept `5_1_grt.odb` opened
with OpenROAD via ot-run (epyc9, epyc8; script + logs in `/srv/opentallas-scratch2/claude/fable-pd-drt-1350/{t37,sc,fe,hroot}/win.{tcl,log}`).
No kit, plan or job was touched.

## 0 Answer

1. One mechanism covers the "interior boundary net", "ring-band net" and KV kv3_hroot classes (14 of the 16 probed kits by
   class): the failing net is a TRUNK WHOSE GRT GUIDE IS ON M6 INSIDE THE GCELL ROW COVERED BY THE M6 PG PAIR. 4 of 4
   databases opened show it (MEASURED, section 1). The row has 0 or 1 DRT-legal M6 tracks, so detail route moves the
   trunk to M4 under the pair, M8 over it, or the one M6 track beside it; the failure is always in the 1st optimization
   iteration, at the cut of such a wire by the new box edge.
2. FABLE-CLOSURE-1310's position statistic is CONFIRMED on epyc7/8/9 (MEASURED). Its cause reading is corrected in two
   points: (a) the blocking shape is the M6 PG pair itself lying on the guide row, not the M8 band (in S81 t37 the M8
   obstruction row is 1.5 um away from the failing track); (b) the points printed in the log are the REACHED source side,
   not the unreachable terminal.
3. `OT_PG_TRACK_TRUTH=1` does not prevent it: 3 of the 4 databases had it on, and GRT still laid 56-70 um M6 guides in
   rows where the hook had obstructed every M6 track (MEASURED). `OT_PG_CELL_KEEPOUT` and `OT_PG_DIE_PHASE` do not act
   on this class at all (INFERENCE from what they change: cells under crossings, M7 strap phase).
4. NOT MEASURED: the exact hard edge that isolates the unreachable terminal inside the worker. No routed DB or maze
   dump exists for these kits. Section 4 gives the one run that measures it. The fix in section 3 does not depend on it:
   it removes the M6-in-PG-row guide, which is the measured common factor.

## 1 Measured

### 1.1 Route logs, epyc7/8/9 (46 logs with DRT-0255, 39 kits, script d255c.py)

- 223 printed source points, ALL in the 1st optimization iteration (box origin = 5 mod 7 gcells of 0.57 um on every one).
- 76 distinct box-edge points. By layer against the PG template (M6 pair 0.288/0.096/0.288 at core + 1.968, pitch 4.32;
  chance level for the pair row is 18 %):

| layer | n | position |
|---|---|---|
| M4 | 21 | 19 in the M6 pair row (under the straps) |
| M8 | 25 | 21 in the M6 pair row (over the straps) |
| M6 | 15 | 13 on the first M6 track below (-0.272 / -0.24 from the pair centre line) or above (+0.624 / +0.656) the pair; 0 inside |
| M5 | 5 | no relation to the M5 pair |
| M7 | 10 | 3 at the M5 pair, 7 elsewhere |

- By die: S81 36 points, QC 26, HEAD 8, KV 6. Same picture on all four.
- All M4/M6/M8 points are ON their layer's track (M4 0.024 + 0.048 k, M6 0.032 + 0.064 k, M8 0.04 + 0.08 k): not an
  off-grid wire end.
- kv3_hroot attempt_13 prints the whole reached component: cell pin M1 (917.757, 162.117) -> M2 -> M3 -> M4 along
  y 162.312 (under the VDD strap 162.048-162.336) west to the box edge x 916.56. So the maze did connect the cell pin
  to one box-edge wire end and then could not reach the next terminal (name empty = another box-edge wire end).
- Tech (all kits, from the DB): M2-M7 are RIGHTWAYONGRIDONLY + RECTONLY, M8/M9 are not. M8 obstructions only
  (285 to 15,095 per kit, from `m8_grant.py` in `pdn.tcl`); 0 obstructions on M1-M7, 0 placement blockages, the failing
  nets have no NDR.

### 1.2 Databases (failing net, its GRT guide, the fixed shapes in the failing box)

| kit (die, track truth) | net | M6 guide (gcell row y, length) | M6 PG pair on that row | legal M6 tracks in the row | where the wire went |
|---|---|---|---|---|---|
| slice_station__t37 (S81, off) | u_ft_ft0_o_5/net176850, BUFx6f -> DFF D, 2 pins | 135.660-136.230, x 5.13-103.17 (98 um) | VSS 135.744-136.032, VDD 136.128-136.416, full width | 0 | M4 y 136.152 (x 18.81, 26.79, 50.73), M8 y 136.200 (x 42.75); 4 failing boxes in a row |
| slw_sc_v1 cl4590432d (QC, on) | u_ft_x_fe_stm_p1_o_2/net277917, 2 pins | 1531.020-1531.590, x 11.40-67.83 (56 um) | VSS 1531.104-1531.392, VDD 1531.488-1531.776 | 1 (1531.040, 0.048 from VSS at min spacing 0.032) | M4 y 1531.512, M7 x 23.968 |
| sle_fe_v1 cl8210183c (QC, on) | u_cland_l9_eo_l9_wi_i/u_ring.dch[3].u_dsel/_028_, 2 pins | 597.930-598.500, x 534.66-604.77 (70 um) | VSS 597.984-598.272, VDD 598.368-598.656 | 0 | M8 y 598.360 (x 553.47), M4 y 598.392 (x 561.45) |
| kv3_hroot attempt_13 (KV, on) | u_cland_ft10_i/u_ring.g_tag.s_tag[2][0], 3 pins | 161.880-162.450, x 909.72-918.27 (3 pieces) | VSS 161.664-161.952, VDD 162.048-162.336 | 1 (162.400) | M4 y 162.312 |

- In every case the pins of the net sit in the same gcell row as the M6 pair (cells in the std rows under the pair), and
  GRT draws the straight M6 guide in that row.
- kv3_hroot only: the sink OA21x2 (917.730-918.108, 162.000-162.270) is also under the M5 pair (917.844-917.964,
  918.036-918.156) x M6 VDD crossing. The other three have no cell of the net in the box.
- M8 obstructions against the failing row: t37 137.940-138.540 (not on the row; M8 track 136.200 is free);
  QC sc 1532.26-1534.94 (34 single-track obstructions above the row; the 20 free M8 tracks lie over the pair row);
  hroot one obstructed M8 track at 162.26-162.30 inside the row. So the M8 band is not the common factor; in QC the M8
  type tracks were simply planned on top of the M6 pair.
- Track truth on sle_fe_v1: `OT_PG_TRACK_TRUTH add 1270 temporary GRT obstructions M5=284/1136 M6=844/5064 M7=142/852`
  = 6 M6 tracks per stripe, 12 per pair = every M6 track of the pair row. The 70-um M6 guide is still in that row.
- t37 after iteration 0: 64,562 violations (route log). slw_su_l1: 3,548 M8 shorts (FABLE-CLOSURE, REPORTED).

## 2 Mechanisms, counts, root cause

| # | mechanism | count | root cause in the flow | status |
|---|---|---|---|---|
| A | M6 guide in the M6 PG pair row (trunk forced to M4 / M8 / the edge M6 track) | 4 of 4 DBs opened; by position 53 of 61 M4/M6/M8 wire ends on epyc7/8/9; classes "ring-band" 6 + "interior boundary" 7 + KV hroot of the 13:10 probe | (1) global route: FastRoute keeps routing M6 through a gcell row whose M6 tracks are all blocked (track truth on) or counted free (off); the guide follows the pin row. (2) placement: landing-ring (`u_cland_*`, `u_ring.dch*.u_dsel`) and ft-station (`u_ft_*`) cells are placed in rows under the M6 pair like any other row, and their hops are 50-100 um straight runs in one row. (3) PDN template `gen.py` phys: pair 0.672 wide every 4.32 um = 18 % of rows have no M6 | MEASURED geometry; the DRT-internal hard edge is INFERENCE |
| B | M7 face pin under the type's own M7 strap | 2 of 16 (hd_spn b_i[67], slice_station__t49 ft2_i[324]) | schema.py:2932 band phase (FABLE-PD-HEAD-1115) | MEASURED there; fix in flight (die phase / pin_band_origins) |
| C | cell pin not reachable (M1 points inside the box) | 11 of 192 blocks (FABLE-CLOSURE), on epyc7/8/9: slice_station__t6 ft2_i[448], sle_stm_v3 u_bin_x_fw_p1_i/net321970, kv3_hroot sink under M5 x M6 | cell under a PG crossing / dense pin row | not traced here; small |
| D | clock net (slw_stm_v2 clknet_3_0_0_clk_t54) | 1 | not opened | UNMEASURED |

Why A ends in DRT-0255 and not only in violations (INFERENCE): M2-M7 allow a right-way wire only on the layer's own
track and only as rectangles, so inside the pair row a net has no M6 at all and M5/M7 can cross the row but not stop
in it; iteration 0 (64,562 violations on t37) leaves the trunk as short M4 and M8 pieces joined by via stacks through
the strap row, and when the 1st iteration cuts it at a new box edge one of the cut ends has no legal continuation in
its box. Which edge is missing is not measured.

## 3 Ranked structural fixes (generator / flow level, all dies)

| rank | fix | where | owner |
|---|---|---|---|
| 1 | GRT must not put M6 guides in M6-pair rows (same for M7 guides in M7-pair columns, M5 in M5-pair columns). `pg_track_truth.tcl` blocks tracks, and FastRoute still routes there. Replace the per-track obstruction on the PG layer by a per-gcell capacity cut that GRT honours: `set_global_routing_region_adjustment` (reduction 100 %) on layer M6 for every gcell row that intersects pair +- spacing, M7/M5 likewise for columns. Accept = new post-GRT check below returns 0 | `tools/die_plan` kit hook `pg_track_truth.tcl` (grt_pre.tcl) | GENBUG-IMPL (implement), DRT0255-PROOF-1115 (prove on sle_fe_v1 + slice_station__t37 + kv3_hroot from the kept 4_cts/5_1 state) |
| 2 | Post-GRT gate, cheap, before any 3-h detail route: for each net, total length of guides on layer L inside gcell rows/columns with < 2 legal L tracks next to PG; print the top nets; fail the route submit above a small limit (start: any single guide > 5 gcells). `win.tcl` in the probe dir already reads guides + PG stripes from `5_1_grt.odb`; run time about 3 min, 14 GB | new kit check next to `grt_post.tcl`; wave accept check | DRT0255-PROOF-1115 (script), KIT-OPS / wave lane (hook) |
| 3 | Keep ring / ft-station cells out of the rows under the M6 pair in the face strips: these families are placed by generated tcl (`landing_placement.tcl`, `ft_bit_sites.tcl`, `istations.tcl`), so the generator can skip the 2-3 std rows per 4.32 um that lie under the pair (row 0.27, pair + spacing = 0.77 um). Then the straight hop row is never a pair row. No plan event (cells move by one row) | `gen_phys.py` landing / station site generators | GENBUG-IMPL; die owners DIE-S81-92, DIE-QC-103, KV-102, HEAD-100 regenerate |
| 4 | QC M8 grant: the 20 type M8 tracks per 4.32 um sit exactly over the M6 pair, the 34 die tracks over the free rows. Shift the type band by half a period in `m8_grant.py` so M8 type tracks and free M6 tracks do not exclude each other in the same rows (needs the die M8 PG phase checked first) | `tools/die_plan/m8_grant.py` | DIE-QC-103 with GENBUG-IMPL |
| 5 | Mechanism B: as already ruled (die phase or pin_band_origins per die) | schema.py / pdn | GENBUG-IMPL, HEAD-100, DIE-S81-92 |
| 6 | kv3_hroot: fix 1 + `OT_PG_CELL_KEEPOUT=1` (its sink is under an M5 x M6 crossing); the FIRM column pattern stays the fallback | kit env | TYPES-KV-FAIL-1115 |

CLKSITE-RESERVE-1115: no action from this review (class D is 1 kit, not opened).

## 4 The one measurement still missing (DRT0255-PROOF-1115)

Smallest failing kit with a kept `5_1_grt.odb` (kv3_hroot, 661 MB, or sle_fe_v1): rerun detail route unchanged with
`detailed_route_debug -dr -maze -net <failing net> -iter 1 -dump_dr -dump_dir <dir> -dump_last_worker` (the form that
produced the hd_spn maze.log), then list the unreachable grid nodes of the failing worker as FABLE-PD-HEAD-1115 did.
This names the missing edge. Run it in parallel with fix 1; do not wait for it.

## 5 Stop list

- No unchanged relaunch of a type that failed DRT-0255 on a ring / ft / u_bound net (slw_su_l1 x3 today, kv3_hroot 13 attempts).
- Do not count `OT_PG_TRACK_TRUTH=1` as the cure for class A: 3 of 4 measured failures had it on.
- Do not roll `OT_PG_DIE_PHASE` / `OT_PG_CELL_KEEPOUT` to all dies as the DRT-0255 fix on the hd_spn or t49 result: they are class B / C only.
- No `MAX_ROUTING_LAYER = M7` as a general fix: M8 is where the trunk escapes over the pair today; without it the row has M4 only. As a single proof route it is fine.
- No more cell keep-out under M5 x M6 crossings for the ring / ft classes (0 cells of the net in 3 of 4 boxes).
- No droute iteration / density / band_spread knob forms: none moves a guide off the pair row.
- Do not classify by "ring-band x 30-47 um" or "no pin in box": both are the same class A.

## 6 Not checked

- The hard edge inside the worker (section 4). Class D clock net. Class C cell pins.
- Whether `set_global_routing_region_adjustment` at 100 % is honoured by this OpenROAD build (26Q3-1510) for 2-pin nets
  whose both pins are in the adjusted row; if not, fix 3 (cell rows) is the lever that works by construction.
- M6 spacing to a 0.288-wide strap was taken as the layer min spacing 0.032; with a width-dependent rule the "1 legal
  track" rows are 0.
- HEAD databases (none opened here); HEAD shows the same positions in the logs (8 points).
- sle_st_b_v2 pv41c959f3 attempt_8: kit dir already deleted on epyc9, not opened.
