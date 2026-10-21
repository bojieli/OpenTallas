# hcoll_fj1_r128u3 -- ot_hgi_coll_fj_n1s0_r128 (HBM-COLLQ6 10-20)
n1s0 fj leaf for the die SE/NW/NE COLL parents (r11 contract: ot_hfd_coll_q2_hard_v8g #(NLINK 1); SAFE successor
ot_hfd_coll_n1s0_lp_ars). Body = ot_hgi_coll_fj_core_s128 #(NPT 1, SOLO 0, NS 8, NSL 18, RC 32): identical to the CLOSED
hcoll_fj2_r128u3 (a36c24de8) except NPT/NS (one capture_fault / link_abort bit fewer). Kit = fj2_r128u3 geometry, hooks,
reset settings, entry wrappers (fj1_u3_*_entry.tcl).

Benches (Verilator 5.050): n1s0 parent EQ vs v8g #(NLINK 1, AR_ITER 1, ROWS 128) PASS 100,576 compared + EQ/RS/LP mutants
(results/rtl/landed_parent_1018/collq/bench_witness_5050_n1s0_ars); fj mutants latespc (parent EQ, REJECTED) and LA_STALE /
LDH_NOFWD via the s128 miter (the parent-EQ LA_STALE form is blind on n1s0, see NOTE_fjmut.txt).

Gate --cts (6a41e0f58): WARN 0 fail (1-bit vector port link_abort naming note). SAFE checklist:
1 pins: RTL pin regs (fj_core), reset 2-stage landing, RC 32 copies -> PASS
2 reach: 103.68 x 71.28 tile, no wire > 405 um -> PASS
3 fanout: pre-gate native census max 32 -> PASS
4 depth: setup WNS +150.9 ps at placement RC -> PASS
5 storage: flow table in ot_sram_1rw_128x64 (u.u_program.u_flow) -> PASS
6 floorplan: macro on the 43.2 lattice (43.2, 43.2), full-width S std-cell band, pins S/E <= 6/um, fill 34% (pin/lattice-bound, as fj2_r128u3) -> PASS (fill reason inherited)
7 clock: S entry beside the band; 3,022 sinks, TT 140-160 ps, pin-flop spread TT 12.4 / FF 11.4 ps -> PASS
8 schedule: static, 0 added edges (= fj_n1s0 ports/edges)
