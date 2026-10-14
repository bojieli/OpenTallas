# S81 Q element per-mac re-partition: mapped containers + seam pins (die lead, 2026-10-14)

Source graph 7602 (`source_graph.json.gz` sha256 a695f611..., uncompressed b2a84564...), `tools/s81/q_native_partition_graph.py --per-mac`,
ORFS yosys image 16470cea (asap7lock), merged lib of /srv/opentallas-scratch/codex/qcg-graph-7602/libs. Scripts: `tools/s81/q_permac/`.

| container | cells | mapped std um2 | FF (sinks) | macros | boundary ports |
|---|---|---|---|---|---|
| mac0 (g_mac[0] return + hardened lane + 2 ROMs) | 10,354 | 11,709.5 | 23,063 = lane 13,149 (own root gclk_ma, hard leaf) + return ~9,914 | 2 x ot_rom_4096x274_m8 | e_i 1,154 / e_o 1,119 / s_o 63 (p* results -> N bank) / s_i 1 (rst) |
| ctl | 5,495 | 4,420.7 | 8,186 | - | w_i/e_i 1,119 each, w_o/e_o 1,154 each (588 own + 566 broadcast, one driver, port per face), s_i 605 (operands, S bank), s_o 5 |
| mac1 | mirror of mac0 | 11,710.6 | 23,063 | 2 ROMs | mirror |

Total 54,312 FF / 27,840.8 um2 (= the Q full map). Seams (M4, 0.048 grid, same y both faces, 10.8 um end margins): 2,273 b each,
ratio 0.561 <= 0.60 (`seam_pins.json.gz`; place_pin files physical/ref_tile_specs/s81_q_permac/).

Area (corrected from the 4720059cf screen): mac at util 0.55 with the 2 ROMs stacked against its pinless S/W (mac0) or S/E (mac1)
corner (127.4 x 128 with halo): W >= ~174 um at H 216 (+ the lane as a hard child: ~190-200); ctl 41.04 (util ~0.58);
seams 2 x 20.16. Sum ~ 430-480 <= 512.64 parent. Physical admission false until the CTS gates (ctl, lane) and the mac kit with the lane child.
