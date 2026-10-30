DIE-HEAD-43 2026-10-30: HEAD one-block plan event l43 (= l40 + 2 one-block deltas, OWNER 12.20 fix-only).
 (1) hd_spn_wshim_tx ft slot link: explicit per-bit station sites (bit_sites_um, stage1 x 349.92 / stage2 x 678.29, each bit
     on its own pin row; event/wtx_sites.py from the l40 kit pin rows). Kit PLACE on main 79ffd79fd: pin_reg_p90 236 -> 21.0,
     r2r 349.5 x0, clock_reach 267.7 -> 179.1 (kits/wshim_tx_s_line.txt, render kits/wshim_tx_s_auto_geom.png).
 (2) hd_spn_wshim_rx clock: sink_bins_file = actual main-clock root register bins of the l40 kit PLACE
     (hd_spn_wshim_rx_actual_root_bins.json, 2417 regs, landing-ring fclk flops excluded), sink_sites_um [] -> est. max
     bin->tap 162 um (was 335.8 with the stale src25p bins). Reset relay re-pick u_rrl_14 -> u_rrl_13 (wshim_rx + top RTL).
 Build: event/edits_l43.json via die-head-40 build_event_stable6 + chain (input_l40). G0C 1 error / 26 warnings = l40, 0 new.
 Die clock rerun l43a405 (head_l40a405 config, plan meta_l43): GRT TT/FF overflow 0 (90679 nets), spread scaled TT 122.3 /
 FF 120.1, OCV shared 133.0/129.1, stated 149.8/142.2 (0 > 150), duty 0 outside 45-55, MPW 0.
 landing_c3/: kit landing_placement variant c3 diff (FLOW-10 ASK): wshim_rx r2r 487.6 x45 -> 378.05 x0.
