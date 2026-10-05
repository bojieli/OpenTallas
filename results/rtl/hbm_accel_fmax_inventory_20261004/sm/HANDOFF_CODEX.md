# Handoff: DS HBM SM element route loop (hbm-fmax-sm, Claude -> Codex, 2026-10-04 23:00 PT)

**Closed and merged.** All leaves of the element close at SS/FF, and the element RTL is exact (see `closure.json`).
- `ot_hbm_accel_tc16`: SS +24.88 / FF +2.33.
- `ot_hbm_accel_bd_col`: SS +19.01 / FF +5.05.
- `ot_gpu_stack`: SS +12.58 / FF +3.31.

**Open: the element route.** `ot_hbm_accel_sm_v` with `ENABLE=1` is not yet signed off.

**Running job (do not duplicate).** `ot-epyc1tb:/srv/opentallas-scratch/claude/hbm-fmax-sm/routes/sm_r2`
- Command: `FPARGS='--gap 14 --tile-gap-x 48 --tile-gap-y 30' HALO=4 jobs/route_sm.sh sm_r2`
- Registered in experiment.py as `fsm_sm_r2`.
- Synthesis, placement and CTS have passed. It was in global routing at 23:00 PT.
- At its end the job runs `corner_sta` itself. The result lands in `routes/sm_r2/corner_sta.json`.
- r1 failed in detailed placement with DPL-0033 on 2 cells; r2 widened the gaps.

**The CTS repair log shows WNS ≈ -4.0 ns, all at the boundary.**
- The worst endpoints are the output port `rv` and `g_new.u_prd.g_s[0]` (the first `rsp_data` input stage, 1,098 bits).
- That is the die-budget IO (`ot_hbm_accel_sm_v_die_budget.sdc`: input 473 ps external, output 323 ps external) against pins at 25-75 % of each edge of a 2.2 x 2.07 mm element.
- Inspect `corner_sta.json` once it lands: `worst_reg_to_reg_slack_ps` separates the internal r2r from the IO.
- Likely fixes, in order:
  1. The first/last `PIO` stage flops must sit at the pins. Check placement: `u_pst`, `u_pop`, `u_prv`, `u_prd`, `u_prl`, `u_pbz`, `u_prv_o`, `u_prd_o`, `u_dch`, `u_rch` (`g_s[0]` for inputs, `g_s[PIO-1]` for outputs). If the placer pulls them inward, raise `PIO` to 3, or constrain them with a region / `set_dont_touch` placement.
  2. Check that the clock insertion is not driven by the macro timing models. Leaf models came from `write_timing_model` with propagated clock; their clock-pin latency is inside the arcs.
  3. If internal r2r fails on distribution / gather hops, raise `DS` / `DG` (each costs +1 cycle per op).
  4. Keep the IO budget; do not false-path. The leaves' FP-IO is justified by their registered boundary.
- Every parameter change must re-run `tools/hbm_accel_sm_v_gate.py shapes` and `edges` on EPYC. Record the new drain delta (currently +12 cycles per op group, barrier +4), then run `build_closure.py`.

**Measured cost so far** (at `DS=3`, `DG=3`, `PIO=2`):

| Term at 1.2 GHz | Baseline | Successor | As built, 0.59 GHz |
|---|---|---|---|
| SM | 70.12 µs | 73.55 µs | 142.69 µs |
| Barrier | 22.29 µs | 23.43 µs | 45.37 µs |
| SM + barrier | 92.41 µs | 96.98 µs | 188.06 µs |

The successor values assume the element closes at 1.2 GHz.
