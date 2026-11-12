# VISLAYOUT2-HBM form G1: q_su31 + q_su31__physical_v1 (DO_NOT_COUNT until signed off)

Base: d49a + spt0 E1 (e4b, 57ba64e79056). The ladder delta `delta.json.gz` touches only q_su31 and q_su31__physical_v1.
Generator:
1. `hand_su31.py BASE OUT SEED 212 8.64 1`
2. `core_place.py --seed SEED --no-search --reach 480`. This moves the cores and the taps and stations riding them.
3. L5053_i in q_su31 is re-spaced at its original 4 registers, with hops of 405 um or less.
4. `ft_nudge`.

## Intent sheet
- Failure (COORD 19:2x): q_su31 0609563b63c5 hit GRT early stop with 44,729 overflow (H 19.2k, V 25.5k).
  - Hot spot: (740,780). Top overflow net: `u_bound.u_ft_L8303mx1_o_4`.
  - This is die transit through the type, but not the q_su30 lanes.
- The transit: L8303 and L8304 are 1615 b each, 3230 b in total, running N->S.
  - N windows: x 662-1169. S windows: x 295-835.
  - In d49a their station bit rows (y 1324, 1000, 780, 578, 238) run straight over the lanes28_31 / lanes20_23 (top) and lanes12_15 (bottom) macros.
  - Over a macro only M6/M7 are open, so every bit crosses both macro rows over the SRAM pieces.
  - In the middle band both lanes jog sideways; L8303 stage 4 sits at (763,778), which is the hot spot.
- Hand arrangement (cores move rigidly by group, orientations kept):
  - W groups (lanes28_31 top, lanes12_15 bottom) go to x 8.64.
  - A 212-um macro-free N-S channel runs at x 769-981 through both rows.
  - E groups (lanes20_23, lanes4_7) move +65 um. The E strip keeps 90 um beside the top row for the E-face L5005/L1203 pins (1399 b).
  - Each lane runs N window -> top band -> down its own channel column (x 828 / 921) -> bottom band -> S window.
  - The first register is 170 um from the window, the rest are even. Station counts are unchanged (6/8/8/8). No cycle changes.
- Internal stations ending on the E groups (L7503_o, L5053_i, L7002_o, L3000_i, L3011_i) are re-routed with the same register counts. Hops stay at 405 or less.

## Scores (edge_outline route_supply)
- q_su31 1.002 -> 1.036; pv1 1.287 -> 1.093.
- Caveat: the model does not see the real failure. It scores the over-macro d49a form at 1.00, against 44,729 real overflow. The real GRT is the test.
- G0: no new finding (551).
