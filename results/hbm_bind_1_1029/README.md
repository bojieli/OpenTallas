# HBM-BIND-1 (2026-10-29): HBM strict die bind, bucketed by root cause

Inputs (read-only, Codex /plan/bind parked 05:0x): intel1:/srv/opentallas-scratch2/claude/codex-hbm-bind-0300.
Plan 16e0513d (C25c base lineage), netlist top_native.sv c0eadd4c, elab current_r2/asbuilt.json bc9707b7
(made by clean pinned Codex worktree a65884a08). All shas: shas.txt. Bind step = main tools/die_plan/bind.py
(this branch base); elab is reused, the netlist is unchanged. Runs: intel1:/srv/opentallas-scratch2/claude/hbm-bind-1-1029/{b1,b1s,b2}.

## Baseline r2 (Codex): 254 error lines (CHECKED bind_report)
| bucket | size | root cause |
|---|---|---|
| U-SU | 29,198 cells, 8 SU slices | the plan splits each slice into su_x0/su_x1; no home for the slice glue/pinned_bank/lane_pinreg |
| U-SFU | 3,262 cells | sfucore_NE/NW u_core glue has no home |
| U-IDX | 3,164 cells (+24 keybuf/or) | scorer quarter W/E glue (input pin flops, W address glue, E glue, score regs) has no home |
| UNPLANNED | 50 pairs, 15,329 b | plan lanes missing (DIE-HBM-11 ESTIMATE scope) |
| EMPTY/EMIT | 3 | NW/NE_mca have no content |

## Candidates (bind = map/manifest only; no plan geometry edited)
- B1 = Codex native cones + SU ownership r3 (map parts + compose with 16 FF fractures) + reset_carrier_parts.
  Unmapped 35,624 -> 5,572 (SU 0). mca/EMPTY fixed. New errors: 48 TIED strap_lane_id; 1 EMIT hcb bank128 rst_n;
  UNPLANNED 50 -> 106 pairs / 94,141 b. The 56 new pairs (78,812 b) are mostly SU half<->half
  (su_x0<->su_x1 3,356-3,728 b each) and hub->su 2,846 b: putting the SU control on both halves needs plan lanes.
  Exact list: b1_unplanned_lanes.json. This is the lane input for the die owner's combined C25c event.
- B1s = B1 + `.*\.strap_lane_id` declared as an ID strap. keybuf lane id = pbase+p is constant per instance (OWNER 10-25 ID straps).
- B2 = B1 + glue_homes.py whole-cell K-partition label propagation for the scorer/SFU residual.
  Unmapped 0, but UNPLANNED 170 pairs / 173,797 b, and 2,128 TIED bits now visible
  (sfucore u_output.ra literal, scorer u_qlate.rst_n=1 literal). REJECTED as a home rule: the bit vote splits
  the quarter W glue between the hub and the banks, which adds comb crossings. The scorer/SFU glue must sit where the
  plan lands its lanes (input regs + W glue with the r0c0 front leaf partition, E glue/score regs with the tail partition).
  That is the next step.

## Result B1s (CHECKED b1s/out/bind_report.json): 308 error lines = 5,572 unmapped (scorer 4x791 + sfucore 2x1204 cells) + 106 UNPLANNED + 1 EMIT. TIED 0.
Next: (1) plan-landing homes for the scorer/SFU glue (replaces B2); (2) EMIT hcb bank128_pair0 rst_n, caused by the cones compose of the hcb leaves (diagnose);
(3) the die owner adds the 106 lanes in the combined C25c event, or moves SU homes to one half (central-primary 86,328 b vs split 60,296 b, Codex estimate UNCHECKED).
