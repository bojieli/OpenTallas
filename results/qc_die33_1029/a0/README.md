# DIE-QC-33 / A0: NK V1L/ICG2 graph-home repair (analysis only, nothing launched), 2026-10-29 09:36 PDT

This is input for the image/count review. The repaired NK placement is **not launched**. ROOT authorized ONE run, and it waits for I/GEOM PASS-COND.

## Diagnosis of the failed NK placement (Codex unit 2355573, kit `codex-qc-a0-0830/kits/qfd_tile_nk_a0c_a0nk14icg2r1`)
I re-derived every long capture from `nk_geom/geom.tsv` with the geom_rules cell kinds. My exact max-distance enumeration finds 531 captures > 405 um, max 657.45; AUTO-GEOM reports 532 (one capture sits on the boundary). The list is in `nk_failed_long_captures.json`.

| class | captures > 405 | cause |
|---|---|---|
| u_me `s2_{round,x,tag,first,v}` broadcast root -> `g_sl[*].g_hd.g_tx.g_r[0].u_tx/q` (first TX relay) | 489 | 262 TX caps were snapped to **NL reset6** anchor coordinates, and the s2 root (unanchored) was pulled by GPL to the fanout centroid (~320,700). |
| W face `n_b_q[512/513]` (4.97,901) -> B-hop `g_kn.h[0]` + `g_icg.dr[*]` | 32 | Hop FFs had no home, and GPL stacked every hop stage next to its ICG (234,541-726). The first leg carries the whole 549-636 um distance. This is the "enable reach" and the main K0 548.53 failure. |
| reset entry `g_rst_native.q` -> slice `g_lrr.rq`, `t_out_reset_q`, `fy_q`, `mis_q` | 9 | No reset relay homes. |
| ROM `gs[*]` -> `mq_wrom[*]`, `split_fault` -> `fault` | 5 | Same mechanism (GPL centroid). |

**Root cause (placement only, no RTL fault).** The ONE run used `apply_anchor_targets.tcl`, which places the 8,077 **NL reset6** home coordinates. It runs in `face_flops_release.tcl` (PRE_DETAIL_PLACE), which is after GPL and as PLACED, so GPL never saw them. NL coordinates do not belong to the NK V1L macro graph, and 5,377 more were dropped by the halo clip. The other 7,280 sequential cells were left unhomed, including every hop FF, ICG, s2 root and reset relay. GPL therefore collapsed the relay/hop stages at the consumers: 7 relay collapses, and hop stages pile up beside the ICG. Measured anchor drift through DPL was <= 3.4 um, so DPL itself is not the problem.

## Repair: NK graph homes
- **Graph.** Nodes are the 15,357 sequential cells plus the 36 ICGs. Edges are 49,596 launch->capture legs through combinational cones (data and reset pins, clock pins excluded), plus FF<->macro legs measured to the macro bbox.
- **Fixed nodes.** The 2,582 face flops (FIRM at faces) and the 19 macros stay where they are.
- **Home rule (`solve.py`).** Every movable FF/ICG gets a minimal-move projection in (u=x+y, v=x-y). Its home is the point nearest its failed position that is inside the intersection of L1 balls of radius **RT = 395 um** (405 minus a 10 um DPL margin) around all its graph neighbours. Where the neighbours alone set the position (relay/hop chains), the home lies on the line between them, so stages end up evenly spaced (minimax).
- **Placement area.** Homes avoid macro halos and avoid the <= 12 um inter-macro gaps (x≈320 and x≈195; 2.16 um free after halos). Only 2 reset cells are exempt. FF density per 4.32 um bin is capped at the failed run's own p99 (31; final max 36, against GPL max 39).
- **Reset entry.** `g_rst_native.q` sits within 140 um of the rst_n pin (457.88,670.00). This uses the 150 backstop for this one pin; p90 is unchanged. At 25 um the path entry -> `t_out_reset_q` -> W `n_y` face (y≈1001-1103) is infeasible: it needs 848 um, but 2 legs give 790.
- **Enforcement (existing mechanism only).** This uses the KV-G3 `kit_istations.py` pattern. `graph_homes.tcl` is sourced at the end of `face_flops.tcl` (PRE_GLOBAL_PLACE). It sets all 12,811 homes (`nk_graph_homes.tsv`) **FIRM** and appends them to `ot_face_flops.txt`, so `face_flops_release.tcl` releases them to PLACED for DPL. The `source /work/apply_anchor_targets.tcl` line is **removed**. GPL places only combinational logic.

