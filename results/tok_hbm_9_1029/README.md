# TOK-HBM-9 (2026-10-29): fulltree collect + DIE-HBM-13 cycle prices

## Fulltree (Codex unit oth-ubuntu-201658-1793260539, epyc2) - CHECKED by reading the logs (not by exit code)
/srv/opentallas-scratch2/claude/codex-hbm-token-1028/fulltree/{pre,post}_n{1,6}/run.log
| case | HNX_FUSED | cycles | done | fault | reads | writes | words |
|---|---|---|---|---|---|---|---|
| pre N1 | PASS | 671 | 1 | 0 | 3201 | 640 | 5120 |
| pre N6 | PASS | 1197 | 1 | 0 | 16006 | 3840 | 30720 |
| post N1 | PASS | 376 | 1 | 0 | 3203 | 2560 | 20480 |
| post N6 | PASS | 1016 | 1 | 0 | 19218 | 15360 | 122880 |
Same-binary A-address mutant (pre_n1/mutant_job_a.log): HNX_FUSED FAIL mism=5113 -> CAUGHT.
Scope: archived 32-leaf fulltree bench + OLD f4c_t9p3 station table = component regression only, not C25c/G5.

## Prices (price_die_hbm_13.py, S2 schedule of tools/throughput/accepted_cost.py, ds base 576,702.4 cyc)
Fixed cycles added to EVERY record of the class (upper bound). ds COLL = 584 ALL_GATHER + 40 GROUP_REDUCE_MCAST
+ 9 TOPK_MERGE + 8 ROW_GATHER + 1 ARGMAX_MERGE = 642 records. CHECKED = tool run; record->lane mapping UNCHECKED.
| item | delta/rec | ds loss | ds tok/s from 1906 | qwen loss |
|---|---|---|---|---|
| NE L4_i +1 (all COLL, upper) | 1 | 0.082 % | 1904.4 | 0.006 % |
| fallback P N=3 (reference) | 3 | 0.248 % | 1901.2 | 0.017 % |
| RX vsN0->root L118 (rx_flit + rx_block_ready together) | 19 | 1.555 % | 1876.3 | 0.109 % |
| TX hub->spb0 (tx_flit + epcal 19 b together) | 24 | 1.974 % | 1868.3 | 0.138 % |
| TX+RX, all COLL (upper bound) | 43 | 3.669 % | 1836.0 | 0.247 % |
| TX+RX, non-ALL_GATHER COLL only | 43 | 0.423 % | 1897.9 | - |

Reading:
- NE L4_i +1 costs <= 0.082 % < fallback P 0.248 %, so +1 is the cheaper of the two (the 0-cycle east-face re-land is still preferred).
- epcal (19 b) rides the same station chain as hb_coll tx_pin_flit (same pair NE/NW_hub->spb0, ~24 stations). It is a
  static calendar: the compiler advances its programme by the chain depth -> 0 steady-state cycles (UNCHECKED until the
  calendar is regenerated), the latency that remains is the TX leg itself.
- rx_block_ready (2 b) rides with ep_S1 rx_pin_flit/rx_pin_v on L118 (19 cycles): ready and data arrive equally late,
  so the static launch admission (launch_v && !ready = FAULT, no stall) only needs launch dated >= arrival + 19;
  the cost is the RX leg. RISK (UNCHECKED): release_v (hub->ep) closes a ready/release round trip of ~43 cycles; a record
  that re-arms the same RX block more than once pays it per block, not per record.
- Whether the token model's TU endpoint (108.6 cyc + 23.75/flit, fit to ha2hub) already contains these hub<->SPB legs is
  UNCHECKED; the table charges them fully on top. Upper bound 3.67 % < 5 %, so no OWNER ask (1906 floor OK).
  Relocating the q1 hb_coll edge master to the hub SW corner (DIE-HBM-11: ~12 TX stations) cuts the upper bound to ~2.7 %.

Note: tools/hgi_sim/timing.py _measured() silently falls back to estimates when a measured file is absent (sparse
checkouts): a run without results/rtl/dshbm_1m_allmeasured_20261004 gives base 557,291 instead of 576,702 cycles.
Run from a full checkout or check base_cycles = 576702.4.
