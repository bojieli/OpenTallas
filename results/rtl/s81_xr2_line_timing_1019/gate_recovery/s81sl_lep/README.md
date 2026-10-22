# s81sl_lep (ot_s81sl_lep) -- S81-SAFE-FIX/LEP regen 10-19

History: route s81sl_lep-90fc20580 failed; its COMBO ECO (TT -44.76 / FF -7.60) is a squeeze and is SUPERSEDED (never
submit/merge it). Fail class = lepnh 90fc20580: lane-1 TX SRAM rd_out (clk->q 421 ps) -> forward mux -> wire across the
lane-0 column -> lo1_d pin flop (distance), plus in->reg -19.4. >1 failed route/ECO -> COORD review before submit.

Fix: RTL = S81-FIX3 40686fe1c ot_s81sl_lep_core TXRP 1 (read register beside each TX SRAM column; lo_v/lo_d +1 edge,
credit round trip ~8 <= CRED 8, full rate). Kit = c12b5663c (432 x 432, km16 regional clock roots, pin_reg_split,
pin_ranges l*_f/l*_st W-top + f_lf N-west, reset_landing 2) + hold_margin 0.045 + io_hold_margin 0.03.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every port lands in / leaves an RTL pin flop (source-registered; pin_reg_split = one launch flop per
  output pin, kept); reset_landing 2 stages (rst_n__ot_rl0 -> rl1 wrapper, OT_RST_LAND=1) then ot_rst_relay 4 regions.
2 Reach: fixed -- TXRP register sits beside each TX SRAM column, so no SRAM->lo pin-flop path crosses the lane-0 column
  in one cycle; f_lf flop at the NW corner beside its inputs (pin_ranges). Gate wire_reach lint must stay clean.
3 Fanout: PASS -- lo*_r credit pulses land in one pin flop each (was 556 loads), RX 16 replicated read pointers, reset via
  relay regions; gate high_fanout lint is a REFUSE rule.
4 Depth: PASS -- TX read now a registered stage; no combinational in->out (gate boundary lint).
5 Storage: PASS -- 2 x 5 ot_sram_1r1w_512x128 landing / TX arrays; no runtime-indexed flop arrays > 2 kb.
6 Floorplan: PASS / waived util -- 432 x 432 (1:1), 10 SRAM on the lattice (place.tcl) in two centred columns, 20-um W/E
  std-cell bands, W/E faces 5.3 pins/um (<= 6). Fill ~33% (std util ~9%) WAIVED: pin-bound (5,307 signal pins); the
  388.8 outline at 5.9/um diverged (gate 3eb62a102).
7 Clock: PASS -- 16 k-means regional roots (clock_split_km.tcl); prior 432 gate spread TT 65.0 / FF 66.5 (<= 80);
  insertion 667 ps TT is guidance (boundary by parent compensation); io_hold_margin 0.03 (was 0.025).
8 Schedule: static (credit lanes are the die's fixed-latency collective lanes). Added: TXRP +1 lo edge on both lanes,
  reset release +2 -> lanes/MU-DIE-S81.md INBOX (land plan E / calendar / token pricer).
