# INFRA-FIRST-QC-R16: riser fix by island window, su_c hold by row placement, 43.2-um centre channel plan delta (2026-10-27 00:35 PDT)

Solver: tools/die_plan/qc_clk_mesh3.py, three opt-in plan options (default path unchanged; test_qc_clk_mesh3.py 4/4 PASS):
- `--island-edge-sym`: the VSS slot rows keep the 8.64-um lane at BOTH type-frame edges (vss_grid top bound L - EDGE).
  R15 dropped the top-edge lane, so an MX instance had no die-bottom lane at seam + 8.64. The nudged seam rows
  (2626.56 / 5235.84 / 7853.76 + mirrors) and the centre rows then pushed their lane-0 repeaters onto lane 1, where
  three repeaters and a node shared one lane. That gave 92 M7 riser collisions (6.115 um).
- `--row-at G=Y`: local row G is placed at Y in the plan, mirrored in the top half, with lanes stepping away from the
  centre. Used as 10471.68=10445.76,5227.2=5218.56: the su-row local x-tree lanes (+8.64..+25.92) ran into the su_l0
  lane cores (partition y 34.56). That pushed the midpoint merge t*_b07_1 127 um off centre, which is the 41.4 ps
  template imbalance and why the su_c / su_l0 taps were 16-28 ps early. The row now sits in the core-free cb top band
  (merge centred, imbalance 0).
- `--ytree-split TAG=H`: an experiment on y-tree topology (not used in the result; see the identity notes).

Runs (pkg epyc2:/srv/opentallas-scratch2/claude/qc-mesh-r12/pkg out/r16e = edge-sym, out/r16f = edge-sym + row-at; solver copy pkg/r16wt). All numbers are UNCHECKED unless marked CHECKED:
| | R15 | r16e | r16f |
|---|---|---|---|
| nominal tap skew TT / FF ps | 40.66 / 35.85 | 40.24 / 36.53 | 25.67 / 22.76 |
| MC 13 samples, die-wide max-min TT / FF | 325 / 281 | 327 / 283 | 327 / 283 |
| seam TT setup (997 pairs) | 531.25 | 531.45 | 540.42 |
| FF hold, zero logic | -119.04 | -119.20 | -115.09 (HB4, 997 neg) |
| kit-contract FF hold, plain | +13.20 | +13.61 | +29.36 PASS |
| kit-contract FF hold, F4G RP1 + VMR core view | -4.64 FAIL | -4.66 FAIL (need 44.66) | **+12.65 PASS** (need 27.35 <= 40 W, 0 neg) CHECKED |
| HB4 cells / area | 2.73 M / 0.279 mm2 (R13) | 2.644 M / 0.270 mm2 | 2.611 M / 0.267 mm2 (0.0325 % die), worst TT cost 249 ps vs setup +540 |
| identity (types identical / hosting) | 74/74 | 74/74, 0 viol | 65/66, 2 viol (cbx_q10 lift lane) |
| dry exact build (original die) | 176 | 84 | 84 |

- The CHECKED kit hold damage was recomputed independently from sta_in_cv tap arrivals over the 773 pair_unc rows, in both directions. Worst r16f 27.35 (sl_W2_su_c -> sl_W2_su_l1) and r16e 44.66 (sl_W0_su_c -> c_W0_bn_00) match the gate.
- Dry: the 84 left are 70 channel x-tree cells (YC, one-lane fold) plus 14 centre-row repeaters at YC +- 8.64..26. All of them are in the centre channel, and the 43.2 delta has not been fed to the solver yet.
- Identity: in r16f the moved rows 3 and 7 have different y-tree depths (4 / 3), so the local-root lift repeater lands 1 slot apart in cbx_q10 rows 2 vs 4. `--ytree-split T_b11=2` equalises the depth (cbx clean), but it creates one top/bottom slot asymmetry in cbn_q00 (947.86 vs 952.72). Open.

Plan delta (plan_delta/, scripts/r16_plan_delta.py D=43.2 on repo physical/die_plan/qwen_compute/die_plan.json 54a1aeb5):
- die H 26265.6 -> 26308.8 (3045 x 8.64, VSS phase and mirror kept). 182 partitions moved up 43.2; coll_f5 kept, west strip channel grown.
- New channel [1563.84, 13132.8, 31216.32, 13176.0] holds 5 VSS lanes (13132.8 + 8.64k, k = 0..4).
- 49 declared crossing channels (between, width 43.2, M4-M7) carry the 316 seam ports. The older candidate_oneqc0733 plan gives 304, because 12 st_a flt ports are absent from it.
- G0 PASS, 0 errors, 111 warnings, the same set as base. Worst cut 0.2159, worst segment 0.5134, both equal to base. The PHY libs were added to the sparse cone.
- NOT done: solve, export and dry on the delta die (shift the r2 rec / tree plan, centre offsets D/2, lane-aware channel x-tree on 5 lanes, channel host in export). Physical build, DRC, RCX and RCX STA were not run, because the dry build is not 0/0.

Render: render/r16_fix.png (viewed). Panel A/B: the nudged row in R15 (lane-1 crowding, error) vs R16 (lane 0 kept, 0 errors). Panel C: the su-row local tree in R15 (lanes into su_l0 cores) vs R16 (cb top band, centred merge). Panel D: the 43.2 channel.
