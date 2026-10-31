# DIE-HEAD-50 HEAD plan event l48c (10-31)

l48c = l48b (l48a hd_st_m status-stage sites + k5 reset copies; l47v hd_st_turn taps; k5 +7 / n4 +5 density clock taps)
+ the forwarded-clock sender fix on every exporter (COORD l47u exception item (4)):
- make_l48c.py: each fclk_out export takes source_clock_port = the nearest planned physical tap (schema.tap_grid,
  exporters_l48b_grid.json) instead of the root clk, and the type gets landing_contract.forwarded_clock_only_inputs.
  21 types / 58 exports changed (l48c_report.json). hd_lep0N has only clk in its tap grid -> unchanged (sender UNMEASURED);
  hd_serdes nearest = clk -> unchanged.
- die clock.ring_hold.sender_ps = 80 (main 45fcec53464 ring_hold contract). Measured sender data_min - fclk_max at the
  sender ports, kit RC, FF: hd_turn_a +115.9, hd_st_m rx_o +95.0 / tx_o +96.3 (TT +149.2 hd_turn_a).
- fix_rrt.py: rr_t<i> reset-tree net remap by tap name after the clock-tap insert (hd_st_k5 47->54); hd_st_n4
  rst_start_raw_7 net rst_n_t48 -> rr_t48 by hand.
- add_top_taps.py: wires the new k5 clk_t29-35 / n4 clk_t26-30 inputs to the instance region clock in
  s81_head_top_l48c.sv (as DIE-HEAD-48 did for hd_st_turn).

Checks (intel2 /srv/opentallas-scratch2/claude/die-head-48): RTL regen p2 rc 0 on all 21 types; G0C --completeness 1 ERROR
(SerDes native release PENDING, same as l48a on the same tools, 0 new); strict die port-bind HEAD_DIE_PORTBIND_SOURCE PASS;
die clock ot_clk kit + combo GRT TT/FF overflow 0; die STA (12.25 form) setup TT +201.62, CA worst lo TT +141.5 / FF +175.8.
sha256(source_plan_l48c.json) = 963ed82fd2ac23573e27431103417074f5ab6f4cb0f4ef6a63ee4387a7b5a179
