# KV-ATTN2 10-19: qkd_kvs_attn_rv pair-lockstep evidence (Verilator 5.050, fleet ot-run, ot-epyc8)
tools/qwen_kv_die/attn_rv_1019/rv_pair_bench.sh RUN MUT -> tb_kvs_attn_rv_pair (A = qkd_kvs_attn_fl_ba5, B = qkd_kvs_attn_fl rv,
B's ports == A's ports one edge earlier, valid-masked data; 11 modes: legal x3 commands + 10 fault modes).
m0/verdict.log: KVS_RVPAIR_ALL PASS 155,024 checks.  m1..m7/verdict.log: the real mutant runs (fail_regex ^KVS_RVPAIR_ALL FAIL).
