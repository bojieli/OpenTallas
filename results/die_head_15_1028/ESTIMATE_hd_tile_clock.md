# DIE-HEAD-15: hd_tile clock from core early taps, ESTIMATE (12.14 estimate-before-build; model UNCHECKED, inputs CHECKED)

Inputs (CHECKED, own reads):
- Tile 708.48 x 1036.8 um. The clk entry pin (353.76, 354.21) is the eA 2x2 channel cross.
- Cores: eA0..3 are 319.68^2 at (17.28|371.52, 8.64|380.16). eB is 285.12^2 at (216, 734.4).
- Core clock pins ft_mstrap_i sit at the core centres: eA at (177.1|531.4, 168.5|540.0), eB at (360.7, 880.6).
- SIGNED pin-register means (core_latency.json): eA 255.24 TT / 208.27 FF, eB 230.71 TT / 189.31 FF.
- Register sinks: 25,747 on clk plus 2,298 on fclk_in_i. From the 4_1_cts.odb bins they sit in three places:
  - the central channel x 337-371 (y 0-700);
  - the strip y 700-734;
  - the columns left (x 17-216) and right (x 501-691) of eB, up to y 1036.
- DIE-HEAD-14 CTS (TritonCTS, one entry):
  - clk_regs: path depth 19-22 BUFx24, average sink wire 837 um, register insertion 735-1082 ps TT (median 805).
  - Macro tree: 9 levels (average wire 689 um) plus 36 CTS-0033 delay buffers. Core pins came out at 317..711 ps TT, with an OT_TAP_CORE WARN on all 5.

## 1. Register leaf target T
- The farthest register from the entry is near (17|691, 1030), about 1013-1017 um Manhattan.
- Repeated M7 clock wire (r 12.5 ohm/um, c 0.0925 fF/um, one BUFx24 about every 150 um) costs about 0.34 ps/um. That gives about 345 ps from the root to the farthest leaf region. DIE-HEAD-8's independent estimate was 357-383 ps TT.
- A local tree (radius <= 150 um, 2-3 levels) adds about 80-120 ps, so T is about 430-470 ps TT.
- Decision: keep the plan budget T = 450 TT / 380 FF.
- TritonCTS reached 805 ps, 1.8x T. Its H-tree spans the whole sink bounding box: the average sink wire is 837 um against an average Manhattan distance of about 450 um. The fix is a plan-placed register spine plus local trees (12.13b local form), not a larger budget.

## 2. Core early taps (12.3 v5.0)
Pin target P = T - L_signed:
- eA: 194.8 TT / 171.7 FF
- eB: 219.3 TT / 190.7 FF

Natural branch, with no padding:
- eA: a BUFx24 at the channel cross (the core corner) plus the over-core M7 leg of 363 um. The leg RC is 4.5 kohm x 33.6 fF = 152 ps, so 0.38RC is about 58 ps, plus about 25 ps of driver: 85-100 ps in total. The leg slew is about 170 ps; DIE-HEAD-14 measured 170.7 ps at eA3 over the same leg.
- eB: two BUFx24 hops up the channel (182 um each, about 50 ps each), then a BUFx24 and a 146 um leg: about 140-160 ps.

Deliberate delay per branch = P - natural:
- eA: about 95-110 ps (about 5 BUFx4).
- eB: about 60-80 ps (about 3 BUFx4).

These delays are small. They are macro insertion-delay balancing (12.3 v5.0), placed at the DRIVER end.

## 3. Slew by construction
- Every delay stage drives only the abutted next stage (about 1 um away), so its input slew is about 20-40 ps.
- Only a BUFx24 drives a long leg: at most 363 um, about 170 ps.
- Repeaters are at most 182 um apart.
- All of these stay under 320 ps without CTS repair.
- DIE-HEAD-14's 1026/703 ps slews came from delay chains placed at the far (core) end and fed by an unrepeated long net.

## 4. Skew budget
- By plan, the related-pair skew reg <-> core is (P + L) - T = 0.
- The residual comes from chain quantisation (+-1 BUFx4, about 15-20 ps) and from leg/position spread.
- The unshared clock per core branch is at most about 0.5 mm plus 6 stages, so the 0.21 %/mm AOCV charge is small.

## 5. Corner check
The FF/TT ratio of the deliberate chain is about 0.84, while the needed ratio is 171.7/194.8 = 0.88. That leaves at most about 8 ps of corner skew.
