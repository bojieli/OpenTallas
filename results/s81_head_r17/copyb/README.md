# HEAD-CORE-R17 copy-B burst FIFO: production depth from the static schedule (COORD ruling 5 on HEAD-CORE-R15)

Ruling HEAD-RTL-4 (10-26 22:59): depth plan-computed from the WORST-CASE replay stall of the production link protocol
(max retries x replay length), not the bench spacing; keep 7 until computed, then freeze with the HEAD plan.

## Bound (tools/s81_head/mesh_bq_bound.py --protocol T; bound.txt)
- Lane endpoint = ot_s81ph_link_ep_safe4 inside dsfd_coll_lane_w_safe8_ntf (CH_BOARD 700, REACH 2: TX_STAGES 2, PIPE 2,
  RX_STAGES 5, KEEPALIVE 16, MAX_RETRY 8 default); hd_mesh straps CH_B 2'b11 = board ACK timeout on both lanes.
- ATOB = RTTB + 2 KEEPALIVE + 32 = (2*700 + 2 + 4 + 5 + 6) + 64 = 1,481 cycles.  With no ACK/NAK the sender rewinds once
  per ATOB; the 9th rewind without progress is retry_exh = link fault.  Worst non-fault stall S = 8 x 1,481 = 11,848.
  NAK rewinds come after ~RTTB < ATOB and only shorten S; a new error episode restarts the retry count at progress.
- Static schedule: positions >= 8,357 cycles apart (ot_s81hd_tile.sv; 8,411 at the default CUT) -> one record per peer
  per T.  Replay window N = floor(S/T) + 1 = 2 (3 would need S >= 16,714; margin 4,866 cycles).
- Worst case for copy B: the same stall on lane a (common mode); both bursts land on the same edges and copy A has
  priority on the word port, so copy B holds both records before its first read -> BQ = N = 2.

## Bench (tools/s81_head/mesh_ep_burst_bench.sh, rtl/dsrom_sys/s81_head/test/tb_s81hd_mesh_ep_burst.sv)
Verilator 5.050 on intel2 (systemd scope MemoryMax 24G). Records every T = 8,357 both directions; lane-b blackout window
W: X->Y data payload (beat bits 143:56) AND Y->X reverse frames (bits 55:3 = ACK/NAK for X's sender) corrupted every beat.
- Sweep W 9,000..14,500 (BQ 32): largest W without link fault = 11,910: timeouts 8, replays 8, copy-B extra latency
  S = 11,848 = 8 x ATOB exactly (CHECKED: measured = formula); peak copy-B occupancy 2.  W 11,920: 9th timeout -> link
  fault (protocol limit, expected).
- W 11,910 lane b only: BQ 2 PASS; BQ 1 also passes (copy A idle, the port reads each B record as it lands) -> info only.
- W 11,910 +BOTH (common mode): BQ 2 PASS (5/5 records x 2 copies exact, no fault, peak A 2 / B 2); MUTANT BQ - 1 = 1
  FAILS: copy B record 3 lost (4/5), Y ep_fault[10] (0x400) set.  W 0: BQ 2 PASS, latency 40.
- MESH_EP_BURST_BENCH rc=0 (bench.txt, sweep.txt).

## RTL
ot_s81hd_mesh_ep_core.sv: comments only (derivation); parameter BQ default stays 7 (7 >= 2: 7 is not an overflow bug), so
no behaviour or cycle change.  ASK: the HEAD PLAN-DELTA sets BQ = 2 on the 3 hd_mesh instances (2 x 5 x 97 = 970 data
flops fewer per endpoint, UNCHECKED area).  Cycles unchanged at any BQ (same 3 edges; depth only).
