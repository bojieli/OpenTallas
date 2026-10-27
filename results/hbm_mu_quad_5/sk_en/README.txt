HBM-MU-QUAD-5 sk sub-lane (task 3), 2026-10-27, epyc2. tail_sink_clk div-7 GENERATED clock -> div-7 CLOCK ENABLE (COORD 03:02 GEOM-18 (a)).
RTL (unchanged from QUAD-4, generator results/hbm_mu_quad_4/sk_en/gen_sk_en.py): rtl/hbm_accel/cores_split/sk_en_q4/
  ot_hdc_sinkhorn_se.sv (sk_step0_en / sk_steady_en: clk = die clock, every flop enabled by sk_en, landing register sk_en_q)
  ot_hgi_hc_tail_static_se.sv, ot_hbm_hc_tail_unit_static_se.sv (free-running /7 counter -> registered sk_en_o, 1+NSTA cycles
  ahead so the landed enable == old sclk; no generated or gated clock). Source hashes: sources.sha256.
SIM (QUAD-4, Verilator 5.050, lock-step old divided-clock form vs new, results/hbm_mu_quad_4/sk_en/sim; source sha256 re-verified CURRENT 04:2x):
  PASS NSTA0 seed1/seed7/mode1 seed3, NSTA1 seed5 (78-84k edges, 150-160 results, sk state compared every edge, 0 faults).
  Mutant MUT_EN=1 (enable one cycle early): FAIL sk_err=39600 out_err=78085 (expected).
LEC (this lane, yosys in orfs:asap7lock, formal/): gold = old ot_hdc_sk_{step0,steady}, gate = *_en with sk_en=1 (EN_LAND=0).
  Combinational arithmetic (sk_add/seed/quot/norm, verbatim on both sides, same instance names) CUT: outputs -> shared free inputs,
  inputs -> checked outputs (proof holds for any arithmetic function = LEC modulo uninterpreted functions).
  step0: 7976/7976 $equiv proven; steady (async2sync): 4989/4989 proven. Non-vacuity mutants (mut/): step0 load polarity -> 1904
  unproven FAIL; steady r_pa default -> 3 unproven FAIL.
  HOLD sk_en=0: opt_dff -sat removes all flops (step0 75 dff -> 0, steady 7 adff + 16 dff -> 0; hold_after_list_*.txt empty) = no state change when disabled.
  Rationale for EN_LAND: the landing flop is a 1-cycle delay of sk_en_i; the tail emits sk_en_o 1+NSTA early; covered by the sim.
  QUAD-4 full-datapath equiv_simple run (serial loop, step0 alone >46 min of 6 jobs) was stopped 04:12 (pids 3734959/3734965, container 914582c7e115) as intractable; its 91 MB log deleted.
PLAN DELTA: plan_delta.json (ports, centre clk entries, generated_clocks.json entries to delete, core_conns change).
