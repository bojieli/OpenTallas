# dsdv_gunit_l5 -- S81 G-unit leaf L5 (HC tail + coefficient CTL rows)

## S81-SAFE-FIX/GUNIT redesign (2026-10-19)

The first route was `dsdv_gunit_l5-g3-37cf95cf2`. Its gate passed only because `gunit_sinkh_mcp.sdc` made the whole
Sinkhorn a 9-cycle multicycle path behind an ICG. That one reg->reg stage was ~5.3 ns and 138 logic levels
(`u_tail.u_sinkh.g_srow[*].g_dec` -> `w[*]`). Hiding it with an SDC exception is masking, so the tile was redesigned
structurally:

- **Sinkhorn:** `rtl/hdc/v41/ot_hdc_sinkhorn_p.sv` matches `ot_hdc_sinkhorn` bit for bit, including y and fault, and
  runs on the core clock. Each normalisation is cut into 11 registered stages of at most ~20 levels:
  - three chained adds;
  - T (+ eps in steady steps, normalise in step 0);
  - the seed, in 3 stages (ROM, carry-save, CPA);
  - the quotient, in 3 stages (X*R carry-save, CPA plus M', remainder carry-save);
  - a combinational final.

  Step 0 takes 12 stages and shares the same datapath. There is no ICG and no multicycle exception.
- **Latency:** the result latency is 441 edges after accept, and the HC result arrives 55 edges later than before
  (tail L 637 -> 692; G-unit `hc_lat` 748 -> 803 at the stop pins). This is handed to MU-DIE-S81 for the schedule and
  the token pricer.
- **Table select:** the select `tj_set`/`tj_w` drove 3,456 loads. It is now replicated in two kept ranks (8 -> 108
  copies, one per 8-bit read group). It costs 0 edges because the select is stable from L4's `mix_go`, at least 29 edges
  before launch.
- **Index delay lines:** the tail's 5-bit index delay lines (79/24/5/4 deep, 560 flop->flop chain flops) are replaced by
  the index recomputed from `age` and registered. This costs 0 edges.
- **Kit settings:** `reset_landing` 2 stages and `io_hold_margin_ns` 0.03 are on; `gunit_sinkh_mcp.sdc` and
  `ot_hdc_cg` are no longer used.
- **Benches:**
  - `run_sinkhorn_p_eq.sh`: equivalence with `ot_hdc_sinkhorn` over 300 mixed cases (exp-like, wide range, subnormal and
    zero rows, fault words), plus mutant 1, which lands a step one stage early.
  - `run_gunit_bench.sh`: the exact bench, plus mutants 8 and 10.

## SAFE-DESIGN checklist (owner 10-19)

| # | item | result |
|---|---|---|
| 1 | pin registers + reset landing | PASS / fixed. The RTL registers every input and output (input flops, output flops, `dsdv_gunit_pass` feedthroughs), so the recipe `pin_regs` stays off with its recorded reason (no double stage on the rung). `reset_landing` is on with 2 stages (fixed), followed by `ot_rst_relay`. |
| 2 | reach <= 405 um per cycle | PASS. The outline is 345.6 x 302.4 and every pin flop is anchored at its face (`io_flop_at_pins`). The gate lint checks reach. |
| 3 | fanout <= ~32 in critical cones | fixed: `tj_set`/`tj_w` have 108 kept copies; the Sinkhorn has kept T and R copies per quotient and 16 kept mode copies. Check the gate's high_fanout warnings and that the kept copies survive Yosys (attribute-based keep, so not name-based). |
| 4 | <= ~600 ps / ~20 levels per stage, no masking | fixed: the multicycle SDC is removed and the Sinkhorn is pipelined (see above). Check the gate's logic_depth. |
| 5 | storage > 2 kb in SRAM, no long delay chains | fixed: the index delay lines are gone. **Waived with reason:** the 2 set x 2 which x 864 b base/scale table (3.4 kb flops) is a 4-entry static configuration table, written only by cw, with a replicated 4:1 read select. An SRAM macro (>= 64 deep) would be ~94 % empty and add macro floorplan risk. |
| 6 | floorplan / util 40-60 % / aspect <= 2 | aspect 1.14 and no macros. Util comes from gate synthesis (see the gate packet); re-outline if it falls outside 40-60 %. |
| 7 | clock: pin-flop spread <= 80 TT+FF, io_hold 0.03 | `io_hold_margin_ns` is 0.03 (fixed). One root with no ICG. The spread is judged at the gate (`--cts`); the previous trial measured TT 77.9 / FF 68.3. |
| 8 | static schedule, cycles handed over | fixed: HC result +55 edges and reset release +2 are handed to MU-DIE-S81 (INBOX). |
