The actual generated nc32 fan-root simulation assertion fires at time0 under
random power-on values, before reset can establish equal copies. Owner13
permits independent initial state. Guard only this known simulation-only
assertion with rst_n && rs_q; all synthesized logic remains unchanged.
stage_src.sh applies the exact-match, idempotent helper to staged copies.
Unknown assertion text fails closed rather than suppressing arbitrary checks.

Actual generated source smallest module is retained as the test fixture.
At exactly833ps clock, random-init original FAIL at0; guarded nominal PASS;
forced post-release copy mismatch FAIL at25ns. Thus the check remains active.
Reproduce through ot-run using tools/qwen_layerbench/kv_dieslice/run_reset_selfcheck.sh
results/rtl/kv_reset_check_1025/qkd_kv_ctl_nc32_face.sv OUT.
