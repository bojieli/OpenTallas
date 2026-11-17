# FABLE-PD-QC-HEADSEG44 — why QC headseg44 will not detail-route (2026-11-16 18:4x PST)

Read-only review of epyc2 `/srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/headseg44` (runs_mm = old run, runs_np = nonport
rebuild), answering the QC-TYPES-R ask of 18:28. Everything below is MEASURED from the files named, unless marked INFERRED.

## Verdict in three lines
1. The nonport rebuild is the same design as the old run. Its hold scope never reached the stage that inserts the hold
   cells, so it will plateau where the old run did. Stop it now.
2. The hot spot IS the hold cells. 75 % of the violation rows touch a hold-chain net; the 2.6 % figure only counted
   nets with "hold" in the name.
3. Fix = fewer hold cells in the south strip (scope + margin + cell type at the CTS-stage repair), then spread the
   south pins. Both are kit changes (QC-TYPES-R). No outline growth, no plan row.

## 1. Root mechanism, with numbers

**a. The rebuild changed nothing before detail route.**
- `4_1_cts.odb` of runs_np and runs_mm are byte-identical (`cmp`).
- The CTS log of both runs is the same: 62,459 -> 79,058 instances, 16,494 hold buffers inserted in nine chunks
  (8 x ~2,001 + 483), utilisation 49.6 % -> 54.1 %. There is no `OT_HOLD_SCOPE` line in `4_1_cts.log`.
- `OT_HOLD_REPAIR_SCOPE` is only read by the GRT-stage helper (`tools/orfs_hold_mm.tcl`). That stage inserted 105
  buffers in both runs (old scope=reg2reg, new scope=nonport).
- GRT totals are identical to the digit: demand 554,205, wirelength 418,912 um, 0 overflow.
- Detail-route totals track: old 14726 5949 5114 3297 3075 2791 2540 2337 2270 2143 1688 1557 1463 1318,
  new 14610 5739 4788 3386 3012 2887 2696 2516 2333 2107 1895 1829 1794 1638. The old run then sat at 833-1,231 with
  five saw-teeth through iteration 52.

**b. A full slab under macro 0.**
- South strip x 10-62, y 2.16-16.2 (728 um2, the rows between the south edge and the 5.4-um halo of the SRAM at
  y 22.464): fill 96.2 %, 6,923 cells, 9.5 cells/um2. Rows y 4-16 at x 46-62 read 92-100 % in 1-um bins.
- Of those cells 3,844 (55 %, 280 um2) are resizer hold buffers, all BUFx2. Design-wide: 12,289 hold BUFx2 in the dump.
- Before CTS the DRC window (46-62 x 6-18) held 646 cells at 54 % fill; after hold repair 1,705 cells at 90.6 %
  (`results/drc_diag/south_growth.json`).
- Cause of the slab: 445 of the 541 south pins sit at minimum pitch 0.096 um from x 13 to x 58 (41-42 pins per 4 um).
  x 58-102 has zero pins and 40-70 % fill. Every pin brings its capture flop (`io_flop_at_pins`, 4 columns), an
  `ot_inhold` HB2 and an `ot_ihdrv` BUFx4f into a strip only 14 um tall, then hold repair fills what is left.

**c. Why this patch and not the rest of the slab.** Density is the same along the slab (control boxes 0.89-0.93 fill,
8.4-9.0 cells/um2; hot box 0.907, 9.67). What differs is M2 demand, from `route.guide` (nets present per 0.57-um gcell,
y 5.4-15.66):

| x (um) | 14-22 | 30-38 | 40-48 | 47-50 | 50-58 (hot) | 58-66 |
|---|---|---|---|---|---|---|
| M2 | 9.2 | 11.0 | 12.5 | 14.4 | **17.6** | 11.1 |
| M3 | 12.0 | 15.6 | 17.4 | 18.1 | 17.2 | 10.3 |

