# dskv_wb_spec PIPE=2 (mtp-lead fork O, 2026-10-09)

Why: the registered-boundary PIPE=1 route mtprb-dskvwb_spec_rb-2426c04bd-tc stopped EARLY_FAIL_SETUP post-CTS TT -499.9 ps,
37,845 failing endpoints. Worst classes: `s0` -> sector address (S = s0 + t, ksec = S - kb_s) -> 17 x 8:1 shadow / data mux ->
wq output pin FIFO (-500, 995 ps of cells); rst_n recovery into the 4,352 `dat` flops (-304); the capture-cycle shadow merge
(pin FIFO -> n_in decode -> 64 field enables x 544 flops) and the b/96 ownership divide are of the same depth class.

Change (`rtl/hbm_accel/service/ot_hbm_accel_dskv_wb_spec.sv`, PIPE=2; PIPE 0/1 unchanged): every stage from registers.
IDLE capture; SHL bring-up shadow load from registers; A: q = (b>>5)*2731>>13 and a key row's 68 B merged into shadow[slot],
with `dat` taking the merged row (the emit reads `dat` for every kind); B: own, k, 68k / 9k / 17(k>>3) as shift-adds;
M: s0 / ns; PREP: registered sector address, row base, one-hot sector select, ns-1; EMIT: one sector a cycle from registers,
data = one-hot AND-OR of `dat`. Data registers carry no reset (only st / iss / ack / sh_locked do).
Wrapper `physical/mtp_rollback/regbound/ot_hbm_accel_dskv_wb_spec_rb.sv` regenerated with gen_regbound.py; the fence hand
edit (fence covers both pin FIFOs) re-applied unchanged.

Cycles: +3 a row vs PIPE 0 (+2 vs PIPE 1), +1 a shadow bring-up load; +1 each pin side from the wrapper. The writer rows
overlap the next draft (results/arch/mtp_step_20261009/hbm_ds_step.json), so the token-path charge stays overlapped.

Gate: tools/mtp_rollback_bench.py campaign on EPYC4 with the wrapper + ot_sc_pfifo in place of the writer and PIPE=2 in the
bench instance (compiled design confirmed to contain u_core.on2 and the pin FIFOs): 33/33 OK -- ROM + HBM good PASS at W128 / W8
(incl. spec_state_f and the MR-6 lock variant), every mutant FAIL, prefetch r256 PASS / as-built 128 FAIL.
rollback_record.json (source hashes are of the bench copy), campaign.log.

Routes: mtprb-dskvwb_spec_p2a-5ce6c3c62-tc (UTIL 35, HM 0), mtprb-dskvwb_spec_p2s-5ce6c3c62-tc (UTIL 28, HM 10, safe).
