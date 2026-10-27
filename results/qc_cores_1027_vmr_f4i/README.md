# QC-CORES-2: qfd_dv_s8x_vmr F4I, a pin-access keep-out at the PG stripe pairs (2026-10-27)

## Root cause of the F4H DRT stall
- **The stall.** The F4H signal DRT (epyc2 unit oth-ubuntu-3601087-1793095695) has stayed at 1 violation from it11 to beyond it52, always the same marker.
  - The marker is an M3 spacing error: net2171 against a VSS pad at (118.749-118.764, 15.643-15.677).
  - net2171 is pin A2 of AO22 `_10830_` at x 118.799-118.836.
  - That job is left running as data.
- **Geometry (CHECKED, `pa_hot.py` / probe on the F4H 3_place ODB).**
  - Every M5 VSS/VDD stripe pair (pitch 4.32) drops M2-M5 via stacks at every rail.
  - Their M3 pads are 0.09 x 0.028 um: VSS at x 118.659-118.749, VDD at x 118.851-118.941.
  - That leaves an M3 escape gap of only 0.102 um, and the pads repeat every 0.54 um in y.
  - A2 sits inside that gap.
- **Exposure (CHECKED).**
  - 2439 cells (3528 pins) have a signal pin within 0.05 um of a pad.
  - 2951 cells (5706 pins) are within 0.1 um.
  - The marker cell is in both sets.
  - So the cell is not unusual. The pinched gap is a structural hot spot at every stripe pair.

## Fix (plan-level, every stripe pair)
- **Band list.** `pa_bands.py` reads the PDN in 2_floorplan.odb and makes one band per stripe pair.
  - The band covers the pad-to-pad gap, widened by half an M3 width and snapped to sites.
  - Result: 56 bands x 0.216 um = 12.096 of 241.92 um of core width (**5.00 %** of row sites, CHECKED).
  - Std-cell utilisation is 9.2 %, so the area is not a constraint.
- **Placement hook.** `pre_gpl_f4i.tcl` runs after the unchanged MIF0 hook.
  - It turns each band into hard placement blockages.
  - Each band is cut in y only around cells that stay fixed through DPL: LOCKED tapcells and FIRM `ot_ms_*` / `ot_isl*` plan clock cells.
- **Tries.**
  - try1: uncut bands. DPL-0033 failed on 1106 tapcells plus 3 `ot_ms_TR*_nd` nodes.
  - try2: bands cut around face flops. That left 997 movable cells in the cuts, and the run was stopped.
  - try3 3_place gate: 61 blockages, 0 movable overlap, 0 movable cells in band x-ranges (CHECKED, `pa_check.py`).
- **Render.** `f4i_place.png` was viewed.
  - The bands are centred on the pad columns.
  - `_10830_` moved to x 121.
- **Rest of the recipe, unchanged (`f4i_chain.sh`):**
  - F4F CTS (mscts_spec_f4f), then GRT, then FF data-hold (`hold_grt_f4a.tcl`, margin 15).
  - F4G guides, then a clock-first route with a B1 DRC 0 gate.
  - F4H single signal DRT: only the tree nets are locked, and the leaves re-route.
  - Then finish, RCX, abstract, meas, `signoff.py` and `lec.py`.
- **Kit location.** epyc2:/srv/opentallas-scratch2/claude/qccores1-1027/kits/qfd_dv_s8x_vmr_f4i
- **Note.** The keep-out removes sites. It is not a clock or timing edit.
