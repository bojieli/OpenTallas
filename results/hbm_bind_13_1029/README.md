# HBM-BIND-13 (2026-10-29): HBM-043 cleared, the SU cut resets are split as in the source and the kits

Sub-lane of DIE-HBM-23 that follows HBM-BIND-12 (branch base 22e60875c07). Plan d23a
(`intel1:/srv/opentallas-scratch2/claude/die-hbm-23/plan/d23a/die_plan.json`, sha256 4133ce1e4e0d) is unchanged.
Run dir `intel1:/srv/opentallas-scratch2/claude/hbm-bind-13-1029` (variant `g3`). No tool was changed.

## Cause
- **As-built top.** `top_native.sv` ties `su_N*`'s `rst_n`, `rst_lane_n[31:0]`, `rst_bcast_n[3:0]` and `bridge_rst_n` all to
  `hb_ckgen__por_stream[0]`. The Codex native compose therefore merged every reset terminal of each SU cut (bank `rst_n`,
  lane `rst_n` and the ARST of the per-lane `g_bcast` ctl replica flop) into one input, `bank_rst_n`.
- **Source.** `ot_hbm_su_static_pgslice_s.sv` keeps them apart:
  - `u_bank.rst_n(rst_n)`;
  - `u_lane.rst_n(rst_lane_n[n])`;
  - the ctl replica at line 135, `always @(posedge clk_bcast[b] or negedge rst_bcast_n[b])`.
- **Kits.** The sw2.py wrapper `ot_hbm_su_static_pgslice_lg__lane_exp0.sv` has `.bank_rst_n(rst_n)` and `.lane_rst_n(rst_lane_n)`.
  The pin tables of the lane_exp / lanes_plain / lanes / lanes8_11 kits all carry `rst_n[1]` + `rst_lane_n[n lanes]`.
- **Plan reset tree.** `reset_tree.core_reset_targets` takes the kit pin `rst_n`, and `bind.py` looks for a bound cut port named `rst_n`.
  No such port existed, so the check found 0 leaves.

## Fix (die-local compose copy plus manifest pointer; nothing tied)
`mk_compose_rst.py` fails closed. It checks every ARST member against Yosys `src` = `ot_hbm_su_static_pgslice_s.sv:135.4-136.56`,
and it allows only bank / lane / ctl-flop terminals and one `g_bcast[b]` per cut. It splits `bank_rst_n` into:
- `rst_n`: the banks' `rst_n` (the kit pin and the plan core reset target);
- `rst_lane_n[k]`: lane k's `rst_n`, lanes in ascending n (the kit pin);
- `rst_bcast_n`: the ARST of the ctl replica flops. This is not a kit pin: the kit keeps those flops outside the core,
  while the as-built cut has them inside. It stays on its as-built net.

It touches 112 cuts. They get renamed modules: `ot_hnx_su_exp__rst3` ×64, `ot_hnx_su_plain4__lid9_rst3` ×44 and
`ot_hnx_su_plain4__7dd6a1bbbf47_rst3` ×4. `mk_g3_manifest.py` changes only the `compose` path (g2 → g3).

## Results (CHECKED = run here, read from out/bind_report.json and bind.log)
| run | errors | UNPLANNED (bits) | EMIT | tied / undriven / multiply_bound | straps | open_outputs | warnings |
|---|---|---|---|---|---|---|---|
| g2 (HBM-BIND-12) | 93 | 92 (82,285) | HBM-043 `wavefront core reset q_su00/u_su_Q0_lane_exp0.rst_n: ... found 0` | 0 / 0 / 0 | 9,945 | 3036 | 0 |
| g3 (+ reset split) | 93 | 92 (82,285), the same set (CHECKED) | `wavefront core reset q_su00/u_su_Q0_side_softplus.rst_n: expected one bound leaf, found 0 (partition NE_su00)` | 0 / 0 / 0 | 9,945 | 3036 | 0 |

The `bind_tied.json` files are identical. The run took 2:57 with a peak of 7.3 GB (intel1, MemoryMax 64G).

## Next masked EMIT: a different pattern, and it needs a ruling (ASK)
The plan d23a carries side cores in the SU types: `u_su_Q*_side_softplus` (q_su00 / q_su10) and `u_su_Q*_side_rest` (q_su01 / q_su11),
in both the plain and `__physical_v1` forms. That makes 8 partitions per die: NE/NW × su00/01/10/11.
The as-built source has no side unit for these cores. `top_native.sv` instantiates `su_NE0..3` with QID 3, G 0..3 and `su_NW0..3` with
QID 2, G 0..3. `ot_hbm_su_static_pgslice.sv:182` builds `u_side` only `if (QID==0 && G==0)`, and the map has no `u_side` cell at all.
So no source cells exist to cut, and no compose or port fix can create them. The pattern is the same as HBM-040 (plan copies that have no
as-built source).
- (A) Plan delta d23c: drop the 8 side cores (and their buses and stations) so the plan follows the as-built source, as HBM-040 (A)
  did for the u_vmdel copies.
- (B) Source: give the SU that should own the side (FULL_SIDE / QID-0 role) a side unit in `top_native`. This is the TOK/architecture
  owner's call, and it applies if the folded 8-SM schedule needs the SU side functions.

DEFAULT (A), unless the token schedule uses the SU side pipe on this die. Note that the plan also places a side core on G 1
(q_su10/q_su11), which the source never builds.

Files: `bind_summary.json`, `mk_compose_rst.py`, `compose_rst_report.json`, `mk_g3_manifest.py`, `ot_hnx_su_exp__rst3.sv` (composed),
`run_bind.sh`, `cmp_vs_b2.py`.
