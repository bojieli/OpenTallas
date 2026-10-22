# qkd_ahub_sdb -- attention hub with BOOT-PROGRAMMABLE AP_OFS / FR_OFS (KV-ATTN4 10-20, COORD 09:56 decision (b))

Top `qkd_ahub_static_dw_bo` (rtl/hdc/nearhbm/qkd_ahub_static_dw_bo.sv) = the CLOSED a7 hub `qkd_ahub_static_dw`
(job qkd_ahub_sdw-a7-c6c412b4c, CLOSED TT +8.48 / FF +8.83, DRC 0) with module names _bo and two new static inputs:
* `ofs_ap[31:0]`: AP_OFS of stack s = ofs_ap[8 s +: 8] (two's complement, sign-extended to 16 b);
* `ofs_fr[7:0]`: FR_OFS (two's complement).
Both land in u_io pin flops and replace the elaborated constants in the SAME adders (cal LMAX_IN / Z_IN, export target),
so hub latency, slots and every edge are unchanged (0 cycles).  Contract: static from before rst_n release; the die
may carry them over any number of relay stages (no timing relation).  Supplied by the boot image / kv_static_params
(today AP [-40,-40,-38,-39] / FR -7; a7 was hardened at [-36,-36,-34,-35] / -7) -> the hub is built once (AHUB_OFS_BOUND).
Pins: ofs_ap N 304.0-336.0, ofs_fr N 336.0-344.0 (free N window between rst_n and ck); everything else = a7.

## Bench (Verilator 5.050, fleet): tools/qwen_kv_die/ahub_static_dw_bo_bench.sh
a7 s4o lockstep vs the sealed hub, offsets on the boot pins: m0 PASS; m8 (a4 boot values {2}/0), m9 (FR+1), m10 (AP[ES]+1)
FAIL = the boot pins are causal; m1..m7, m11, m12 FAIL as a7.  Witnesses results/rtl/kv_ahub_bo_1020/mut*.log.

## Safe-design checklist (a7 accepted geometry, COORD 17:00; deltas only)
1 Pins: PASS -- the 40 new inputs land in pin flops (u_io); all other pins as a7.
2 Reach: as a7 (one registered relay per >405 um leg); ofs pins sit beside u_io on the N face.
3 Fanout: ofs flops drive 8 adders each (<= 32); in-gate native census reports the rest.
4 Depth: constant add -> variable 16-b add on the same pin-flop operands (~+2-3 levels on the hub_cal / tgt cones).
5 Storage: unchanged (no new storage).
6 Floorplan: a7 outline 734.4 x 540, closed Z-tree / reciprocal children on the a7 lattice positions.
7 Clock: as a7 (spine to child pins; one region). io_hold_margin as a7.
8 Schedule: static, 0 cycles; offsets are boot data (kv_static_params), no flow control.