M2 has 15.8 tracks per gcell before the follow-pin rails. 1,406 nets use M2 in the 78-um2 hot box, 851 of them
hold-chain nets. GRT reports no overflow because its capacity model does not price pin access at 96 % fill.
- The extra M2 load at x 50-58 is the east end of the wrom mux: `t_lane_c` (the 16-lane select, each bit 78-140
  guide segments spanning x 36-60) meets the `aligned_wr`/`q_wrom` flops and 145 mux gates (`_129xx_`), at the corner
  where the strip opens into the channel between the macro columns (macro 0 ends x 54.864, halo to 60.26).
- PDN: M5 pairs at 5.4-um pitch (51.0-51.31, 56.4-56.71); not the differentiator, same everywhere. Clock leaves: 18
  leaf nets touch the window, 109 rows; a victim, not a cause.

**d. Violation make-up (np `5_route_drc.rpt-10`, 1,895 rows).** 1,420 rows (75 %) name a resizer net `netN`
(14,674 such nets in the guide file, 13,760 with N >= 1400; INFERRED to be hold-chain nets from the 16,494 + 105
insertions against about 100 other buffers). `t_lane_c` 197, `aligned_wr` 160, clock 109, PG 83, `ot_inhold` 72.
x 49-58 holds 1,694 rows; y 7-13 holds 1,676.

## 2. Ranked structural fix (all kit / flow changes, QC-TYPES-R; no QC-PLAN-R row)

1. **Cut the hold cells at the stage that makes them (CTS-stage repair in `4_1_cts`).**
   - Apply the nonport scope there. `hold_scope_summary.json`: 5,585 of 12,289 hold cells are port-only; 581 of 1,018
     in the hot region. Window fill 90.6 % -> about 69 %.
   - Repair to the gate, not to +30 ps. At start the log reads 1,052 endpoints violating against 7,020 endpoints
     selected at margin 30. Use margin 0-10 and close the rest post-route with the HB4 ECO already proven on coll_n.
   - Use delay cells (HB2/HB4) instead of BUFx2 chains for what remains: fewer cells and fewer M1 pins per ps.
   - Proof before spending detail route: `4_1_cts.odb` differs from the old one, "Inserted N hold buffers" sums to
     well under 16,494, and the 46-62 x 6-18 window reads <= 70 % fill.
2. **Spread the south pins.** Region is `bottom:*` with `-min_distance 2` tracks; the placer packed them at x 13-58.
   Give the S buses a pitch of about 0.19 um over x 13-115 (541 pins fit), or split wrom_q into two ranges either side
   of the channel. Halves the flop/inhold stack depth per um of edge. Kit change while this master is unbound; it
   becomes a plan row only if a parent bind already fixes these pin x positions.
3. **Density screen on the whole slab, not the patch.** Partial placement blockage (max 65-70 %) on x 10-62,
   y 2.16-17.06, applied before the CTS hold repair. A screen on the 192-um2 window alone moves the problem west:
   x 41-50 already reads M3 17.6-18.1.
4. Not needed: outline growth (design is at 54 %), clock-tree change, PDN change.

## 3. Stop the current run?
Yes, now, by exact unit: runs_np `oth-ubuntu-2182252-1794878574` (container ot-headseg44-kv1-np). It is the same
design as the old run and is following the same curve. Also stop the old runs_mm unit 3610370 (iteration 52, 6 h,
plateau 833-1,231). Keep logs, reports and both DBs.

## 4. Stop doing
- Relaunching from the same placed DB with a flag that only the GRT-stage helper reads. Compare the CTS DB and the
  inserted-buffer count with the previous run before detail route starts.
- Classifying "hold" by net name. Resizer hold nets are called `netN`, instances `holdN`.
- Waiting on this form past iteration 16, or relaunching it unchanged.
- Blocking only the 20 x 10 um patch.

## Not checked
- Which SDC drives the CTS-stage hold repair and why reg-to-reg needs 6,704 buffers (skew between pin flops and core
  flops is the likely source; not measured here).
- The `netN` -> hold-chain mapping was not confirmed in the DB (no OpenROAD session opened).
- Cell positions are from the runs_mm `layout_dump_5_1_grt.json`; runs_np has the same CTS DB but no dump of its own.
