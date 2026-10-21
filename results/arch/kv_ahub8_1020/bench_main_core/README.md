# KV-AHUB9 10-20: a7 hub benches against the source the die binds

Source = branch claude/kv-ahub8-1020 @b4197ae74: a7 `qkd_ahub_static_dw.sv` (sha 8b0b8b2d) with MAIN's
`ot_qkd_ahub_core.sv` (31f136f3, a7 built with 5e2479bd) and `ot_rst_pipe.sv` (29203f84, a7 7d6cba3c).
Fleet ot-epyc5, Verilator 5.050 (daemon version), `runall.sh`.

Why main's core is safe to bind: the a7 hub uses only `ot_qkd_drly` from `ot_qkd_ahub_core.sv`
(module text byte-identical in both versions; the diff is in `qkd_ahub_core` / `ot_qkd_ahub_die` defaults and ports,
which the a7 hub does not instantiate). The `ot_rst_pipe` diff adds `COPIES` (default 1 = the old `assign`).

| bench | result |
|---|---|
| s4o (a7 production bench; the kit's only bench) m0 | PASS: 7 passes, Z_IN_STRIDE 4, FR_OFS -7, AP_OFS ffddffdeffdcffdc |
| s4o mutants m1..m12 | all FAIL as expected |
| dw (main's 10-18 hub bench, own offsets) m0 / m1..m3 | PASS / all FAIL |
| bo (qkd_ahub_static_dw_bo, g7 line) m0 | PASS (other module, unaffected) |
| s4 (HKV-AHUB4, RTL default offsets {4{2}}/0) m0 | FAIL `die hub fault hf` -> RETIRED on this branch |

s4 is the a4-kit configuration (default offsets). The a7 hub requires PV_START + R + FR_OFS >= HUB_PUB + 3, and the
die binds the BOUND offsets [-36,-36,-34,-35] / -7, so default offsets fault by design. s4o MUT 8 (DUT at the default
offsets against this die) is the kept witness for that configuration and FAILS as required.