## Analytic census after repair (geom_rules `r2r_metrics`/`relay_metrics` on the homed geometry, `repaired_census.json`)
| item | failed | repaired (analytic) |
|---|---|---|
| r2r captures > 405 | 532 | **0** (max **395.00**) CHECKED (tool re-run on homed geometry) |
| graph legs > 405 incl. FF<->macro bbox | n/a | **0** (max 395.85) CHECKED |
| relay collapsed | 7 | **0** (balance max 8.92) CHECKED |
| ICG enable legs (Codex `enable_reach.tsv`, 100 rows) | 7 > 405, main K0 548.53, NODE 408.81 | **0 > 405**, max 395.8 CHECKED |
| cells moved | - | 880 (p90 0, max 354.5 um); 0 new homes in <= 12 um gaps except 2 reset cells |
| rst_n `pin_reg_max` | 261.76 | **OPEN (structural)**, see below |

**Not solvable by position alone, flag for ROOT/COORD.** 73 FFs hang directly on raw `rst_n`: 64 B-hop `h[*]` (ASR set), 8 `g_icg.dr` and the entry. The B-hop `h[0]` must be <= 405 from `n_b_q` (4.97,901.13). Staying <= 150 from rst_n (457.88,670.00) as well would need 684 <= 555, so it is infeasible. With homes, the rst_n -> ASR distances are <= 357 (0 > 405, 72 > 150). `pin_reg_max` depends on which FF repair_design's tree reaches first, so it is UNCHECKED and likely still > 150. Fixing it needs RTL: either feed the ASR of hop/dr from the synchronized reset relay, or put a local synchroniser at the hops. That is outside the position-only approval, so it goes up as an ASK. Clock reach/channel estimates are CTS/GRT items and are not addressed here.

## Render (VIEWED)
`nk_graph_homes.png`: on the left, the failed long captures; on the right, the planned homes coloured by class, with move lines.
- TX relays land in the y≈985 H-street and the east column.
- s2 roots land near (310,700).
- Hop FFs and the main ICG land at (157-238, 660-740).
- Slice reset rq cells land in the central V-street.
- No homes on macros.

Inputs viewed for comparison: `nk_auto_geom.png` (Codex failed run) and `nl_dpfail_auto_geom.png`.

## The ONE placement I would launch (NOT launched, waits for PASS-COND)
```
M=/srv/opentallas-scratch2/claude/die-qc33-a0; S=/srv/opentallas-scratch2/claude/codex-qc-a0-0830/kits/qfd_tile_nk_a0c_a0nk14icg2r1
K=$M/kits/qfd_tile_nk_a0c_a0nk14icg2r2; mkdir -p $K && rsync -a --exclude 'run/results/asap7/*/base/[23]_*' --exclude 'run/logs/asap7/*/base/[23]_*' --exclude place.log $S/ $K/
cp nk_graph_homes.tsv graph_homes.tcl $K/; sed -i '/apply_anchor_targets.tcl/d' $K/face_flops_release.tcl; echo 'source /work/graph_homes.tcl' >> $K/face_flops.tcl
sed -i 's/a0nk14icg2r1/a0nk14icg2r2/' $K/config.mk && mv $K/run/results/asap7/kq_*r1 $K/run/results/asap7/kq_qfd_tile_nk_a0c_a0nk14icg2r2 && mv $K/run/logs/asap7/kq_*r1 $K/run/logs/asap7/kq_qfd_tile_nk_a0c_a0nk14icg2r2
ssh -o ControlPath=none intel2 ~/.local/bin/ot-run --mem 32 --threads 8 --dir $M -- bash $M/nkr2_place.sh   # nkr2_place.sh = Codex nkr1_place.sh with k=$K, container name dqc33-a0-nkr2-place
```
After the run: AUTO-GEOM (geom_check.sh) plus a recomputed `enable_reach`. All of r2r, relay, enable and reset must clear before any CTS/GRT. Note that the `echo >>` places the source after the `face_flops.tcl` closing brace, at top level. Check the line placement at kit build.

## NL ONE placement (Codex unit oth-ubuntu-2306050, kit `qfd_tile_nl_a0c_a0nl14icg2r1`): FINISHED, FAIL
- ot-run exit 2. GPL converged (1644 s, `-overflow 0.21`). DPL then failed with **DPL-0033**: 2 cells are unlegalised, `g_sl[4].g_tx.g_r[0].u_tx/q[10]` and `g_sl[6]...g_r[1]/q[33]`, which overlap PHY_EDGE tapcells, and `t_out[343]` is off its site. There is no `3_place.odb`.
- My AUTO-GEOM probe on `3_5_place_dp-failed.odb` (own dir `die-qc33-a0/nl_dpfail_geom`): **r2r 410.02, 8 > 405** (worst `s2_x[13] -> g_sl[7].g_tx.g_r[0].u_tx/q[13]`, same class as NK), relay_collapse 0, pin_reg_max 143.73, p90 8.95, channel_h 0.822/v 1.273/col_v 1.334 (est.), clock_reach 762.25. Verdict FAIL.
- The same graph-home method applies to NL. It should take the 8 TX legs and the 2 DPL cells; snapping homes to rows would avoid the tapcell overlap.
