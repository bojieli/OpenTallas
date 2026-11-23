# VIS-QC fork: fe/fw + misc structural forms (11-23 00:2x PST)

Renders are in visqc/fefw/<tag>.vq.png. Each shows GRT overflow from the latest congestion*.rpt plus taps (red means more than 1000 sinks), and station/pad/landing flops at their placed positions (ot_face_flops). The kit layout_review PNGs were read too: fw1a place layout and density, hc1a density, glue density, and fw3/stm1 grt congestion.png. Kit paths are in visqc/fefw/kits.txt.

## What I saw (fe/fw strips, 622 x 1832 um, no hard macros)
- **East fw (sle_fw_v1 cl9d029624, sle_fw_v2 cl69f5e854):**
  - The whole GRT overflow (V 24-27k at it5) sits in two 10-um-wide vertical columns at x 260-275 and x 335-350, y 590-720.
  - These are the x_fe_o, x_fe_p1_o, x_fe_p2_o and dd_eo station columns. All of them are sited on or next to the die spine (x ~265-345).
  - The lpad_dr_ei and lpad_x_fe_p1_i pad rows cross them at y ~710.
  - The worst spine taps sit exactly on that crossing: t41 has 5540 sinks at (315,705) and t39 has 7133 at (315,715). t25, t43 and t28 (3-4.7k) are on the same x=315 column.
  - Cell density elsewhere is below 0.3. The die is empty and the demand is stacked.
- **Do over-cap taps coincide with congestion?** YES on east fw: the worst tap is at the hotspot centre.
  - On slw_fe_v2 clf110fab2, GRT converged (ovf 7/1), but 12 of its 40 over-cap taps cluster at x 230-360, y 720-1010. That is the same spine station column (x_stm_o / st_eo / x_fw_o at x ~310), and GRT usage there is 100%.
  - Tap load follows the flops, so over-cap taps are a symptom of station columns stacked on the spine. The "tap-site legality" block on the residual taps goes away if the flops move off the spine.
- **West fw:**
  - slw_fw_v1 cl592e3d37 is mild: ovf 169/75 at (300,650-700), on the same spine.
  - slw_fw_v3 passed GRT, but routing usage is 75-80% across the whole die, with the spine at x ~300, y 350-1100 hot. DRT iteration 0 has 305k violations.
  - Cell counts are 426-503k at place and 520-590k after repair. That is above the ~400k guidance on every fw/fe type.
- **sle_stm_v1:** a macro channel (4 SRAMs top-left; channel at (246,1614-1638) at 100%) plus routing usage of about 75% across the die. DRT iteration 0 has 194k violations.

## VISQC-FEFW-1 (one form for fw_east, fw_west, fe_west; 0 cycles unless a leg exceeds 405 um)
1. **De-stack the spine.**
   - Re-site the station and pad columns of the N-S buses so that no two buses share an 80-um x band and none sits within 40 um of the spine tap column x=315.
   - East fw: x_fe_o -> x 150, x_fe_p1_o -> x 230, x_fe_p2_o -> x 400, dd_eo -> x 480. West fe: x_stm_o / st_eo / x_fw_o similarly at x 150 / 400 / 480.
   - Move the lpad_dr_ei / lpad_x_fe_p1_i rows (y ~710) at least 60 um off the corridor block, toward their landing side.
   - Lateral moves are at most 170 um, once per bus. Any placed hop over 405 um gets +1 station (pre-approved).
2. **Taps.** After step 1, re-run the sink-bin tap split (TAP-GRID-R5 sink_bins_from_place) on the probe placement. Expected result: the spine taps drop below 1000 because their flops have moved. Residual taps go on the new corridor columns, which are legal open-row sites.
3. **Strip width.**
   - fw/fe strips are wire-dominated: routing usage is 75-80% at cell density below 0.3, and there are more than 400k cells.
   - Grow the strip width 622 -> 778 um (+25% tracks, pre-approved). This is a die-level change for the QC plan lane, because it moves strip abutment.
   - Alternative: split slw_fw_v3 and sle_fw_v1/v2 into N and S halves, each about 250k cells.
   - Pick growth if the die floorplan has room; otherwise split.
4. **V4 status.** V4 does NOT address this.
   - FEFW V4 lever3 rows add stations (+2 on l9_wi->x_st_a_o, +1 on x_fe_p1_i->ch_dn_o) for setup.
   - L1 has the clf110fab2 arv_ei/arm_ei stations.
   - V5c splits taps only on clf110fab2. None of these move columns off the spine.
   - Carry VISQC-FEFW-1 as a V5/next-event row on top of the lever3 stations. Site the new lever3 stations in the de-stacked corridors.
5. **Fast probe.**
   - Fork V4 L0 bound tree, apply the site rows on sle_fw_v2 cl69f5e854 (worst: 10.4k gcells over 90%).
   - Run place plus a quick GRT (geom_check GRT, 10 iterations).
   - Re-render with vq_extract/vq_render and READ it.
   - PASS means: no 10-um column with V-ovf over 50 in (250-350, 590-720); spine taps at or below 1000; GRT usage over 90% below 2k gcells.
   - Then run one sealed --goal route kit and one OT_PROBE_THROUGH=1 kit on sle_fw_v2 cl69f5e854.

## VISQC-MISC-1 sle_stm_v1 clbe630b9c
- Widen the SRAM row gap at (246,1614-1638) to at least 30 um by moving the lower SRAM pair 20 um south.
- Give the stm strip the same width growth as FEFW-1 step 3: usage is about 75% across the die and there are 535k cells.
- The kit is in DRT now; let it run. The form is for the next event.

## VISQC-MISC-2 sle_ctl cla4f6f12f
- Over-cap taps sit in and around the u_tap / u_ctl slit: t193 has 9752 sinks, t170 6791, t121 6684.
- The existing SLWSLE lever-3 rows (rows_v2b: u_tap off the slit, b_hw stations core-free) are the right form. They were dropped from V4 because of 13 G0 errors on V3 geometry.
- Rebase them on V4 L0 and add sink-bin taps on the probe placement.
- Probe: place + GRT. PASS means no tap over 1000 at the slit and GRT ovf in (350-650, 300-600) below 100.

## Others
- **glue:** the row is CB-R4's +21 taps and 146 ROM rows (replay: max 1000 sinks, 0 over-cap). It still needs a placed probe; status PRE-PASS.
- **sle_hc1 pve230954c / pve289215f, native59, tt_ctlm:** NONE-NEEDED. They are running and progressing, and hc1 has signed siblings with the same form.

## Family status for OPUS-FIX-QC-V4-R2
- fe/fw: FEFW-1 DRAFT, not in V4. The V4 fe/fw station rows are fine to apply; they neither cause nor fix the spine stacking.
- hc1 / native59 / tt_ctlm: NONE-NEEDED.
- stm_v1 and ctl: DRAFT.
- glue: PRE-PASS (CB-R4).
