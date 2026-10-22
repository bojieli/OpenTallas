# S81-IDX3R (10-20, MU.BAL.SX.3): non-inline idx3 reader dsdv_idx_rg3 + controller client face dsfd_ctrl_rg3

Design notes, lane sizes, cycle offsets and the die-plan follow-on: lanes/S81-IDX3R.md (takeover dir). In-line
dsdv_idx_rg2 / dsfd_ctrl_rg2 are unchanged (116-frame fallback).

- mk_rg3.py + hdr_rg3.txt: generate rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv from dsdv_idx_rg2.sv (HBM faces only).
- mk_tb3.py: generate test/tb_dsdv_idx_rg3.sv from tb_dsdv_idx_rg2.sv (8 rg3 + 16 dsfd_ctrl_rg3, relay stations
  3/8/13/18 a pair each way, XD 21 W->E chain crossing, slice traffic before + after the window, ctrl status checked).
- bench.sh (fleet, from the shipped tree): ctrl / ctrln / cm1-4 (tb_dsfd_ctrl_rg3_mux), b3 / t0 / sdx / sd0 / m1-m7
  (idxrd3_campaign.sh, Verilator 5.050, split C++ -O1, S81CTRL_NATIVE32), lint.
- native/: synth-only census recipe (rg3 | ctrl3 | ctrl2 baseline), textbook 32 / 405.
- receipts/: campaign logs (.log / .res per case), build heads (Verilator version + source sha256), census json.

Safe-design checklist (dsdv_idx_rg3 = rg2's checklist; the changed faces / dsfd_ctrl_rg3 additions):
 1 pins: lane inputs land in flops, lane outputs leave flops; svc rq / rd paths = rg2 (one 2:1 mux before the pcr pin
   register, rd outputs <= 1 gate after flops); reset: landed regional reset -> 2-level relay forest, control bits only.
 2 reach: the die links get relay stations every 405 um (die plan); nothing inside a tile crosses > 405 um by design.
 3 fanout: census PASS (rg3 0 refusals; ctrl3 adds 0 to the record ctrl's pcr-class refusals); kept copies for selects /
   enables / pointers / decisions, survived synthesis (keep hook).
 4 depth: move = AND of 3 registered flags; accounting registered; rg3 engine unchanged.
 5 storage: rg3 13 SRAM macros as rg2; ctrl landing FIFO 24 x 44 = 1,056 b a PC in a flop ring (< 2 kb).
 6 floorplan: rg3 1036.8 x 1036.8 slot as rg2 (no new macros); ctrl outline unchanged (+3.6k FF, re-kit owed).
 7 clock: single regional clock in each tile; die lanes forwarded-clock relays (die plan).
 8 schedule: static. +s+4 request / +s+1 response edges a pair, +21 W->E chain; priced for MU.S81.CAL.
