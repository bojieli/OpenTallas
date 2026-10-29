# hd_tile ONE canonical PLACE (DIE-HEAD-24 tile_place1, epyc2 ot-run oth-ubuntu-3831005): post-DPL checks by DIE-HEAD-25, 2026-10-29

ODB: epyc2:/srv/opentallas-scratch2/claude/die-head-24/tile_place1/hd_tile/run/results/asap7/dp_hd_tile/base/3_place.odb
(gen6 kit, PLACE_DENSITY 0.5, outline 708.48x1036.8). Checks are my own runs, marked CHECKED in the lane line.

- DPL: legal (negotiation legalizer). Max displacement 157.6 um, average 0.6 um, HPWL +1%. 2951 OT_CLAND packed cells kept FIRM.
- AUTO-GEOM (geom_check.sh standalone --all-kits --outline 708.48x1036.8): FAIL. Result in auto_geom.json and the image auto_geom.png
  (personally viewed).
  - GRT0 over M2-M7 at 50 iterations (converged in iteration 2). 0 cells on macros. Fill is INFO (macro-dominated, 66.7%).
  - r2r: 15 captures > 405 um, max 418.99 (u_b.res_bits -> c_rb).
  - pin_reg_max 154.34 (cland_tstart_in), against the 150 backstop.
  - pin_unreg 570 = i[564:0] + cland_dn_fault_i/dn_ready_i/fstart_in_i + fclk_out_o. The 565 i bits feed the count-aligned landing
    ring's write-enable AND2 (u_cland_i, by design under 12.16a); they are not unregistered pins. fclk_out_o is the forwarded clock.
  - clock_reach 893 um: pre-CTS, no clock cells are placed yet.
  - channel_h est 1.288 at the E end of the horizontal street, but GRT shows 0 overflow there.
- Net reach census (reach/reach.tcl, every signal net driver -> farthest sink, Manhattan, placed pins): 73,463 nets, 0 signal nets > 405 um.
  The only net over 405 is clk (962.6 um, pre-CTS). This covers the 12 private reset exports and all data nets.
- Fix variants for r2r/pin_reg_max (12.17-3), PLACE only from the same kit: PLACE_DENSITY 0.60 and 0.70
  (epyc2 die-head-25/tile_pd60, tile_pd70).
