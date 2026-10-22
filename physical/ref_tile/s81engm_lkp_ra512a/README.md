# s81engm_lkp_ra512a -- S81 L14 Engram lookup, RETURN_AGE 512 (CRITICAL tile; coordinator review before submit)

Top dsfd_engram_lkp_ra512 (RETURN_AGE=512), branch claude/s81-eng512-1021. Replaces closed s81engm_lkp_static14 (st10).
RTL: ot_s81_engram_lookup_ra512 = static14 engine with the row payload (6 banks x 9 atoms x 256 b = 13,824 b runtime-indexed
flops + 6 x 768 b c* captures) moved into 3 x ot_sram_1r1w_128x256_m1_r2c2 (E even atoms, O odd atoms, A atom 8) on ck_rd;
ck_rows roots removed (11 phase-0 roots). One window is in flight (II = RETURN_AGE + 64 = 576), so return storage = one
window's rows at any RETURN_AGE. Same cycles as static14: bench tb_dsdv_eng_rr at RETURN_AGE 512 PASS, first/last XQ
fragment 556/651 (= RG-ENG static14 result), 6 mutants FAIL (results/rtl/s81_eng512_1021).
Floorplan: 259.2 x 302.4 um (aspect 1.17); macros u_row_e/o/a in one column on the pin-free E side at x 129.6, y 43.2 / 129.6 / 216.0 (43.2 lattice); 45 um to the N face, 43.2 um to S, 34.8 um to E; std cells in the W 129.6 um band + full-width bands between macros (gaps 45 um).
Pin plan: face lists (N window+row beats+hash/seed/n clocks, S HBM request/response+ck_s/ck_rd, W ck/rst/cfg/fault); the v28
die exact pin plan is dropped (ck_rows gone, outline changed) -> die pin re-grant needed (slot_change_request).

## Safe-design checklist
1 Pins: PASS -- RTL registers every data input/output (one flop, unchanged from static14); reset_landing 2 stages on ck, 16 kept copies (reset_relay_split max 32).
2 Reach: PASS by outline (max macro-to-face distance < 405 um; ra512b width 432 -- E-W wires across the full tile would exceed 405, flows N<->S only).
3 Fanout: write data has one kept copy per macro (wx_de/do/da); census pending gate (native census numbers below).
4 Depth: unchanged static14 stages; macro rd_out -> 2:1 parity mux -> E1 (one level); static14 hash stage 712 ps WARN carried (u_hash g_col x->s1), guidance.
5 Storage: FIXED -- 13.8 kb row payload + 4.6 kb c* captures now in SRAM macros; no runtime-indexed flop array > 2 kb remains.
6 Floorplan: macros on 43.2 lattice, >=34.8 um channels on macro pin faces (E face wd+mask ~12 pins/um on the macro edge: halo 5.4 + channel), aspect <=2:1, full-width std band; util from synthesis: see gate.
7 Clock: 11 phase-0 1:1 regional roots of one PLL (static14 st10 minus ck_rows); macros on ck_rd; io_hold_margin 0.03.
8 Schedule: static; no added cycle (write lands one edge earlier than static14, read/E1 edges identical); compiler contract = RETURN_AGE + 2 at the pins.
Native census / gate numbers: see gate JSON /home/ubuntu/scratch/s81-eng512-1021/ra512a.json (filled by the review entry).
