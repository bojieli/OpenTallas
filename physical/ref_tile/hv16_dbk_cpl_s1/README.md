# hv16_dbk_cpl_s1 (L2H-HC 10-19, H.STA.BLK.12)
Successor of hv16_dbk_cpl (65c2387ab NEEDS_RTL TT -12.30 / FF +20.59 / DRC 1; 2b44fa775 TT -32.43).
Classified paths (route w18_sta_tt): u_control/bank_read_addr[166] -> L[5].read_addr -12.30 and bank_write_slot -> L[2] -11.73
(macro->macro, ~457 um U-turn / one-face star), L[4].wd -> wd port -7.63 (macro->out); DRC 1 = parent M4 wire inside a bank OBS pocket.
Structural fix in place (HH-7 3d37f28ac on main): per-bank-group controller copies on the face of the group they serve (worst leg ~343 um),
column-0 wd order, child_pocket_guard. This kit binds the CLOSED rt80 controller (RR_RT 80, the d4g round-trip budget).

## SAFE-DESIGN checklist
1 Pins: PASS - children own their pin flops (bank/controller/collar); parent = wires + reset relays; reset_landing 2 stages on clk_rst.
2 Reach: FIXED - worst controller->bank leg ~343 um (< 405) after per-face copies; wd column order fixed. HBM-DMABACK 10-19: gate 163741 FAIL mv_src/mv_done/mv_fault controller->E-face-top 544-547 um (pins at y 535-538, controller at y 259-328) -> the three pins moved beside busy/quiet/stk at the controller row (E y 320.8/322.4/324.0, ~280 um), wires only, 0 cycles. Gate GRT_RC=1 was infra (ot-epyc8 "No space left on device"); measured GRT overflow 0 on M2-M6.
3 Fanout: PASS - parent has no datapath registers; reset via ot_rst_relay copies (u_rst_bk 9 regions).
4 Depth: PASS - wires only between child pin flops (child clk->q ~310 ps + ~350 ps wire).
5 Storage: PASS - storage in bank SRAMs (hard children).
6 Floorplan: PASS - children on the 43.2 lattice, 606.96x542.16 (1.12:1), one std band; WARN: rr/wd/clk_bank faces left ANY (die contract pins).
7 Clock: hybrid entries per child (landed die clocks), gate spread 68.9/67.7 <= 80; io_hold_margin 0.03.
8 Schedule: static; 0 cycles added; RR_RT 80 is the compiled d4g round trip (dma_min_drain_lag rule).
