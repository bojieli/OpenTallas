# VISLAYOUT2-HBM form E1: q_spt0 + q_spt0__physical_v1 (DO_NOT_COUNT until signed off)

Base: d49a `e9ae418c06ca`. Output plan sha256 `57ba64e79056`. The delta is `delta.json.gz` (ladder_delta.py v1, round trip checked).
Generator: `hand_spt0.py BASE OUT 420`, then `ft_nudge.py`.
Scope: positions only. Windows, outline, cores, register counts and cycles are unchanged.

## Intent sheet
- Dataflow: the type is the xcal tile. The xcal macros u_xc_Q0 (SW, origin 77.76,25.92) and u_xc_Q1 (SE, 1460.16,25.92) are about 250 um tall. Their buses are:
  - S-face outputs: L41_o 1064 b at x 1531-1722 and L88_o 68 b.
  - S-face inputs: L50_i 618 b at x 146-257 and L84_i 99 b.
  - Each bus runs as an internal station chain between the face and the macro on the opposite side, so every chain crosses the full 1780 um width.
- Transit: wide N-S flowthroughs pass through the middle. L8x2 is 3070 b and L21x4 is 2560 b.
- S-to-S slots: q_spt0 has L1271x8 (512 b, x 33 to x 1446). pv1 has L5076x2 (653 b, x 1488 to x 53).
- Defect: in d49a, every chain and S-to-S slot has its registers on the S edge row (y 0 to 8.6). They run under and between the macros and through the S pin field.
  - Real GRT a10 on q_spt0: FAIL with 962,945 overflow. 44% of it is on the face.
  - route_supply p99 (edge_outline halving): q_spt0 2.87, pv1 3.04.
- Timing-critical pairs:
  - u_xc_Q0 to the L41_o window, u_xc_Q1 from the L50_i window, at 1 register per 395 um or less.
  - L1271 S0 (the input pin) to S1 must stay at 405 um or less.
- Hand arrangement:
  - Every edge-row station chain goes face, up to the macro-free row y 420 (above the 250 um macros), along that row, then down to the core pin.
  - Registers sit evenly by arc length and keep their counts. Chains whose hops would exceed 395 um stay where they are.
  - L1271x8 rides the same row. Its last register is kept, and its interior registers are spaced from the input window.
  - pv1 L5076x2 has only 4 registers, so it cannot reach the row and stays on the edge. This is the open item below.

## Scores (base -> E1)
| type | route_supply p99 (edge_outline) | G0 |
|---|---|---|
| q_spt0 | 2.873 -> 0.961 | no new errors (551 = 551) |
| q_spt0__physical_v1 | 3.037 -> 1.937 | no new errors |

## Open structural item (AMENDMENT 4)
pv1 L5076x2 already fails G0 in d49a: S0->S1 is 759 um against a 405 um limit, and it is the remaining hot face bin at (761, 5).
- Structural fix: add one station (+1 cycle on L5076, latency row owned by DIE-HBM).
- With 5 registers on the y 140 row between the macros, hops are 343 um. That clears both the G0 error and the face hot spot. In a trial with L5076 lifted, pv1 p99 was 0.961.

## E1b (adds the AMENDMENT 4 item, COORD approved 11-11 19:1x)
`delta_e1b.json.gz` = E1 + pv1 L5076x2 +1 station (4 -> 5, y 140 row between the xcal macros, hops 343 um) and
latency.lanes.L5076 cycles/stations/natural +1 (41 -> 42; DIE-HBM-100 owns the latency row).  Generator: `spt0_l5076.py`
on the E1 plan, then ft_nudge.  route_supply p99: q_spt0 0.961, pv1 0.968.  G0 551 -> 549 (the two d49a L5076 reach
errors are gone; no new finding).
