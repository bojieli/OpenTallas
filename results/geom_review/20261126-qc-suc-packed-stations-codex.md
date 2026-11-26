# QC SU_C packed-station visual review

**Source only. Keep kit submission and routing held pending the scoped gate and clearance of placement concerns.**

The exact C1p R6 plan de1cef5cf59d and C1q source 00abead30cfa have the same three SU_C type blocks. In the old PLACE-PRECHECK reports, positive macro-site totals on the input buses are hypothetical per-bit seats. The supported emitter selects 132 actual packed centers across 16 priority chains and none are inside the exact hard macros. Another 63 stages in those chains have no specified center. The two East L1 chains also have all 17 actual stages unconstrained. The routers still have real channel and register-span defects.

## Actual placement evidence

I viewed the detailed-place density images for all three variants.

- East `epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-SUC-FTSITE/sle_su_c_1125131756/gen/sle_su_c/run/layout_review/place/density.png`.
- West cl19 `epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-SUC-FTSITE/slw_su_c__cl19bb38ef_1125131816/gen/slw_su_c__cl19bb38ef/run/layout_review/place/density.png`.
- West cl92 `epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-SUC-FTSITE/slw_su_c__cl92142dac_1124173816/gen/slw_su_c__cl92142dac/run/layout_review/place/density.png`.

The placed East banks leave a 458.190 µm CTL P1 gap and long isolated receiver paths around the packed PG macro. The West C1o placement with the wider gap still has a long diagonal reduction-output bundle. Older cl92 has a physical four-macro bottom wall and the native GRT iteration 15 overflow of 14,670 clusters beside the W edge. The 23:16 exact R6 SUC-C source fix e3e7019400b2 widens the west macro channel and is PRE/strict green for all three.

## New source candidate

The exact combined C1q successor c6aa6f33086e is in `epyc12:/srv/opentallas-scratch2/claude/QC-SUC-FTSITE/codex_station_scope_1126/combined_refine_spread.json`. I viewed its three images in `combined-refine-spread-render`, the exact East overlay `east_refine_spread.png` and the exact West overlay `west_refine_spread.png` in the same directory. The current renderer's resolved nominal maximum is 396.1 µm. The explicit cases below use native old placement, exact connected bit identities and the successor hard macro geometry.

| Cohort | Measured cases over 405 µm | Worst measured → modeled |
|---|---:|---:|
| East x_su_l1_i | 31 → 0 | 652.482 → 133.272 µm |
| East x_su_l1_p1_i | 112 → 0 | 678.834 → 152.334 µm |
| East x_ctl_p1_i stage 5→6 | 301 → 0 | 458.190 → 387.990 µm |
| West cl19 reduction producer→stage 0 | 255 → 0 | 727.434 → 273.483 µm |
| West cl92 reduction producer→stage 0 | 255 → 0 | 817.803 → 357.642 µm |

The East proposal fixes 1,256 existing payload stage sites for 143 measured bits with unchanged depths 8 and 9, moves each terminal at most 1.593 µm, and shifts the existing CTL P1 stage five south 70.2 µm. West spreads only the 255 affected first-stage output flops in each variant, with downstream station coordinates preserved. The three earlier SUC-C CTL P2 northern shoulder crossings are removed with unchanged local route length and 16.416 µm clearance. The exact stock Tcl emitter accepts every updated named key. The plan preserves the pins, native bus declarations and cycle latency.

The small East edge corridor still needs actual density and access confirmation, and the West stage 1 fan-in must be checked on the exact repaired placement. These exact candidates remain source-only. The prior lean official C1q carry was admitted E12 unit oth-ubuntu-2235300-1795685270. The combined scoped PRE service `codex-qc-suc-refine-pre-1126` is held by standard E12 live disk reservations.
