# hbm-fmax-sm: DS HBM SM element at 1.2 GHz (0.833 ns, SS +60 ps / FF +25 ps)

`closure.json` (built by `build_closure.py` from `records/`) has one row per block.

**Element.** `rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv`, `ENABLE=1` (default 0 = W13's `ot_gpu_sm_v`, unchanged).
- Closed issue and bulk copy successors; issue outputs registered (s1).
- One leaf per (column, sub) with its own 4 x-store macros (fragment re-laid out, per-bit write masks).
- Replicated (keep_hierarchy) distribution DS=3, gather DG=3, x-write DW=4.
- Registered boundary PIO=2, with credit channels for the descriptor and request.
- Leaf macros `ot_hbm_accel_tc16` (split bmul product, bubble kill) and `ot_hbm_accel_bd_col` (FP4 decode in P0, CSA 32->10|10->2) are routed abstracts.

**Exactness.** `tools/hbm_accel_sm_v_gate.py` runs W13's bench with the successor as the DUT, against the golden and the original on the same vectors:
- `synth`: W13 smv vectors, NC 1 and 2.
- `shapes`: every DS-token matvec shape of the baseline record. The original reproduces the recorded cycles.
- `edges`: zeros, signed zeros, subnormals, extreme block scales, cancellation.

Separately, `rtl/test/tb_hbm_accel_bmul_equiv.sv` checks the split multiplier on 2M vectors.

The real-operand rerun is pending; `closure.json` gives the reason under `unvalidated`.

## Replay (remote hosts only; R=/srv/opentallas-scratch/claude/hbm-fmax-sm, sources in $R/src)
```
FP="$(cat $R/jobs/fp_srcs.txt)"; L1="--routing-layers M2 M6 --orfs-var PDN_TCL=/src/tools/chip_assembly/tcl/pdn_block.tcl"
SRCS="$FP rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv" FP=1 UTIL=45 EXTRA="$L1" jobs/route.sh tck2_u45 ot_hbm_accel_tc16
SRCS="$FP rtl/v41rom/ot_v41_bterm.sv rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv" PARAMS=M1=10 FP=1 UTIL=40 EXTRA="$L1" jobs/route.sh bdk10_l1 ot_hbm_accel_bd_col
SRCS="$FP rtl/gpu/ot_gpu_stack.sv" PARAMS="LEV=4 IL=8 TAGW=12 ALAT=7" FP=1 UTIL=30 jobs/route.sh stack_orig ot_gpu_stack
jobs/abstract.sh tck2_u45 ot_hbm_accel_tc16; jobs/abstract.sh bdk10_l1 ot_hbm_accel_bd_col   # -> physical/hbm_accel_sm_views
FPARGS="--gap 14 --tile-gap-x 48 --tile-gap-y 30" HALO=4 jobs/route_sm.sh sm_r2  # element + corner_sta (OPEN: HANDOFF_CODEX.md)
python3 tools/hbm_accel_sm_v_gate.py {synth|shapes|edges} --out R.json --workdir W --jobs 12
iverilog -g2012 -s tb_hbm_accel_bmul_equiv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
  rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv rtl/test/tb_hbm_accel_bmul_equiv.sv
python3 results/rtl/hbm_accel_fmax_inventory_20261004/sm/build_closure.py
```
`jobs/route.sh` and `jobs/route_sm.sh` hold the sign-off recipe: ADDER_MAP off, WC setup, WC/BC hold, then `tools/w18/corner_sta.py`.

The leaf FP-IO is justified because every leaf port is registered on both sides. The element's IO uses the W13 die budget `rtl/hbm_accel/sm/ot_hbm_accel_sm_v_die_budget.sdc`.

**Qwen.** `ot_hbm_accel_sm_q` is off the measured Qwen HBM token. HA8 uses the W12 datapath; its token_result source lists contain no `rtl/gpu/*`.
