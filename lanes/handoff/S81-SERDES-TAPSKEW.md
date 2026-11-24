# S81-SERDES-TAPSKEW handoff (fresh lane 11-24 07:5x PST)
Job: serdes__t2 tap skew row (STB-COMMON) on c9, PRE + scoped strict bind, ROW-REBASED -> S81-ALLFIX-INT.
- Tool: STB-COMMON main 4d87f4ac76c (in c9 rt 515889f6ef75). STB-BOUND-PORTS 6d967ec98ec also in.
- R1 = SELLK read_lockup (S81-ALLFIX-SVC, main 8c20aed38f/07359c423f) already in c9 048fa468f0a2 for all 11 serdes.
- Row: epyc9 /srv/opentallas-scratch2/claude/s81-serdes-tapskew/c9row/c9_stb_common_t2.ops.json d30ff3db5f4d
  (add /partition_types/serdes__t2/clock/stb_common true); plan p6w_c9_stbcommon_t2.json 291a0f8396d0 (base c9 048fa468f0a2).
  gen_phys exports for t2: OT_STB_COMMON = 1 (checked with rt 515889f6ef75).
- PRE: c9row/pre.sh row|base (plan_gate_pre check, tree amd1_tree read-only), out pre_row.log / pre_base.log.
- Prediction (epyc8 s81-serdes-tapskew/pred_common.out, pred_rehome.out, hold, in-type, SELLK not modelled):
  common Tc 401: ring 475->0, txl t28->t29 88->0, rm 21->0; left: rck 73 -110.9 (DCHN-KLOCK in c9), t31>t24 29 -80.8,
  t27>t28 2 -42.9, NEW fclk_in->clk_t33 40 -30.2, enc t20>t28 207 -26.6, t29>t24 40 -2.1. Total 900->395.
  per-tap rehome-only (no common): with SELLK closing the ring, leaves fewer (enc 216->4) -> candidate tool mode.
