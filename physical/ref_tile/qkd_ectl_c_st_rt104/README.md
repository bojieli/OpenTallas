# qkd_ectl_c_st_rt104 (KV-SAFE32D 10-20, route B K budget 104)
Re-harden of the closed rt80 kit at K_RT_BUDGET 104: RESPONSE_LAT 104 / ROW_RETURN_LAT 111 / QK_ISSUE_AGE 115 (QK = RL + 11,
the bench-proven minimum). Same RTL, outline, macros and pin plan as the closed rt80 kit. Benches/witnesses:
results/rtl/ref_tile/qkd_ectl3_kiss_st/bench_witness_rt104 (tools/qwen_kv_die/chain/kv_safe32d_bench.sh, Verilator 5.050).
## SAFE checklist (owner 10-19)
1 Pins: PASS (pin regs as the closed rt80 kit; reset landing as rt80).
2 Reach: PASS (tile <= 254.88 um wide; frame: wires-only, as closed e5).
3 Fanout: as rt80 (gate textbook high_fanout census = the record; a census violation counts as FAIL).
4 Depth: PASS (deeper shift lines add no logic depth).
5 Storage: WAIVED (rule freeze 10-20 09:35): K issuer ident line 36 b x 105 = 3.8 kb flops (rt80: 2.9 kb, CLOSED); a fixed-age
  shift line, never runtime-indexed; ROW_RETURN_LAT return slots are 1 b x 111.
6 Floorplan: PASS (unchanged closed floorplan, macros on the 43.2 lattice).
7 Clock: PASS target (pin-flop spread <= 80 TT+FF checked at the gate; io_hold_margin as rt80).
8 Schedule: static; +24 edges of K round trip priced by kv_static_ages.K_RT_BUDGET -> die_ages (RESPONSE_LAT / QK_ISSUE_AGE)
  and CALGEN D_QK (kv_static_attn_join); no credits or backpressure.
