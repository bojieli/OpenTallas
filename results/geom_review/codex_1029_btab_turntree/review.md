# Independent BTAB turntree diagnostic continuation

REPLY [BTAB-TURNTREE-GRT50-0251]: PASS-COND for ONE actual CTS/GRT, no detailed route. Type qfd_dv_s8x_btab__turntree, native kit sourcef28e60fc9464, AP7335febad21d.

Personally viewed placed turntree PNG. Four SRAMs form2x2, with open32um horizontal crossbar and48um central street. Logic is clustered near S/E pin bands; no blocked macro wall. Static channel_h2.604 is a narrow edge projection at the upper-right macro corner. Actual signal global route on exact3_place.odb used M2-M5,.25capacity adjustment,50iteration budget and converged at extra iteration8:0overflow on every layer,17.52%total utilization,12096nets/368251um. Thus the estimator alone does not justify changing macro/pin geometry.

Inherited scoped full reach387.85um/0above405 and319clock frozen-body/halo/hardblock/PG clearance support this continuation; no new measurements of those are claimed here. Conditions after CTS: actual whole-graph reach and clock-body legality, actual clock slew and unchanged833ps/60psTTsetup/25psFFhold. Existing failed AUTO record stays failed. Sparse logic/fixed ABI remains a slot constraint, not a newly added gate or interface change.
