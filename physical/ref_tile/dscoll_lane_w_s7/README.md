# dscoll_lane_w_s7 -- S81-COLL lane tile, REACH=1 forwarded relay hops (S81-TILES-E, S81.STA.LKTO.2, 10-20)

Top `dsfd_coll_lane_w_safe7` = ot_s81ph_coll_lane_safe4 REACH=1 (defines OT_COLL_NATIVE32 + _OFF, v8), CH_BOARD 700.
Generator results/rtl/s81_coll_native32_1020/kit_s7/gen_s7_specs.py (base = dscoll_lane_w_s6c spec: outline 725.76 x 583.2,
macro map along the data flow, pins, PDN, layer contract unchanged). Clock: TritonCTS sink-clustered tree (as s6c); s7 / s7k are parallel routes.

## Why (s6c terminal)
- W s6c: clock_rule FAIL TT pin-flop spread 83.9 ps (FF 77.6), 16,342 sinks on one root.
- E s6c: gate WARN, but the actual GRT native reach audit (codex/s81-terminal-collect-1020 coll6_e) FAIL: 5,403 pairs > 405 um,
  max 756.8 um: 5,108 receive control (u_ep c_diff/c_crc_ok/xp_v at the gearbox) -> 18 RX FIFO address groups at the core face;
  194 rx landing -> gearbox; 150 lo_d pin -> credit-rx d_q; 51 misc. One single-cycle cone spanned the tile.
- Note: s6c place.tcl did not source physical/dscoll_cx/coll_s5_cell_band.tcl (README claimed it); s7 keeps the s6c row set.

## RTL delta (REACH=1; REACH=0 = byte-identical v8 safe4 netlist)
- rx landing lr -> lr2 (+1 RX edge); endpoint RX_STAGES 3 -> 5 (+2: forwarded frame hops gearbox -> receive control beside the FIFO);
  reverse ACK/credit frame relay 2 stages endpoint -> gearbox (reset-free, consumed only under lk1); core landing lo_v/lo_d +1 stage.
- Bench tools/xdie_s81/coll_reach7.sh (tb_coll_reach7): safe4 reference pair + safe7 pair, same impairments as the v8 miter
  (CRC windows, blackouts, backpressure, stream reset), transactional in-order/exactly-once/bit-exact scoreboard, credit models,
  equal faults, >= 97% delivered. Mutants 5 (rx flag hop skipped), 6 (core landing data never loads), 7 (reverse relay drops frames)
  must FAIL. Shared safe4 submodule mutants m1-m4 stay on tb_coll_safe4_boundary (v8 witnesses).

## SAFE-DESIGN checklist (owner 10-19) + pre-gate native census
1 Pins: PASS -- every data pin lands in a flop (rx: 2; lo: 2 incl. the credit-rx landing); reset_landing 2 stages.
2 Reach: FIXED -- the receive-control cone is split by 2 forwarded RX hops + 2 reverse relays (gearbox <-> FIFO ~520 um = 3 segments);
  rx / lo pin cones get a second landing flop. Verified by the post-GRT native reach audit (owed on the gate ODB).
3 Fanout: native census runs pre-gate in the gate (limit 32); the new flops add <= 6 reset loads on rr[R_LOC] / 1 on rr[R_CRX].
4 Depth: unchanged v8 cones (540.1 ps / 14 lv); hops are plain registers.
5 Storage: unchanged (55 bank64 SRAMs); +~2.4k relay flops (frame/beat payload in flight, not storage).
6 Floorplan: unchanged s6c (lattice, channels, aspect 1.24, pins <= 3.6/um on full W/E faces).
7 Clock: TritonCTS; pin-flop spread judged by the --cts gate (TT/FF <= 80); io_hold_margin 0.03.
8 Schedule: off-die link boundary (elastic by owner rule 10-14); added edges: core->link +1 (lo landing), link->core +3 (lr2 + 2 RX
  stages), ACK round trip +2 (inside the ACK timeout margin 2*KEEPALIVE+32). Measured mean lo->li latency: see bench m0 log
  (COLL_REACH7_STATS ref4 vs safe7) -> MU.S81.CAL / collective ledger.
