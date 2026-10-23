Source 222474aac (one-hot grouped ring slice). Full-TX lockstep (tools/s81_dv/tx_export_1021/run_tx.sh, Verilator 5.050, ot-gold1):
MAIN D4K2 REF_LPX8 p0/p9000 PASS 2522 cycles/56074 checks; ALT D8K3 REF_LPX10 p0/p9000 PASS; MUT7 (missing ring) caught cycle 340 on both.
slice_equiv.log: random dual-clock/reset miter old binary slice (old_slice.sv) vs new, tb_eq.sv. slice_phase.log: tb_tx_ring_phase 0/+-0.9T.
