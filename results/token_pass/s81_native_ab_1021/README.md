# S81 L0 native A/B programme generation (collected 10-21 TOK-FUNC2-S81)
Source generation only (no simulation), Codex gold1 unit2120299 (session17120), terminal exit0, compiler base a00d5b7f5,
out dir ot-gold1:/srv/opentallas-scratch/claude/codex-tok-s81-layers/dense_driver/native_compile/out_r1.
A: 1 op (a_proj) PARTIAL, 6 native target2/3 CTL rows, held END 809 (inherited price 534.5).
B: 55 ops = 46 PARTIAL + 9 GAP, 111 calendar rows, END 10770; sealed programme held, lifetime_qualified false.
GAPs: kv_norm.{sumsq,rsqrt,scale}, kv_rope_qdq (no KV unit on die), rows_allgather, router_allgather, substage_hop0
(vpx rows not placed), out_allreduce (vs owner fold encoder), normalize (SO P.V transpose). Not a layer PASS.
