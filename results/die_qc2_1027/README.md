# DIE-QC-2 (10-27): QC slice clock — (A) 16w trunk NDR vs (B) locality re-cut

Base: claude/die-qc-1027@e80fd072df. All numbers are OWN and UNCHECKED (no independent NUMBER-CHECK yet).
Data: intel2:/srv/opentallas-scratch2/claude/die-qc2-1027 (C1w5 = routed build, S_none/S_trunk/S_all = SPEF NDR what-ifs).

## Outcome
Neither (A) nor (B) gets in-region spread down to <= ~150 ps. Per the brief, the next step is the 12.8e per-slice mesh.
- **(A) 16w NDR on the trunk** (3,539 nets), real GRT:
  - GRT disabled the NDR on 542 nets for congestion. It reached extra iteration 12/50 (TT) and 1/50 (FF) after 42 min, so I killed it as non-converging (`runA_ndr_grt_summary.txt`).
  - I measured (A) instead by scaling the routed SPEF (`spef_ck.py`: R x 0.0625, C x 2.2 on the selected clock nets).
  - The trunk sits above the partition LCAs. Insertion drops by about 3 ns, but in-partition spread does not change.
- **(B) locality re-cut**: this is an estimate only (below), so I did not build it. It fixes the seam OCV but not the nominal spread.
- **Root cause of the nominal spread.** The site pass moves tree nodes off the cores, which leaves sibling legs unequal:
  - Real internal path-length spread is up to 783 um on std slices and 1,518 um on W5 (0 for the ideal tree).
  - Routed 1x M8 runs about 334 ps/mm, against the builder's 199 ps/mm. The builder uses R = 4.336e-3 kOhm/um, half of ASAP7 M8.
  - So the nominal spread is roughly 300-370 ps at routed RC, whatever the region cut.
- **Negative experiment: DME pad length-match** (`length_match_negative.diff`, reverted).
  - The U-jog repeaters snap far off over the cores. The pads came to 1.2-1.9 m (20-30 % of tree wire) and did not converge.
  - Placement spread got worse: W5 1,439 ps.

## Fix kept: W5 re-cut (regions_w5cut.json)
The hard_io_serdes_2 region box contained io_serdes_2, so the bisection cut the c_W5 partitions. I moved io_serdes_2 into hard_ucie_kv.
- Its only link is to c_W5_bf_01 (1,197 bits), which adds 5 crossings: 269 total (`crossings_plan_w5cut.json`).
- Routed build C1w5 (slice spine, rep 250, no NDR):

  | measure | value |
  |---|---|
  | GRT overflow | 0 TT/FF (2.92 %) |
  | insertion | 9.77-10.54 ns |
  | per-partition spread | median 213, max 372 (W5 was 549) |
  | count-aligned (MESO-INTEG-1, x1.05) | 269/269 PASS, lo 221.8 / hi 1887.8, all DEPTH 8 |
  | current-ring worst | -463 |

## Measured (routed RC, SPEF what-if on the C1w5 topology; none = validation, within ~2-3 % of the combo arrivals)

| variant | TT spread med/max | FF spread med/max | insertion TT | CA (x1.05) lo/hi | die STA --cppr-lca TT setup intra/seam | FF hold intra/seam | HB4 TT setup intra/seam | landed |
|---|---|---|---|---|---|---|---|---|
| C1w5 routed (1x) | 213/372 | - | 9.77-10.54 | 221.8/1887.8 | +114.2/+107.7 | -476.3/-479.9 | -280.9/-478.6 (18.9M+2.5M cells) | FAIL (-31.0) |
| trunk 16w | 235/358 | 199/310 | 6.49-7.04 | 106.9/250.2 | +199.1/+186.9 | -391.6/-406.1 | - | FAIL (-109.9) |
| whole-tree 16w | 156/202 | 120/155 | 6.40-6.72 | 115.6/117.6 (D4 77, D8 192) | +345.1/+342.7 | -245.8/-247.1 | +168.9/+105.0, hold 0 (10.4M+1.6M cells) | PASS (115.8/192.1) |

Region-CPPR (the default) for whole-tree 16w gives TT +239.3/+228.4 and FF hold -327.9/-336.6.

Whole-tree 16w is the only variant that closes, and only with HB4 and --cppr-lca. Its spread (202 TT max) still misses 150, and it cannot be routed: real GRT already drops NDR on 15 % of the trunk-only set.
--cppr-lca alone on the predecessor's r250 data: TT -293.6 -> -18.9 intra.

## (B) one-page estimate (locality re-cut, MESO-INTEG-1: K_tree=-1-PAD, arrivals x1.05)

| cut | regions | crossings | bits crossing | routed insertion | seam OCV (~2.5 % x (Ua+Ub)) | nominal in-region spread |
|---|---|---|---|---|---|---|
| slice (now) | 13 | 264-269 | 63,170 | ~5 ns region / ~10 die | ~255 ps | 300-370 |
| half-slice | 25 | 576 | 204,914 | ~3 ns | ~150 ps | 300-370 (slide floor) |
| quarter (bf/bn/centre/tn/tf) | 61-62 | 528-533 | 199,250 | ~1.5 ns | ~80 ps | 300-370 (slide floor) |
| partition | 377 | 3,005 | 1,277,498 | <1 ns | - | ~200 (leaf legs) |

- No crossing is longer than 3 mm. DEPTH mix is 4-8.
- Cost of the quarter cut:
  - Flops: +136k crossing bits x DEPTH 4-8 = 0.55-1.1M flops, about 0.16-0.32 mm^2.
  - The rings go into partition glue, so the c_/sl_ types change and need a new sign-off.
  - tok/s: about -0.1 % (+4-8 cycles per layer).
- The re-cut fixes the seam OCV only. Each region is still a slid tree, so spread stays above 150.

## Next: 12.8e per-slice mesh
INFRA-FIRST-QC-R12 mesh3 measured nominal entry skew 22.1/19.7 ps and pair U max 103/95 (CHECKED there).
A mesh common point removes the slid-tree nominal floor that defeats both (A) and (B).

Scripts are in this directory: ndr_nets.py, mk_combo_qc.py, runA.sh, runC.sh, spef_ck.py, sta_spef.tcl, runS.sh, postA.sh, mkq.py, pspread.py.
