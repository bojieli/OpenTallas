# SLE cws1 FREG child, November 22 placement review

I viewed the actual layout and density for `sle_cland_w517_n_s10_freg`. The fixed 88.992 by 51.84 µm footprint has no macros, 45% utilization and a 0.334 maximum M5 pin-track fraction. The north input and south output rows are continuous. The density is spread across the interior with small low-density gaps. The only geometry flags are `rst_xn[6]` and `[2]`, whose first reader groups are approximately 52.7 and 65.0 µm from their south-face inputs. The clock-entry distances are 22.19 µm on `fclk` and 11.68 µm on `clk`.

This geometry is accepted for an isolated CTS proof. The fresh build passed stock face checking for all 1,037 signal bits, with no missing or extra pins. Pre-place LEC proved all 4,737 compare points. A separate netlist check proved all 517 data inputs and the forwarded start each enter one direct `fclk` face-register D pin. CTS timing and parent boundary qualification are pending.

Placed unit `2086136-1795382235`, exit 0. Exact kit `epyc10:/srv/opentallas-scratch2/claude/QC-SLE-R5/freg_hard_children/sle_cland_w517_n_s10_freg/registered_face/kits/sle_cland_w517_n_s10_freg_synth0`. Reviewed `run/layout_review/place/{layout.png,density.png,smells.json}`.

## Sibling placements

I also viewed the exact `sle_cland_w517_n_s10_1_freg` and `sle_cland_w517_n_s10_2_freg` output density plots. Both have the same fixed outline, cell distribution across the center, continuous north and south pin rows, and a 0.334 M5 pin-track fraction. The only flagged legs are `rst_xn[6]` and `rst_xn[2]`, at 47.74 and 65.49 µm for the x_hc1_st_b child and 51.83 and 65.70 µm for the cws2 child. The admitted placement units `2288732-1795382547` and `2289172-1795382547` both exited zero. The geometry supports an isolated GRT timing proof for each.

Exact images are under `epyc10:/srv/opentallas-scratch2/claude/QC-SLE-R5/freg_hard_children/<master>/registered_face/kits/<master>_synth0/run/layout_review/place/density.png`.

## cws1 exact global routing

**GOOD for the private detailed route.** I viewed `run/layout_review/grt/density.png` from the same cws1 kit after unit `2386496-1795382678` exited zero. Maximum grid demand was 86%, with no grid cells above 90%. Placement density stays distributed across the footprint. The same two short reset paths are the only geometry flags. The scoped FF repair cleared all eight internal violations, improving the internal worst slack from −106.71 to +17.01 ps. Final global-routing setup worst slack was +137.53 ps. The remaining negative hold reports include boundary paths that require parent qualification.

## Sibling global routing

**GOOD for the private x_hc1_st_b detailed route.** I viewed the exact `_1_freg` GRT density image. Unit `2470653-1795382803` exited zero with a maximum grid demand of 82% and no cells above 90%. Setup was +135.07 ps and internal FF hold was +17.49 ps with zero violations. The two short reset legs remain the only placement flags.

**ISSUES for cws2 detailed routing.** I viewed the exact `_2_freg` GRT density image. Unit `2470655-1795382803` exited zero with +136.64 ps setup and +15.37 ps internal FF hold. Peak grid demand reached 100% with 35 cells above 90%. The marked hotspots are near (37.91, 31.07), (29.36, 6.55) and (51.02, 20.80) µm. The current cws2 checkpoint is held for a placement adjustment that reduces routing demand.

## cws1 routed result and cws2 density variant

The reviewed cws1 form finished at 13:41 PST with minimal-profile physical SIGNED, TT setup +141.76 ps, DRC and antenna zero, and all 1,037 face checks passing. Its FF boundary paths remain conditional on a real-parent hold receipt. Exact routed-netlist LEC proved 4,622 of 4,622 points with zero differences or undecided, unit 3167594 exit zero. Its signoff and routed proof are under the existing cws1 kit at `signoff/signoff.json` and `lec_routed_1122/lec.json`.

I viewed the exact cws2 density-0.47 placement. The outline and pin rows are unchanged and the center remains broadly distributed. The 0.334 pin-track fraction is unchanged. Only `rst_xn[2]` remains flagged, a 46.35 µm direct-distance reader leg. I cleared this specific placement for isolated GRT timing and congestion measurement, unit 3167391. Its kit is `epyc10:/srv/opentallas-scratch2/claude/QC-SLE-R5/freg_hard_children/sle_cland_w517_n_s10_2_freg/less_dense/kits/sle_cland_w517_n_s10_2_freg_synth0`. Detailed route depends on the density variant's own viewed GRT result.

### cws2 density-0.47 global routing

I viewed this form's exact `run/layout_review/grt/density.png` after unit `3167391-1795383859` exited zero. The eight cells above 90% demand are sparse across the otherwise even center. Peak demand is still 100%, with no overflow in either direction or across the whole die by the final congestion report. The original density-0.50 form had 35 cells above 90%. Final setup is +137.56 ps. I cleared the exact density-0.47 checkpoint for isolated detailed routing. The density-0.50 checkpoint remains held.

The reviewed x_hc1_st_b form also finished with minimal-profile physical SIGNED, TT +142.53 ps, DRC and antenna zero, and 1,037 face checks passing. Its exact routed-netlist LEC proved 4,622 of 4,622, zero differences or undecided, unit 3226099 exit zero. Parent FF hold remains conditional.
