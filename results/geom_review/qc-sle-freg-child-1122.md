# SLE cws1 FREG child, November 22 placement review

I viewed the actual layout and density for `sle_cland_w517_n_s10_freg`. The fixed 88.992 by 51.84 µm footprint has no macros, 45% utilization and a 0.334 maximum M5 pin-track fraction. The north input and south output rows are continuous. The density is spread across the interior with small low-density gaps. The only geometry flags are `rst_xn[6]` and `[2]`, whose first reader groups are approximately 52.7 and 65.0 µm from their south-face inputs. The clock-entry distances are 22.19 µm on `fclk` and 11.68 µm on `clk`.

This geometry is accepted for an isolated CTS proof. The fresh build passed stock face checking for all 1,037 signal bits, with no missing or extra pins. Pre-place LEC proved all 4,737 compare points. A separate netlist check proved all 517 data inputs and the forwarded start each enter one direct `fclk` face-register D pin. CTS timing and parent boundary qualification are pending.

Placed unit `2086136-1795382235`, exit 0. Exact kit `epyc10:/srv/opentallas-scratch2/claude/QC-SLE-R5/freg_hard_children/sle_cland_w517_n_s10_freg/registered_face/kits/sle_cland_w517_n_s10_freg_synth0`. Reviewed `run/layout_review/place/{layout.png,density.png,smells.json}`.

## Sibling placements

I also viewed the exact `sle_cland_w517_n_s10_1_freg` and `sle_cland_w517_n_s10_2_freg` output density plots. Both have the same fixed outline, cell distribution across the center, continuous north and south pin rows, and a 0.334 M5 pin-track fraction. The only flagged legs are `rst_xn[6]` and `rst_xn[2]`, at 47.74 and 65.49 µm for the x_hc1_st_b child and 51.83 and 65.70 µm for the cws2 child. The admitted placement units `2288732-1795382547` and `2289172-1795382547` both exited zero. The geometry supports an isolated GRT timing proof for each.

Exact images are under `epyc10:/srv/opentallas-scratch2/claude/QC-SLE-R5/freg_hard_children/<master>/registered_face/kits/<master>_synth0/run/layout_review/place/density.png`.
