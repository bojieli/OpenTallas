# qfd_mu_ctx_rx_die (QW-MU 10-20, kit c1; fallback _b = same RTL/pins, PD 0.35)
Filler runtime initial-context receiver of the Qwen MU compute die (die inst `mu_ctxrx`, dv_case CTXRX), NU 4.
Bench (Verilator 5.050, fleet oth-ubuntu-2362006-1792564029): tb_ctxrx PASS 983 slots / 741 loads; bad record PASS; MUT 1 FAIL.
SAFE-DESIGN checklist:
1 Pins: outputs all flops; inputs -> one compare cone -> flops; pin regs opted out (owner 10-20 09:05: same region as the face, clk_d2d). Reset lands in 2 stages (reset_landing).
2 Reach: tile 43.2 x 97.2, no wire > 405 um.
3 Fanout: reset loads 4 (load, ctx_user x2, mu_fault) -- the 128-b record is unreset and un-enabled (RTL change); user decode ~37 loads (in-tile, < 100 um).
4 Depth: one compare (31-b header + 59-b tag check) per stage; no in->out path.
5 Storage: 132 flops (< 2 kb).
6 Floorplan: outline + pins = the die generator's frame (dv2f20g5r2b out/pins/qfd_mu_ctx_rx_die.json); rx_payload 548 b W at 2 tracks (pin-bound; [511:59] unread: whole-port GEN endpoint, narrow port = GEN follow-up); no macros.
7 Clock: single root ck, ~140 sinks.
8 Schedule: static, edges unchanged (one register edge after the slot).
Census: from the --remote gate netlist lint (gate_result.json).
