# PLAN-DELTA/QC 2026-10-25: approved type reductions on non-PATH Qwen compute types

Base: Codex START plan `codex/qc-start-plan-0719@1c0e347be4` (main 394765394 + `reset.start=broadcast`; plan sha256 ce2406b9...b92720).
Delta: `delta_qc.py` (in place, idempotent, refuses if any PATH type json changes); `run.sh` calls it after `apply_start_broadcast.py`.
Checked against the canonical START bind of this exact plan (epyc1 `codex-qc-token-current-0719/plan_canonical_394_start/final`, verify 0 errors).

## Result
| | before | after |
|---|---|---|
| partition types | 56 | 55 (`sle_hc3` -> `slw_hc3`, 6 E partitions, orient R0) |
| su_lane core designs (module, pin table) | 16 (8 W + 8 E) | 11 (8 W unchanged + E lanes 4, 5, 7) |
| G0 | PASS 0 err / 110 warn | PASS 0 err / 109 warn (dropped: near-duplicate `sle_hc3`/`slw_hc3`) |
| G0C | PASS 0 err / 110 warn | PASS 0 err / 109 warn |
| die max reset release (wavefront) | 128 | 127 (START boot S+130 holds) |

PATH check (`reset_path_compare.json`): 18 PATH types (slice W5, `sle_ctl`, `coll_ftc`, `native59`, `glue`, `phy_ucie_kv`):
json unchanged, derived wavefront reset pins (IN, rst_o, start_o, depth) unchanged, every PATH partition's type, orient and
release cycle unchanged. `slw_hc3` (a PATH type) is byte-identical; it now has 12 instances (6 E partitions re-typed onto it).
The `su_lane_w` pin tables and module used by `sl_W5_su_l0`/`su_l1` are byte-identical.

Changes:
1. `reset.in_sites` freezes the current wavefront IN site of 37 of 53 soft types: all types except the non-path E-slice types `sle_*`.
   This is needed because `reset_tree.wf_solve` is a die-wide search. Without the freeze, any re-type moved the reset pins of
   `coll_ftc`, `native59`, `glue` and `slw_*`.
2. `sle_hc3` -> `slw_hc3`: `dedup.try_merge` keeps every die pin. Outside the reset tree the bound RTL (START bind) is identical
   (the "s6b" contents label is stale). Non-path reset pin sets re-solved: `sle_hc0`, `sle_hc1`, `sle_hc2`, `sle_st_b`. About 50
   E-half partitions move by 1-3 release cycles.
3. su_lane: E lanes 0-3 (`sle_su_l0`) and lane 6 (`sle_su_l1`) have pin tables equal to the W table of the same lane (R0). They now
   point at `qfd_qc_su_lane_w` and the W pins_file, and the 5 E pin files are deleted. Lanes 4, 5 and 7 have different E pin
   placement and stay `qfd_qc_su_lane_e`.

## Deferred (measured)
The W/E pairs are NOT exact on the current bind. W and E slices take their wavefront reset from opposite faces (W types IN on
the E face, E types IN on the W face), so the bound RTL differs in the reset relay tree (rst_o_k/start_o_k counts and relay depth).
A merged type carries the union of the instance reset pins, so a merge either changes the PATH W type or delays the release.
Measured per merge (`in_sites` frozen for all types / all except `sle_*`):
- hc0, hc1, hc2: change PATH `slw_hc0..3` reset outs (hc1: 33 partitions unreachable with full freeze).
- st_a: changes PATH `sle_ctl` and `slw_hc3`, or leaves 2 partitions unreachable.
- su_l0: changes PATH `slw_su_l0`, or max release 131 > S+130.
- st_b: G0 R8 ERROR. The E and W instances need different landing pads at 8 sites (pads 14/15); W `qfd_qc_slw_st_b` has pd15 pads
  that E lacks.
- hc3 combined with any of the other merges: changes a PATH type or raises the max release to 132-134.
- su_lane 4-class reduction (lane0/lane1/lanes2-3/lanes4-7 by orient): no two W tables are equal under any orient, so it would
  rewrite the PATH `su_lane_w` tables.
To unblock: a symmetric reset plan for the slices (IN site on a face that every instance reaches from the same side, or the root
moved to the slice axis) is a reset re-plan of PATH types and needs PATH-QC's agreement. st_b also needs an R8 lane-depth fix.

## Downstream
Bind artifacts in `bind/bound*`, plan_notes and kits still name `sle_hc3` and the 5 E lane tables. They need a re-bind (the 6
`sl_E*_hc3` partitions bind `qfd_qc_slw_hc3`) and kits for the changed non-path types `sle_hc0`, `sle_hc1`, `sle_hc2`, `sle_st_b`,
`sle_su_l0` and `sle_su_l1` (core pointers only). PATH kits do not change.
