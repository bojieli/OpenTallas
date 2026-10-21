# hcoll_reduce_lane_u -- COLLQ7 10-21: _t (51.84^2) daemon FLOORPLAN_MARGIN (util 65.6% with hold allowance > 65%) -> outline 60.48^2 (est. ~48%); RTL/pins/recipe = _t. Checklist item 6 FIXED (outline from synth area inside 40-60%); all others as _t below.

# hcoll_reduce_lane_t -- ot_hgi_coll_reduce_lane (HBM-COLLQ6 10-20), x16 in the SAFE COLL parents (q3 / n1s0 lp_ars)
Native32 redesign, 0 added edges: the lane takes the D side of its command registers (u_ariter tag D outputs, inst_d2
strobes, reduce control wb pipe stage 6) and lands its own kept copies per 2-bit slice (16 slices x 23 flops), equal bit
for bit to the upstream d3 registers; LAT-8 add = pin regs + ot_hdc_fp32_add_n32 #(LAT 6, DRST 0) + one output stage,
copy families split by the kit-scoped synth_canonicalize.tcl (from hbm_su_qcore_r13_1020). Benches 5.050: RS EQ PASS 200k
+ 3 mutants REJECTED; q3/q2/n1s0 parent EQ PASS (lp records unchanged: no port offset moved).
Gate --cts: WARN 0 fail. SAFE checklist: 1 pins: inputs land on the slice copies / adder pin regs, outputs flop Q PASS;
2 reach: 51.84 um tile PASS; 3 fanout: native census max 32 PASS; 4 depth: setup +66.7 ps (adder s2 stage ~625 ps est) PASS;
5 storage: 512 b state flops (< 2 kb) PASS; 6 floorplan: no macros, util ~53%, square PASS; 7 clock: W entry, 1,693 sinks,
TT 109 ps, spread TT 9.4 / FF 8.9 PASS; 8 schedule: static, 0 edges.
47.52^2 variant hcoll_reduce_lane_s FAILED util 76% (synth std 1425 um2) -> dropped.
