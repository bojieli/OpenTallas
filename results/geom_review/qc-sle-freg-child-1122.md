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
