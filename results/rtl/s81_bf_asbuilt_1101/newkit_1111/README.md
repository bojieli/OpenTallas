# S81 as-built BF measurement on main's ef870e plan kits, bound-plan seams (S81-FRAME-FIX-1 11-11)

Replaces the withdrawn claude/s81-bf-asb-meas-1111@a29d655ca4. That bench used plain 2-flop s81b_fint seams while the
schedules were traced with `--bound-plan plan_h2_2249` (u_s01 11, u_s12 6). Every return through a deepened seam was
measured 9 or 4 edges early, and a29d655 hid this with an as-built leaf_ret_corr. This run removes that corr branch
(xs_bf.py is unchanged from main). The extractor is also unchanged.

Bench (tools/s81_dv/bf_asbuilt_1101/prepare.py --bound-plan):
- reads the same plan as the schedule, and refuses if its sha256 or seam depths differ from the schedule's `bound_plan`;
- after each s81b_fint u_s<ij>, inserts D-2 whole-bus `ot_dp_st` stations, taken verbatim from tools/die_plan/bind.py CELLS
  (`<shape>/s81_asb_models_bound.sv`);
- records the bound plan in manifest.json and in every record (`asbuilt_source_qualification.bound_plan`).

Inputs:
- root = TOK-VERIFY-1 b3 frame root (TS5 + ef870e kits h9 598afa63580f / h10 0b0f9a60d5c6);
- schedules = b3/sched (sha cb86bc1f4542 / a5d1a2d0c99d / 15075f9cdcf3);
- Verilator 5.050 at 833 ps, as the 11-01 flow.

| shape | pv old (plain seam) -> new | ret old -> new | leaf_ret_corr |
|---|---|---|---|
| col_h9_asb_x | e4 324->324, e8 336->345, e13 347->360 | [414,417,431,433,439,442] -> [423,426,444,446,452,455] | {} |
| col_h9_asb_nx | same as col_h9_asb_x | same | {} |
| col_h10_asb_x | e1 321->321, e5 330->339, e10 339->348 | [412,415,424,427,428,436] -> [421,424,437,442,445,449] | {} |

Descriptors are unchanged (OFF4 PER1 N64), and lat_issue_to_pv is 106 for every leaf. Each pv shift equals the go_edge
shift: h9 e8 162->171, e13 173->186; h10 e5 156->165, e10 165->174. bf_input_seam_crossing.json shows the cause: the BF
x/go/cfg inputs of the r1 units (h9 e8, h10 e5/e10) cross u_s01 (+9), and those of the r2 units (h9 e13) cross u_s01+u_s12
(+13). The r0 units (h9 e4, h10 e1) cross neither.

Per shape: walker self-check OK (composed == run). The full, tail and router replays PASS. descriptor_fault and
payload_fault are both caught. Native family hold PASS (96 samples, pulse control caught).
qualify.log: PASS on root; REFUSED on a2/froot, on root_old, and on b3/froot as is.

Leaf latency (tools/s81_dv/bf_asbuilt_1101/bench_leaf_latency.py, leaf_latency*.json):
- every BF and q leaf, structurally (bench seams from Yosys, then the extractor's tracer);
- the measured BF leaves, by run.
Result: plain-seam bench FAIL, bound bench PASS. Covered by tools/s81_dv/test_bf_bench_leaf_latency.py.

Plan seams (plan_seams/seam_depths_plans.txt):
- TS5 bind plan_h2_2249 and BASE_1200 b5faa1ba: h9 and h10 {u_s01 11, u_s10 2, u_s12 6, u_s21 2}.
- DIE-S81-87 s87_ready5 c665c54a2573: h10 is the same. h9 u_s01 is 12 (all 60 col_h9 r0->r1 fi lanes have fixed_cycles 9->10).

So the col_h9 records only hold for a bind on plan_h2_2249 depths. After a ready5 rebind, col_h9 needs re-extraction with
`--bound-plan` ready5, then a re-measure. prepare.py refuses a plan/schedule mismatch.
