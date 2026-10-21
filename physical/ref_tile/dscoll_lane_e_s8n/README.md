# dscoll_lane_e_s8n -- MU-die tf-less COLL lane tile, s8 REACH=2 fix (DRIVE-S81-NTF, 10-20)

Top `dsfd_coll_lane_e_safe8_ntf` (rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv) = ot_s81ph_coll_lane_safe4 REACH=2, TF_CLEANUP 1,
CH_BOARD 700, NO parameters and NO tf pin: the successor of dsfd_coll_lane_e_ntf (legacy core, LCR 1) bound by the lepe_mu /
lepw_mu landed parents of the release die. A default-parameter die bind of this module IS this view (die source swap owed:
DRIVE-S81-SLICERTL). Generator results/rtl/s81_coll_native32_1020/kit_s8n/gen_s8n_specs.py (base = dscoll_lane_e_s8 spec; same outline
725.76 x 583.2, macro map, PDN, layer contract; pins minus tf). Clock: TritonCTS sink-clustered tree (as s8).

## RTL / bench
- Core netlist identical to dsfd_coll_lane_e_safe8 (DRIVE-S81-COLL s8): only the top's tf port and parameter list differ.
- Bench tools/xdie_s81/coll_reach7.sh with OT_COLL_REACH8N=1 (tb_coll_reach7, DUT pair = the two _safe8_ntf tops vs the safe4
  reference pair), Verilator 5.050 on the fleet: m0 PASS; m5/m6/m7 (s7 relay-hop mutants) and m8 (group-0 landed FIFO write copy
  never fires) FAIL; witnesses results/rtl/s81_coll_native32_1020/reach8n/bench/m{0,5,6,7,8}.log. Shared safe4 submodule mutants
  m1-m4 stay on tb_coll_safe4_boundary (native_v8 witnesses).

## SAFE-DESIGN checklist (owner 10-19) + pre-gate native census
1 Pins: PASS -- unchanged s7 (rx 2 landing flops; lo 2 incl. credit-rx landing); reset_landing 2 stages.
2 Reach: FIXED -- decision -> FIFO groups is now 3 registered segments (decision, 3 mid copies, 18 group copies); data 2 stages.
  Verified by the post-GRT native reach audit on this gate's ODB (owed).
3 Fanout: c_acc +4 kept loads; each mid copy 6 loads; each group copy 1 + its group (wp_r/count_r logic, u_m slice valid);
  pre-gate native census (limit 32) runs first in the gate.
4 Depth: decision cone ends at a flop pair now (was c_diff -> compare -> count_r/wp_r adder in one cycle).
5 Storage: unchanged 55 bank64 SRAMs; +1,106 reset-free data-stage flops (payload in flight, not storage).
6 Floorplan: unchanged s8 = s7/s6c (lattice, channels, aspect 1.24, pins <= 3.6/um on full W/E faces); pins: route.pin_balance
  group_max 1 (M4 W/E faces) = defined bit order on rx/tx/lo_d/li_d (main-tool pin_order check).
7 Clock: as above; pin-flop spread judged by the --cts gate (TT/FF <= 80 within the region); io_hold_margin 0.03.
8 Schedule: off-die link boundary (elastic by owner rule 10-14). Added edges vs s7: link->core +2 (write landing), credit return +2
  (freed counts drains). Measured mean lo->li latency: bench m0 log COLL_REACH7_STATS (ref4 vs safe8) -> collective ledger.
Census: the gate's pre-gate native census (limit 32, reset nets included) on this kit's mapped netlist; s8 netlist census PASS max 32
(52,133 roots) -- same core. 8 Schedule: +6 lo->li data edges vs the legacy LCR-1 lane (core landing +1, rx landing +1, RX_STAGES +2,
FIFO write landing +2), ACK/credit return +2; handed to the MU calendar (lanes/S81-MUCAL140*.md, DRIVE-S81-NTF).
