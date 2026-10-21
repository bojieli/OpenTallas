# s81engm_lkp_ra640a -- S81 L14 Engram lookup, RETURN_AGE 640, NATIVE32 (CRITICAL tile; coordinator review before submit)

Top dsfd_engram_lkp_ra640 (RETURN_AGE=640), branch claude/s81-eng640-1021 (lineage claude/s81-eng512-1021@4d1484501).
Why: G7 die (claude/s81-die72-g7-1021) measured Engram response age ~435 + 2x70 eng<->etap_15 chain stations = ~575 > 512.
RTL: dsfd_engram_lkp_ra640 / ot_s81_engram_lookup_ra640 / ot_s81_engram_hash_n32 = ra512 (row payload in 3 x
ot_sram_1r1w_128x256_m1_r2c2 on ck_rd, 11 phase-0 roots, no ck_rows) with RETURN_AGE 640 and NATIVE32: the ra512 gates
FAILED the pre-gate native census (345 drivers > 32 loads, max 1,173: hash w/roll_h 308, e0r_v/r_k0/e1_v/e1_off E1/E2
enables+selects, csel/hdone/icnt/acnt decodes, a_last/a_v/a_first) -> kept keep_hierarchy copies (ot_s81eng_kq/kqr) or
unobservable enables removed. 0 cycles vs ra512.
Schedule (price for the die calendar): one window in flight, II = RETURN_AGE + 64 = 704 (ra512 576, +128); row beats
leave at RETURN_AGE+2: bench first/last XQ fragment 684/779 edges from f_ks (ra512 556/651, +128). Compiler contract =
RETURN_AGE + 2 = 642 at the pins. In-flight storage unchanged (one window, 13.8 kb in the 3 SRAMs).
Bench: tb_dsdv_eng_rr at RETURN_AGE 640, Verilator 5.050 (ot-epyc9), base PASS + SEED 2/LAT 160 + SEED 3/LAT 60 PASS;
mutants xq1/xq2/tap1/tap2/rpar/onesc FAIL (witnesses results/rtl/s81_eng640_1021/witness/*.log, runner
tools/s81_dv/eng_rr/run_eng_rr.sh @48f78e8e6).
Floorplan: 259.2 x 302.4 um (aspect 1.17, = ra512a); macros u_row_e/o/a in one column on the pin-free E side at x 129.6, y 43.2 / 129.6 / 216.0 (43.2 lattice); std cells in the W 129.6 um band + full-width bands between macros (gaps 45 um). MAIN.
Pin plan: same face lists and ports as ra512 (N window+row beats+hash/seed/n clocks, S HBM request/response+ck_s/ck_rd,
W ck/rst/cfg/fault); die pin re-grant needed (slot_change_request), master dsfd_engram_lkp_ra640 replaces ra512.

## Safe-design checklist
1 Pins: PASS -- RTL registers every data input/output (one flop; hr_tag two kept flops); reset_landing 2 stages, 16 kept copies.
2 Reach: PASS by outline (all faces within 405 um of the std mass; no single-cycle wire spans the tile diagonal > 405).
3 Fanout: FIXED -- NATIVE32 kept copies (ra512 census 345 drivers > 32); census numbers: see gate JSON (pre-gate census in the gate).
4 Depth: static14 stages; hash residue select now 8 bits per copy; E2 shifts explicit 4:1 per 8-bit slice; static14 hash 712 ps WARN carried (guidance).
5 Storage: PASS -- row payload in SRAM macros (ra512); new copies are pipeline flops, no runtime-indexed flop array > 2 kb.
6 Floorplan: macros on 43.2 lattice, >= 34.8 um channels on macro pin faces, aspect <= 2:1, full-width std band; outline from ra512 synthesis area 35,064 um2 (incl. 3 x 3,894 macros) + ~2.9k um2 NATIVE32 copies -> util ~44-47%.
7 Clock: 11 phase-0 1:1 regional roots (ra512); copies on the root of the register they copy; io_hold_margin 0.03.
8 Schedule: static; 0 cycles vs ra512; RETURN_AGE 512 -> 640 = +128 on II and row-beat latency (priced above).
