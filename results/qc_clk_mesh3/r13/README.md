# INFRA-FIRST-QC-R13: one identical top-tree cell set per partition type (QC die)

All numbers here are UNCHECKED (plan model, waiting on NUMBER-CHECK). Branch `claude/qc-mesh-r13-1026`, off R12 40c84d59cd.
Data: `epyc2:/srv/opentallas-scratch2/claude/qc-mesh-r12/pkg/out/{r13,r13p}`.

## (1) Identical cell set per type: options (a), (b) and the chosen (a+b) structure
`scripts/r13_eval.py` gives `eval.json`.
- **(a) Top tree only in 12.7 channel bays outside the partitions.** FAIL on reach. Partitions cover 97.7 % of the die; the only free area is the west strip x < 1555 um. The farthest column tap is at x = 31207.68 um, so there would be a 29,652.7 um unrepeated gap against a 450 um reach (66 stages would have to sit inside partitions).
- **(b) Periodic top tree inside partitions, with plan-computed per-tap sizing.** FAIL on skew. Content that is identical per type is periodic in x (2471.04 um, 12 copies per row), so a periodic chain arrives linearly in x. That is 6 stages per period, 411.84 um each (89.6 TT / 72.25 FF ps). Row spread is 3225.5 TT / 2600.9 FF ps and neighbour-period skew is 537.6 / 433.5 ps. Per-tap sizing moves a tap by only about 10-30 ps.
- **Channel cells placed inside partitions instead of a channel.** This breaks identity: 14 of 28 types below the centre and 9 of 9 above.
- **Chosen: (a+b) hybrid.**
  - ONE die-level centre-channel x-tree (y = 13132.8, the die centre seam). This is the only non-periodic part: 23 node groups and 108 repeater groups. It needs a plan delta.
  - 12 period trunk columns at x = 2177.28 + 2471.04k.
  - Per column: a y-tree whose bottom subtree covers 10 local rows; the top half is its exact mirror, with the root on the centre line.
  - Per local row: a 4-leaf x-tree to taps at offsets 0 / 622.08 / 1235.52 / 1848.96 um. (`eval.json` still lists 1866.24 for the 4th offset; it was written before the off-die fix.)
  - Seam gap rows are nudged 8.64 um into the partition nearer the centre. The centre group is split into two mirrored half trees.
  - Ideal: 35 column stages + 32 channel stages; leaf spread 0.44 TT / 0.51 FF ps; longest leg 436 um (reach 450).
- **Legal solve on the per-type island lattice** (`qc_clk_mesh3 --feed periodic --islands type`, new `assign_periodic`):
  - 74/74 hosting types identical, 0 identity violations; 4512 groups on slots; max move 18.2 um.
  - Independent check `scripts/r13_idcheck.py` on the physical export: every cell origin, master and orientation mapped back to the TYPE frame gives **IDENTICAL** (74 types, 360 instances, 0 missing). This check found an r12 export bug: units were stacked +y in the die frame, which mirrors them in MX hosts. It is fixed in `r13_phys_sites.py` (units now stack along the type frame).

## Clock MC (13 samples x TT/FF) and related-pair STA (997 pairs)
- **Clock MC:**
  - Nominal tap skew: 48.51 TT / 39.57 FF ps (r12: 22.10 / 19.65).
  - MC worst: 329.8 / 285.4 ps.
  - Insertion: 6456-6797 TT / 5185-5485 FF ps.
  - Pair uncertainty (U) max: 116.17 TT / 111.21 FF ps.
  - Longest net: 437.5 um (0 over reach).
- **Die STA** (`sta/`, pair-unc):
  - TT setup +537.33 ps, 0 negative pairs.
  - FF hold, zero-logic: -117.69 ps. This is covered by the approved data hold buffers.
  - Kit-contract hold: +6.20 ps PASS (window 40, 33.80 needed).
- **With core views** (`sta_cv/`): RP1 = **F4G** RCX leaf-mean range TT 231.2-254.4 / FF 181.9-203.8 (`qc-f4g-1026/kits/qfd_dv_s8_crh_rp1_f4g/f4g_chain.txt`); VMR = GRT model 249.66-263.16 / 194.06-206.66. Result: TT setup +537.33 / FF hold -117.69 / kit-contract +6.20 PASS.
- **HB4 hold buffers** (`hb4_count.json`): 2,730,799 HB4 = 0.2788 mm2 (0.034 % of the die); worst partition fit 0.28 % of free area; TT cost 249 ps against TT setup +537.
- **Cost vs r12:** periodic identity costs +26 ps of nominal skew. The top-tree arrival spread is 31.0 TT. A corr re-solve (`scripts/resolve13.py`) brought it to 23.7 but broke identity (8 violations) and was non-monotone, so it is not used. The next lever is a per-TYPE identical tap sizing.

## (2) Dry build (`dry_build/`)
Run: `die_clock_mesh build --ndr 16w --explicit-cells`, with the R9 nearest-move seam fix applied to 22 channel units (at most 0.864 um, `scripts/r13_seamfix.py`, dry aid only).
- **3147 plan errors:** 779 `no_clock_track` (r12: 1368) and 2368 `no_pin_stack` (r12: 1681). Without the seam fix, the build stops at 22 `cell_site_seam` (channel nodes) before the track stage.
- **Risers:** 2.6-6.9 um. Of the failing pin stacks, 776 sit on their tree row, so the riser comes from router track moves (PG / shield packing). About 1000 sit 4-11 um off the row, where the type slot y lattice (19.3 pitch) misses the row line. The rest are column y-tree cells.
- **Next:** plan each tree row's trunk y on a legal M8 track between PG stripes, put a slot row at (track - TREE_OFF) in each type frame, and use a PG-flank shield only where no offset fits. This needs one re-solve plus MC. It is not done in this lane.

## (3)/(4) Not done in this lane
Not done: physical ot-run build, DRC, RCX with the 0.64 um rules, resistor-graph check, and RCX-fed STA. They are blocked on (2) reaching 0/0 and on the centre-channel plan delta.

## Renders (viewed)
- `render/r13_top.png`: 12 period columns, centre channel line, mirrored half trees.
- `render/r13_zoom_cb.png`: cb rows 1-4, two periods; the MX cb rows host the same local rows.
- `render/r13_zoom_centre.png`: channel at y = 13132.8 and both mirrored half trees.
- `sites/r13_top_sites.png`.

## Tools
- `tools/die_plan/qc_clk_mesh3.py`:
  - `--feed periodic` (`periodic_feed`) and `assign_periodic` (one slot per class, identical in every instance of the type; it registers its slots).
  - chan_node / chan_rep kinds.
  - Optional CORR terms in plain merge (an empty CORR leaves behaviour unchanged).
  - The default path is unchanged: `test_qc_clk_mesh3.py` 6 PASS.
