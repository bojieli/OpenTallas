# hv16_dbk_cpl_l1b (HBM-HC7-DBK 10-20, H.STA.BLK.12) -- PARALLEL FALLBACK of hv16_dbk_cpl_l1: same RTL, pins and stations, child halo 10.8 um
Master: `ot_hgi_dma_back_static_vp4_banks_cpl` (rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks_cpl.sv),
same ports as `_cp`, same children (8 landing banks, CLOSED rt80 controller, collar leaf), same floorplan as s1.
Fallback in parallel: hv16_dbk_cpl_l1b (identical, child halo 10.8 um).

Why: Codex 04:04 REVIEW REFUSED s1/s2 @ca6707526 on exact post-GRT buffer-transparent reach (11 captures > 405 um:
rr[2055] valid W face -> bank7.write_en 713.3, rr valid -> bank2/bank6 566.1/540.8, controller bank_output_en[7] /
bank_read_en[7] -> bank7 454.7/408.2, reset landing E y 2.4 -> u_rst_bk leaves 456.4).  Evidence: codex/hbm-dbkcpl-review-1020
9589117b1 (reach runner results/arch/hbm_dbkcpl_review_1020/sequential_reach.py, re-used post-GRT on this kit).

## Structure (one failed review = structural redesign)
* rr landing: every rr bit -> kept clk_land[b] register at its face (io_flop_at_pins); valid bit landed twice: wv_q half way
  port -> bank write_en, cv_q half way port -> controller rr_valid_i.  rr valid ports moved beside each bank
  (results/arch/hbm_dbkcpl_land_1020/make_pins.py: W y 130.8/150.0/260.3/389.9/519.4, S x 446.1, N x 273.4/446.1).
* read path: bank_read_en / output_en / read slot / read address relayed one edge per bank (kept), half way between the
  controller face pin and the bank pin.  write_slot NOT relayed (write frame = controller frame); bank 5 takes the W copy.
* wb_fill_start / wb_fill_bank / wb_fill_epoch relayed one edge with wd (half way controller N face -> wb ports).
* reset: rst_n port E y 195 (beside clk_rst); rl0 at the pin, rl1 + u_rst_bk sync pair at the centre station (380, 215-225),
  collar leaf in the controller|collar channel (420, 262), u_rst_ctl chain at (345, 250), bank leaves half way to their
  bank rst_n pin.  Release edges unchanged (ot_rst_relay REGIONS 9 / 1).
* Stations: results/arch/hbm_dbkcpl_land_1020/relay_anchor_l1.txt (+ relay_anchor_post_l1.txt for wv_q/cv_q, after io_flop_at_pins), placed FIRM by physical/common_flow/relay_anchor.tcl (+ _post.tcl)
  (pin_hook_before_flops, before io_flop_at_pins; anchor_row_packing legalises), released before DPL.

## Cycles (static; handed to the die schedule, lanes/HBM-HC7-DBK.md)
rr at the parent port -1 edge (die pads every rr lane to RR_RT-1 = 79 at the port; GEN2c worst lane round trip 72 fits);
wd and wb_fill_* +1 edge at the ports (every DMA-back drain completes one edge later: +1 cycle per KVWB move, < 0.01 %
tok/s); controller frame (RR_RT 80, rq, mv_src/done/fault, quiet, busy, wb_reserve_*) unchanged; reset release unchanged.

## Benches (Verilator 5.050, ot-epyc9; witnesses results/rtl/ref_tile/hv16_dbk_cpl_l1/witness/)
fold: CPL_LAND PASS commands=7 beats=2769 (lockstep vs the die composition through the real host ingress, rr -1 / wd,fill +1).
banklat: BANKLAT_RL PASS RR_RT_die=80 die_pre=1 beats=2889 (d4g faces bank + GEN2c NE lanes, every landing slot through the SRAMs).
Mutants FAIL: controller valid unlanded (mv_fault), write slot relayed (landing payload), fill unrelayed (lockstep),
die not re-padded (mv_fault), reset-latency (cycle did not advance).

## SAFE-DESIGN checklist
1 Pins: FIXED - rr landed at its face in RTL (2,056 + 8 kept copies on clk_rst); wd/rq/host bus/status are child pin flops;
  reset lands 2 stages at the E face (reset_landing) then the regional relays.
2 Reach: FIXED - planned single-cycle legs (die coordinates, fixed pins): rr valid port -> wv_q -> write_en <= ~140 um,
  port -> cv_q -> rr_valid_i <= 238 + 238 (lane 2), controller -> relay -> bank <= 228 + 228 (output_en[7]), write_slot
  unrelayed <= 383 (bank 5 W copy), rr data landing -> bank rr_data <= ~316, fill relays <= ~165 + 165, rl0 -> rl1 244,
  rl1 / sync -> leaves <= ~305, leaf -> bank rst_n <= ~305.  MEASURED post-GRT with Codex's sequential_reach.py: see gate packet.
3 Fanout: PASS by construction (largest parent driver: rl1 -> 15 async clears; landing copies 1-3 loads); mapped native32
  census at the gate (numbers in the review packet).
4 Depth: PASS - parent = registers + wires; no parent logic between registers except the RL_MUT-0 constant muxes.
5 Storage: PASS - landing storage in the bank SRAMs; parent holds only 1-deep landing / relay registers.
6 Floorplan: PASS (unchanged s1 floorplan) - children on the 43.2 lattice, 606.96 x 542.16 (1.12:1), one std band.
7 Clock: FIXED after gate 20261020-054637 (one clk_rst tree over 2,425 flops: TT insertion 650.7, boundary spread 284.6 > 80):
  eight regional CTS roots clk_land[b] (new die-forwarded ports at the centre of lane b's rr face group) clock bank b's
  landing + read relays (~300 sinks each); clk_rst keeps the reset relays + wb_fill relays (~33); hybrid entries for the children; spread / linked pair TT+FF <= 80 checked by the --cts gate;
  io_hold_margin 0.03.
8 Schedule: static, no credits; every added edge listed above and handed to the die schedule.
