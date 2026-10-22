Actual selected KV attention r17 minimum

Source: 08d6b6778. Selected physical spec is physical/ref_tile/qkd_kvs_attn_rv5/spec.json; top qkd_kvs_attn_fl, wrapper qkd_kvs_attn_fl_r17.sv, core qkd_kvs_attn_r17.sv. RETIRE_STATIC = 1; STATUS_DELAY = 213. The generator flag ATTN_R16 names this r17 successor.

Fleet EP7 unit 1927132-1792642776, client 1770101, Verilator 5.050. Positive pair lockstep passes all 11 modes; calendar reset passes all 3 random seeds. The reset-removal mutant 8 and command-field misalignment mutant 2 both fail at runtime. The runner requires explicit causal runtime markers and rejects build failures. All source identities and binary hashes are retained.

This is a component qualification. It does not qualify actual HBM relay delays, the current generated die programme, the RoPE admission relay, or the complete physical token. A separate r17 top build over unchanged retained native datapath libraries is running. The historical r16 real-token chain remains predecessor evidence only.
