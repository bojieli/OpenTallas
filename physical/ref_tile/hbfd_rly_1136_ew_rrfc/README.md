# hbfd_rly_1136_ew_rrfc (L2H-RSTFB 10-19, HBM d4g H.RST.FB)

L2H-RSTFB 2026-10-19 (H.RST.FB): NEW master hbfd_rly_1136_EW_rrfc = hbfd_rly_1136_ew_rr (station instantiated unchanged) + ONE reset-forest carrier stage ot_hbm_rly_rfc (rfi async-clears 2 landing flops, sync carrier flop q, rfo = land[1] & q: assert immediate, release exactly 3 edges); rfi on the i face, rfo on the o face; outline / recipe / pin faces of the closed kit; 0 data cycles.

Bench: rtl/hbm_accel/die_glue/test/bench_rly_rfc.sh (Verilator 5.050): 6 instances chained rfi->rfo, release age 3k at station k, immediate assertion, data / rso unchanged and independent of rfi; mutants land1mut / combmut / nogatemut / datamut FAIL (witnesses in results/rtl/hbm_rly_rfc_1019).

## SAFE-DESIGN checklist (owner 10-19)
- 1 pins: PASS: station pins unchanged (i captured / o launched by the ONE stage register, as the closed kit); rfi lands in 2 registered stages at the face (async clear of exactly the 2 landing flops, textbook reset_landing <= 2 sinks on rfi); rfo = land[1] & carrier flop q (flop-driven; AND for immediate assert)
- 2 reach: PASS: no new wire inside the tile beyond the station outline (<= 114.5 um); forest edges into rfi / out of rfo are reach-checked by reset_forest_layer (hop budget) and re-checked on real LEF pins by die_case
- 3 fanout: PASS: rfi drives 2 flops, land[1] drives q + the AND, rfo drives one forest stage or leaf
- 4 depth: PASS: rfi -> async clear; flop -> AND -> rfo; no combinational data in->out path
- 5 storage: PASS: 3 flops; no delay line >= 3 (the 3-edge age is 2 landing + 1 carrier flop, not a shift chain)
- 6 floorplan: PASS: same outline as the closed station kit (+3 flops on a >= 21.6 x 21.6 um strip: util rise < 1%); rfi on the i face, rfo on the o face
- 7 clock: PASS: the station clock ck (planner hosts only on stations of the forest domain); hold_margin / io_hold_margin 0.03; pin-flop spread judged by the gate --cts
- 8 schedule: PASS: static; data stage unchanged (0 data cycles); reset release age 3 edges per hosted stage, charged by reset_forest_layer --host-form rfc in every leaf / pad age (equal-age leaves)
