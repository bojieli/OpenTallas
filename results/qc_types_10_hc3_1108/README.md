# QC-TYPES-10/HC3 2026-11-08: slw_hc3 read-select fanout class -> ot_qfd_xs_leaf_fo32

Types: `slw_hc3__clccfc3e6b` (6 partitions: sl_W0, sl_E0..E4) and `slw_hc3__cld86a7ad4` (sl_W1..W5, sl_E5).
Both were routed but not signed off: TT -57.30 / FF -37.99 ps (clcc a7) and TT -119.94 / FF -38.09 ps (cld86 a8).
The one late ECO was used up on each.

## Class (measured)
- The worst setup paths start at a read-select replica flop `u_u_xl3_{6,7}.g_t[*].g_flat.g_lv[L].g_c[c].f` of the flat
  leaf `ot_qfd_xs_leaf #(NCH 4, READ_PIN_PIPE 1, FILL_PIPE 1, BANK_PIPE 0)`.
- The select leg alone is 380-460 ps:
  - cld86: QN fo16 116 ps, INV fo18 108 ps, BUF fo50, load_slew fo36 158 ps.
  - clcc: fo8, fo78, BUFx3 fo72 at 193 ps slew, 167 + 182 ps.
- Then come 8-9 mux/AO levels of about 270-320 ps, with 43-60 ps of tap skew against the path.
- Cause: `nrep() = ceil(loads/256)`. Level 0 gets 5 replicas, each driving about 218 mux loads, and ABC re-associates
  them up to 569 loads (SQC-CB16b census).
- At the GRT gate the same kit was at TT -6.3 ps, on a cland path. The leaf paths only fail after detailed route:
  every cell sits in a dense blob of about 330 x 230 um at the S face, and about 2/3 of the 622 x 1339 outline is empty.
- Not this class:
  - FF hold -38 ps on 7274 endpoints (b_hw_i pin reg -> pd1 -> xh3).
  - DRV slew 2925 (u_bout_cw_s3 D pins).
  - Both rows were built before tap-pair affinity was turned on.

## Form (no ECO, structural)
- Every hc3 x-slice leaf `dvs_[EW][0-5].u_core.u_sub.u_xl3_[0-7]` takes `ot_qfd_xs_leaf_fo32` through the new
  pass-through wrapper `rtl/qwen_sys/dvm_20261014/ot_qfd_xs_leaf_fo32_w.sv`.
  - Why the wrapper: fo32 declares NCH as a localparam, and bind kept the as-built `#(.NCH(4))` on it.
  - The wrapper declares the as-built params and accepts ONLY NCH 4 / FILL_PIPE 1 / READ_PIN_PIPE 1 / BANK_PIPE 0 /
    EXTERNAL_WD_CAPTURE 0 (yosys elaboration error otherwise). That is 96 leaves in
  12 partitions, all of them in the two slw_hc3 types.
  - The switch is one `substitute_inst` entry in `physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_hc3.json`.
  - That file = main `asbuilt_reach.json` + this one entry.
- fo32 has been on main since 10-22 (SQC-CB16b):
  - same ports and 0 added edges;
  - cycle-exact against exactly this leaf configuration;
  - one registered select replica per kept 16-bit `ot_qfd_xs_mx16` slice, so a select drives at most 16 mux bits;
  - kept per-region write-control copies;
  - kept entry halves.
- No pin cycle, plan or latency change. Plan = v4w `e5dc7eacb745`, no plan event. The other 117 types are unchanged
  (see cmp_bind.txt).

## Estimate
- Select leg 380-460 -> ~100 ps (16 mux bits per flop). The tree is 7 kept mux2 levels, ~200 ps.
- Standalone A/B on main (closure_loop, same leaf slot): fo32a TT +144.7 ps vs w130 +62.3 ps.
- Expected leaf paths >= +100 ps (were -119.94 / -57.3).

## Proof
- `bench_run.sh` runs the Verilator lock-step `tb_qfd_xs_leaf_fo32`: fo32 against the reference leaf configuration,
  with every output compared on every edge.
  - Seeds 7, 11 and 23 x 20000 ops: PASS, about 5000 answers each, good and bad.
  - Mutant MUT=2 (swapped tile): FAILS with 485 errors. See `bench_run.log`.
- `bench_w.sh` runs the same lock-step on the bound form `ot_qfd_xs_leaf_fo32_w #(NCH 4, FILL_PIPE 1, READ_PIN_PIPE 1)`.
  - 3 seeds: PASS. MUT=2: FAIL. See `bench_w.log`.
  - yosys: the bound params elaborate (rc 0); FILL_PIPE 0 is refused (rc 1, `$error`).
- Kit LEC (bound RTL vs netlist) runs in the kit flow as usual.

## Files
- `setup_src.sh` + `stage_w.sh`: private `cp -al` src tree + bind out seeded with the v4w elaboration (qct9/reach/bind_v4w).
- `run_bind.sh` (written by setup_src.sh): strict bind. `cmp_bind.py`: bind_hc3 vs bind_v4w.
- `run_dry.sh`: advisory dry path kit-rtl -> kit_topology -> gen phys -> gen_lint.
