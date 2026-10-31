ECTLK four-column RTL at the KV BOUND parameters (DIE-KV-50 2026-10-31, COORD 02:0x option (a)).

Why: the KV strict bind of record (event28w_c, kit-wave bind of plan_c) regenerates every ectl
(param_regen.json via r8/kv_pv_col_regen.py, PATH-KV kv_regen ECTL) from as-built RESPONSE_LAT 80 / QK_ISSUE_AGE 91 to
the bound 18 / 34; every hg type RTL instantiates qkd_ectl3_kiss_st #(.QK_ISSUE_AGE(34), .RESPONSE_LAT(18)) u_ectl.
ectlk_q/qkd_ectlk_columns.sv was generated (results/arch/kv_plan_1025/ectlk_columns/ectlk_columns.py) from a reference at
91 / 80, so the four quarter cores did not implement the die's ectl.

Change: ONLY the parameter literals of qkd_ectlk_reference.u_leaf, 91/80 -> 34/18 (port ABI, pin drop and column
ownership unchanged, so qkd_ectlk_q0..q3 pins/outlines are unchanged).

Miter (tb.sv = ectlk_preflight_1025/tb.sv with RL = the response latency, si[632:537] tied 0 and the dropped outputs
so[12:0], so[25], so[409:282], req_v, req_t[13] masked = the approved pin drop; o side = kiss_st #(O_AGE, O_LAT),
n side = qkd_ectlk_columns_legacy; Verilator 5.032, run.sh):
  nom  : columns 34/18 vs kiss_st #(34,18), RL 18 -> PASS mismatches=0 edges=8580 kreq=2672
  mut  : columns 34/18 vs kiss_st #(91,80), RL 18 -> FAIL mismatches=8472 (the bench sees the parameter)
  base : old columns 91/80 vs kiss_st #(91,80), RL 80 -> PASS (bench reproduces the 10-25 result)
Consequence: q0..q3 must be re-hardened + re-signed from this RTL; the signed 80/91 quarter views are not the die's ectl.
