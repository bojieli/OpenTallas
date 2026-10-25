# S81 rank-aware indexed13 TX helper (dsdv_idx_tx_i13) -- functional evidence 2026-10-25

RTL: codex/s81-idxenc-1025@0221f2570 (dsdv_idx_tx_i13.sv + dsdv_idx_l20s.sv + dsdv_idx_tree.sv). Verilator 5.050,
`--x-initial unique --x-assign unique`, `+verilator+rand+reset+2`, all via ot-run on intel2.

| run | config | cases | result |
|---|---|---|---|
| r3/ | D=128 flop store, C=1024 | dense, cam: 88/88 beats exact, no fault; miss / duplicate / wrongtag: FAULT (st 0089 / 00a9 / 0089) | PASS |
| sram/ | D=1024 ASAP7 macro model ot_sram_1r1w_1024x256_m2_r2c2, C=1024 | same five cases | PASS, same cycles |
| multi/ | two jobs, job B exchange lands during job A transmit (other tag bank) | multi: 174/174 beats exact, 2 accepts/2 dones; samebank (B on A's bank): FAULT 0089 | PASS |

Measured cycles (all positive cases): command edge -> first lookup +27, first output +45, JOB_DONE +612
(issue_to_done 612, output span 567 for K=512). Job B in multi: accept 1711 -> done 2323 (612).
Open: two-source selector + wrong-qslot/order controls; actual synth fit (yosys SRAM_MACRO=1, D=8192; first run
still elaborating after 1 h: the C=1024 combinational duplicate search is the likely cost) and render before any route.
