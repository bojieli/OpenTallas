# HBM-BIND-11 (2026-10-29): HBM-041 cleared, the hub HC `$div` is emitted as native glue

Sub-lane of DIE-HBM-23. Plan d23a (`intel1:/srv/opentallas-scratch2/claude/die-hbm-23/plan/d23a/die_plan.json`,
sha256 4133ce1e4e0d). Run dir `intel1:/srv/opentallas-scratch2/claude/hbm-bind-11-1029` (variant `g1`).
The tools are hub main fbde5b15d98, and they were not changed.

## Cause
HBM-BIND-5 e2 dissolves `ot_hbm_hc_qcen_static` (hc_NE.u_cen and hc_NW.u_cen), so its own logic is re-emitted as glue.
Line 85 is `wire [3:0] drun = 4'(in_w / NJ)` with `NJ = W / 32 = 4` (W 128). Yosys keeps it as a `$div` cell whose
divisor is a constant. `bind.py _glue` has no `$div` form. It does exist in `bind_native_glue.SUPPORTED`, the opt-in
path that re-emits one cell through Yosys `write_verilog`, with no mapping and no optimisation. That path was not
enabled in the manifest, which listed only `$shift` and `$shiftx`.

## Fix (die-local manifest only)
Add `"$div"` to the manifest's `native_glue_types` (see `mk_g1_manifest.py`; it reproduces g1/asbuilt.json byte for byte).
The emitted helper is `ot_bind_native_626a9a88cf25221c8bfe5338.sv`: `assign Y = A / 32'd4`, with A = the 6-bit `in_w`
register. The constant divisor stays inside the helper, so it is not a parent tie. NE and NW share this one helper,
and each hub partition (`hbm_arch_q_hub__q_hub_ne/nw`) instantiates it once.
We considered two alternatives and rejected both. Mapping u_cen whole would undo the HBM-BIND-5 subtree32 parent cuts
that the plan needs. Dissolving one level deeper is not possible, because the `$div` is u_cen's own logic.

## Results (CHECKED = run here and read from out/bind_report.json and bind.log)
| run | errors | UNPLANNED (bits) | EMIT | tied / undriven / multiply_bound | unmapped | open_outputs | warnings |
|---|---|---|---|---|---|---|---|
| b2 (DIE-HBM-23 baseline) | 93 | 92 (82,285) | HBM-041 `hc_NE.u_cen.$div...qcen_static.sv:85` | 0 / 0 / 0 | 0 | 3036 | 0 |
| g1 (+ native `$div`) | 93 | 92 (82,285), the same set (CHECKED, list equal) | `parent ID q_su00.u_su_Q0_lanes_plain0_3: parent_id_straps lane_lane_id: no actual input of width 9` | 0 / 0 / 0 | 0 | 3036 | 0 |

The `bind_tied.json` files are identical. The straps count is 11,485 in both runs. Peak RSS was 7.2 GB and the run
took 2:53 (intel1, MemoryMax 64G).

## Next masked EMIT (a different pattern, so this lane stops here)
The plan d23a `partition_types.q_su00.hard_cores[8]` (`u_su_Q0_lanes_plain0_3`,
`ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526`) declares
`parent_id_straps {"lane_lane_id": {"width": 9, "value": 16}}`. `parent_id_straps.py:86` finds no 9-bit
`lane_lane_id` input on the bound actual master. Either the plan declaration or the canon split's port is wrong.
This is a plan/kit ID-strap contract question, not glue.

Files: `bind_summary.json` (full error list + counts), `mk_g1_manifest.py`, `run_bind.sh`, `cmp_vs_b2.py`, the helper `.sv`.
