# QC-CLK-MESH r10 (INFRA-FIRST-QC-R10, 2026-10-26 21:30 PDT) -- numbers UNCHECKED except where marked

Fix: `qc_clk_mesh3.py solve` now times the LEGALIZED geometry (`--geometry legal`, default; `ideal` = r3 plan model,
reproduces r3 nominal 12.772 ps TT exactly). d1 sizing is computed on the nominal plan netlist, each driver group is
decomposed into real cells (BUFx24/BUFx16f), `legalize()` places every unit, and every tree stage is one real
driver->load net between legal pin centroids (ASAP7 R 1x LEF pins + unit tie straps); fine drivers attach to their strap
at the legal site. `--feed r9` uses the R9 tree5 16-leaf H-tree (RCX leaf arrivals + per-leg variation) as the global tree.
`sta-export` + `die_sta_related.py --pair-unc` = related-pair die STA over all 377 entries.

| | mesh3 top tree, legal (`legal/`) | R9 feed, legal (`r9/`) | r3 ideal (reference) |
|---|---|---|---|
| cell groups / instances | 22886 / 35488 (34980 x24 + 508 x16f) | 21850 / 33416 | 22886 groups |
| bumps / max | 427 / 77.76 um | 207 / 77.76 um | not timed |
| real nets max (reach 450) | 443.2 um, 0 over | 441.6 um, 0 over | - |
| nominal entry skew TT / FF | 26.27 / 22.94 | 303.64 / 247.93 | 12.77 / 10.9 |
| MC whole-die (INFO, not a gate) | 301.5 / 262.3 | 561.1 / 459.6 | 293 / 258 |
| per-seam-pair U max TT / FF (773) | 103.15 / 92.73 | 306.04 / 250.99 | 97 / 93 |
| die STA TT setup worst (997 ordered pairs) | +563.51 | +349.02 | - |
| die STA FF hold zero-logic worst | -91.48 (all 997 need data hold buffers) | -248.44 | - |
| FF kit-contract hold (W 40) | +29.74 PASS (need 10.26) | -123.10 FAIL (need 163.10) | - |

CHECKED by independent recompute from the 13 per-sample solve files (`scripts/numcheck.py` -> `numcheck.txt`): STA worst
slacks, pair U maxima, nominal spreads, 377/377 partitions with taps, 997 connected ordered pairs, 0 uncovered bits.
The R9 feed fails structurally: its leaf lattice (y 3918/9145/17120/22347, central bridge arm 7975 um) is not
commensurate with the 19 mesh tap rows (regions 4/6/5/4 rows, 11-13 columns) -> 287 ps nominal region-to-region spread
at the region seams (y ~5900 and ~13800). Renders viewed: `r10_pairs.png`, `r9_feed_plan.png`.

## Real core views (COORD 21:3x): `legal/sta_cv`, `legal/sta_cvraw`
`sta-export --core-view MODULE=TTe,TTl,FFe,FFl`: the partition core latency range = union over its hard cores (viewed
module -> its range, others -> declared 250 TT / 202.5 FF), folded into the entry arrivals as the delta to the declared
value. Applied to the 12 su_c partitions. RP1 qfd_dv_s8_crh_rp1 (SIGNED, RCX, lane-CHECKED mean 247.46 TT / 195.95 FF,
window 33.8 / 31.2 centred) and VMR qfd_dv_s8x_vmr (F4F GRT model 256.41 +-6.75 TT; FF 194.06 .. +12.6).
- sta_cv: TT setup +563.51, FF hold zero-logic -94.25 (997/997 need data hold buffers), FF kit-contract +11.21 (W 40, need 28.79) PASS
- sta_cvraw (RP1 raw RCX sink extremes 219.69..268.91 TT / 172.05..219.00 FF, sensitivity): +557.25 / -102.55 / +2.91 PASS
Worst hold pair sl_W3_su_c -> c_W3_bn_00; worst kit-contract pair sl_W4_su_c -> sl_W4_su_l1 (RP1 window sets it).
