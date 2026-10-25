TOK-QW 10-24: Qwen ROM (Qwen3-8B, compute dies + KV die) functional token record on current main.
Compute-die stages measured on assembly = git archive main 8a5d1f3dab (rtl tools configs physical/asap7_memory_macros*);
their readset (rtl/qwen_dv, rtl/test/qwen_dv, headprep13, tools/qwen_layerbench, tools/qwen_tokfunc stage drivers) is
unchanged 8a5d1f3dab -> main 7d75427c59 (only d2d/KV/S81 files changed). RUNROOT intel1:/srv/opentallas-scratch/tok-qw/r1024.

Stages (stages/*/result.json), all Verilator 5.050, grade RTL-functional (source assembly):
  stg     PASS 527/527 cases, delivery timing qualified, 0 unknown (slice2 12-slice chain, SU_LT 0, rel/pos/mut; 36 layers)
  head    PASS img0 123/123, imgh 131/131, bmut3 FAIL as required; die-selected leaf native32_1r (stage_head.sh --leaf);
          LM-head start->END 3,135 = compiled
  attnret PASS measured span 98 == compiled 98 (rel + pos), ddwin/ddbase mutants FAIL
  xhead   PASS 4/4 consumers (qkv/gu/o/down), 10/10 mutants FAIL; calibrate go_lag -3 / xpf_lead 4 (sweep widened to
          OT_XH_GO_MIN -8: the -2..6 sweep had no FAIL edge); consumer ages qkv -5/4, o -1/4, down -2/4
Composed with QC-TOK link stages (results/token_pass/qc_tok_1024/link: tp8, xdie, ovl4u, assembly 3e05af806) and carried
10-23 stages (results/rtl/tokqwm_1023: xt1, ctx4u, kv, chain; KV r17 child archives were lost, readset 53/53 unchanged).
compose/report.json (compose_tokfunc.py --grade RTL-functional):
  all 9 stages + attnret + xhead PASS; 1u 271,106 cyc = 4,428.1 tok/s; 4u 11,844.1 tok/s (833 ps).
  vs 10-23 (269,452 / 4,455.3 / 11,811.3): +1,620 cyc from the QC xdie stage on the CAL-AUTO regenerated D2D constants
  (roundtrip 1887 -> plan 1872, = TOK-QW xdie_bound measurement), 4u +32.8 from QC ovl4u.
  PRICE HELD: open gaps IMAGE CAPACITY (slice table_req consumer not exercised), TILE DELIVERY (per-slice go delay not in
  RTL), PER-TOKEN RoPE ROW producer->consumer (no cross-die co-sim of the KV RoPE row).
NOT RUN: stg families on the BOUND compute slice row (bound_r8 uses qfd_dv_s8_flat / s8_ce_* instead of qfd_dv_slice2);
  tb_qfd_dv2 FACE 3 (DV2_S8DIE) vehicle builds (32 C++ units, ~2-3 h each) -- run_scripts/s8cal*.sh, still compiling.
