# Qwen ROM closure-cost ledger (qwen-blocks, 2026-10-07)

Base: 194,226 cycles / AR token at 8K (1.2 GHz). Upper bounds: every added cycle exposed on every op / crossing; ME ops/token = 325 (assumed).

| item | cost | cycles/token (UB) | AR % (UB) | cum AR % |
|---|---|---:|---:|---:|
| tile_rom_pipe | qfd_tile/_e ROM_PIPE (rp2 = ROM_ARELAY 2; rp1 = 1): ROM/KV/x memory return +ROM_ARELAY+2 cycles per ME op fill | 1,300 | -0.665 | -0.665 |
| spine_lane_ostn | spine lane y station +1 per tree traversal (one per ME op) | 325 | -0.167 | -0.83 |
| spine_lane_credit_ps | lane credit shell +3 per transaction (one per ME op) | 975 | -0.499 | -1.321 |
| hub_ps | hub ar +1, link tx +1 (per stack-link word path; 2 all-reduce link legs a layer) | 144 | -0.074 | -1.393 |
| hub_cdcp | hub link receive CDC PIPE +2 fck +1 ck a crossing | 216 | -0.111 | -1.501 |
| io_xfifo_p | IO CDC channels: +1 wclk relay, +1 wclk pointer publication, +1 rclk station per crossing (2 crossings an all-reduce) | 432 | -0.222 | -1.716 |
| io_collective_pr | collective: local word +1 cycle to its FIFO head per all-reduce | 72 | -0.037 | -1.752 |
| ctrl_hbm_domain | controller masters in their die clock domain hbm_976p6 (1.024 ns) per the die clock plan: no cycle change | 0 | 0.0 | -1.752 |
| cdc_m2 | STREAM4 CDC reset release +1 edge: no data-path cycle | 0 | 0.0 | -1.752 |
| **TOTAL (UB)** | | **3,464** | | **-1.752** |

Status: candidates; adopt only on CLOSED routes with exact benches. Replace the ME op count with the measured token trace before publication.
