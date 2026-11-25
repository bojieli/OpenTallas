# QC-HC0-GROW options B and C (COORD Q-08), 11-25
Target: hc0 (E strip, 622.08 x 717.12, 366.2k cells final synth, 0.82 cells/um2) to <=0.60 or <=0.50 under the 26 mm die cap.

## C: remove cells from hc0 (measured on E4 type pv48712631, epyc2 kit attempt_3 yosys netlist; other 4 types assumed same)
Breakdown (383.2k raw / 366.2k final): 8 lanes u_u_xl0_0..7 237.1k (29.2-30.0k each), u_u_xh0 55.2k, 4 landing rings 40.8k (13.3k+13.3k+13.4k+0.8k), pd9 b_hw_i pad chain 26.7k, ot_dp_st stations 19.7k, relays/glue 3.4k. Overhead 90.6k (24%), logic 292.3k. Placed utilisation 12.6%: only the soft cell count binds, not area.
Hosts: E strip has no free area; st_a (south) has ~0.67 mm2 open and 68k soft cells; fw/fe 0.25-0.27 but 3-4 hops away; hc1 0.89, c_E4_tn_00 68% macro.
Options (cells out): A 3 wide rings as hard cores 40.0k (in hc0, ~0.014 mm2, 0 cycles); B pd9 pad to sender 26.7k (st_a soft 0.084->0.12 mm2); C lane hard core 29.6k each (~0.026 mm2 est.); D xh0 hard core 55.2k; E route rsn/rsf from tn_00 to hc1 35.9k (estimate); F drop pad inverters 12.6k (estimate).
Recipes: <=0.60: A+C x2 = 99k (0.60 borderline); A+B+C x2 = 126k (0.54). <=0.50: A+B+C x3 = 156k (0.49); A+C x4 = 158k (0.48).
Sources: epyc2 .../s29q103S4Q9N46R6V4/items/sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631/attempt_3/gen (synth_stat.txt, cell_census.jsonl); FLAGS-CELLCHECK.tsv; OVERSIZE-1.md.

## B: ROWSHIFT (shrink fw/stm/sc/fe row, hc grows, die height unchanged)
Needed D for hc0: 264 / 460 / 685 um for 0.60 / 0.50 / 0.42. Row densities after shrink (measured kit cells): D=460 -> sc 0.322, stm 0.321, fw/fe 0.358.
Blockers measured: (1) plan objects fill the full height (no empty band >= 460 um in 18 E row types; largest gap 127 um); (2) E/W lane windows: largest face needs 1294.7 um of 1371.7 at D=460 (17 windows, 4.5 um gaps), 26 of 35 faces end above 1371.7; (3) stm hard cores reach y=1661.4, sc 1499: without moving them the row shrinks <= ~150 um.
Hybrid: die +345.6 (25989 mm height) + D=150 -> hc 1212.7 um, hc0 0.485 with no hard core moved. D=339 (-> 0.42) needs stm/sc core re-seat.
Generator (D parameter): per-boundary window repack, station resample, ft_corridor re-site, relay re-solve, landing_remap. ETA 20:00 (D=150). DEFERRED -> C1q, owner QC-HC0-GROW.
