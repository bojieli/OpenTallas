# PROG current-aspect corner repair, 2026-10-29

Verdict: PASS-COND for one GRT-only trial (at least 50 iterations). No detailed route or STA admitted yet.

Source: epyc2 `codex-qc-cores-0815/prog_l2h3_route2` actual `5_1_grt.odb`, current 354.24 x 259.2 R0 outline.
The old 259.2 x 354.24 s8b signed-cache view is inapplicable to this slot. Its PG-only repair restores
216 supply terms but its 89 register paths over 405 um remain FAIL; it is not a release view.

Personally viewed `results/codex_qc_fix_0825/prog_corner.png` and `prog_spread_full.png`.
The persistent 47-hour DRT failure concentrates outside the northeast SRAM pin-column keep-off:
528 cells in x270.6..281/y118.8..140.4, including 104 flops and 376 combinational INV/NAND/OA cells.
PG stripes and clipped routing blockages remain continuous, but logic crowds the narrow escape column.
Moving only those 376 combinational cells into the visibly open east street (x285.12..319.68) removes
that concentration while leaving all macros, flops, clock cells, pin locations, masters and connectivity unchanged.
Maximum actual move is 21.87 um; no added cell or cycle. Native rows and all occupied footprints define free sites.

Native geometry after placement: register reach 354.73 um, zero paths over 405; pin-register p90 23.11/max27.73;
zero cells on macros; own-clock-driver reach 44.5 um. The global clock-entry distance 255.76 is informational.
The four legacy ft clock/reset ports trace through actual `ot_isl_ckft` and `ot_isl_rstft` cells and are
classified by the normal typed ft metadata, yielding zero unregistered pins. No pin exception was added.
Macro-dominated fill/empty and existing E partial-face pressure are unchanged. Channel projection still needs GRT0.

Independent reviewer `/root/coverage/review` viewed both pictures and returned PASS-COND for ONE GRT-only trial:
native `check_placement` must pass; require zero GRT overflow and no new corner congestion; view the resulting guides
before any DRT. The old failed run stays untouched.
