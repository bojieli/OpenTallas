# dscoll_lane_e_s8 -- S81-COLL lane tile, REACH=2 = s7 hops + RX FIFO write landing (DRIVE-S81-COLL, S81.STA.LKTO.2, 10-20)

Top `dsfd_coll_lane_e_safe8` = ot_s81ph_coll_lane_safe4 REACH=2 (defines OT_COLL_NATIVE32 + _OFF, v8), CH_BOARD 700.
Generator results/rtl/s81_coll_native32_1020/kit_s8/gen_s8_specs.py (base = the s7 spec: outline 725.76 x 583.2, macro map,
pins, PDN, layer contract unchanged). Clock: TritonCTS sink-clustered tree (as s7). Parallel structural fallback of the running s7 routes
(owner 10-19 PARALLEL: bind whichever closes first under the checklist).

## Why (s7 reach audit)
- s7 E gate ODB GRT native reach audit (scratch/s81-tilesf/reach_e_s7): FAIL 5,379 pairs > 405 um, max 765 um. 4.8k = ONE cone:
  u_ep c_diff (1800+1620+700), c_crc_ok (412), xp_v (412) -> g_fifo_safe g_address[].count_r / wp_r and u_m g_slice[].valid_r.
  The receive decision sits by the gearbox (link face); the 18 RX FIFO groups sit beside their banks at the core face.
- W s7 gate placement TT reg->reg -246.3 ps at u_ep.g_fifo_safe.g_address[5].wp_r (same cone).
- The REACH=1 frame hops did not move the decision cone (placer keeps exp_seq / d_q by the gearbox).

## RTL delta (REACH=2 = REACH 1 + ot_s81ph_link_ep_safe4 WRL=2; WRL=0 = unchanged safe4/safe7 netlist)
- c_acc -> 3 kept copies (ot_s81ph_kff4_1, edge 1, one per 6 groups) -> 18 per-group kept copies (edge 2, each on its own
  group reset leaf, beside its banks) = the group write enable; write data {last,data} 2 reset-free stages into u_m.
- Logical occupancy fill (c_full, overflow fault) still counts c_acc at once; physical occupancy fillw / tail / drain count the
  landed write acc_p (= c_acc + 2 edges), so a read never precedes its landed write (OLD-read forwarding unchanged).
- New endpoint reset leaf rst_v[RN-1] (EP_RN 16 -> 17): 3 + 2 kept copies + fillw 10 + ok_f3 = 16 reset pins.
- Sim checks: group state == central (tail, head, fillw, out_valid, acc_p, drain); 0 <= fill - fillw <= 2; every landed copy == acc_p.
- Bench tools/xdie_s81/coll_reach7.sh with OT_COLL_REACH8=1 (tb_coll_reach7, DUT pair = safe8): m0 PASS; m5/m6/m7 (s7 hop mutants)
  and m8 (group 0 landed write copy never fires) FAIL. Shared safe4 mutants m1-m4 stay on tb_coll_safe4_boundary (v8 witnesses).

## SAFE-DESIGN checklist (owner 10-19) + pre-gate native census
1 Pins: PASS -- unchanged s7 (rx 2 landing flops; lo 2 incl. credit-rx landing); reset_landing 2 stages.
2 Reach: FIXED -- decision -> FIFO groups is now 3 registered segments (decision, 3 mid copies, 18 group copies); data 2 stages.
  Verified by the post-GRT native reach audit on this gate's ODB (owed).
3 Fanout: c_acc +4 kept loads; each mid copy 6 loads; each group copy 1 + its group (wp_r/count_r logic, u_m slice valid);
  pre-gate native census (limit 32) runs first in the gate.
4 Depth: decision cone ends at a flop pair now (was c_diff -> compare -> count_r/wp_r adder in one cycle).
5 Storage: unchanged 55 bank64 SRAMs; +1,106 reset-free data-stage flops (payload in flight, not storage).
6 Floorplan: unchanged s7/s6c (lattice, channels, aspect 1.24, pins <= 3.6/um on full W/E faces).
7 Clock: as above; pin-flop spread judged by the --cts gate (TT/FF <= 80 within the region); io_hold_margin 0.03.
8 Schedule: off-die link boundary (elastic by owner rule 10-14). Added edges vs s7: link->core +2 (write landing), credit return +2
  (freed counts drains). Measured mean lo->li latency: bench m0 log COLL_REACH7_STATS (ref4 vs safe8) -> collective ledger.
