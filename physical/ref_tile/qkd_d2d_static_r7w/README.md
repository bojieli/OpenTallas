# qkd_d2d_static_r7w (TW7-KVD2D 10-19)
KV die D2D link end re-hardened at the MU release seam TXDP_K 0x03030415 [21,4,3,3] (r7v = 0x03030418 cannot bind the MU KV die).
Only the TXDP parameter differs from r7v (CLOSED 1b609a25c, TT +13.55 / FF +7.68); geometry identical (review 83ff32c7 carried).
Benches: run_d2d_dies.sh KDLY=18 (exact + LOCK NTX3 lockstep; mutants MUT1 / LMUT1 / LMUT2, witnesses in results/closure_witness/qkd_d2d_static_r7w).
SAFE checklist (owner 10-19): 1 PASS (RTL PR=1 pin flops + kit reset_landing 2 stages + ot_rst_pipe regions); 2 PASS (475 um tile, pin flops FIRM);
3 waived: reset region rst_n[1] 321 loads, CTS/repair buffered, r7v closed with it (SAFE-AUDIT-KV: none blocking); 4 PASS (r7v closed);
5 PASS (slot store in 4 SRAM macros); 6 PASS (lattice, std-cell band, as reviewed); 7 PASS (spread 71.2/64.7 r7v, io_hold 0.030);
8 PASS (static compiled calendars, no credits/backpressure).
