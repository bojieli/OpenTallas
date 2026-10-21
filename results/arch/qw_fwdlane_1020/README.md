# QW-FWDLANE 10-20: Qwen compute forwarded-lane family (qfd_fwd_lane_family) -- bind coverage on the g5 die

Input: dv2f20g5r2b strict bind (ot-epyc6 mu-die-qw/dv2f20g5r2b/chain/bind.json, copy bind_dv2f20g5r2b.json):
175 masters / 20 bound; 690 forwarded-lane instances (landh0 508, landh 91, rlyh0 91) over ~130 per-frame
masters, 627 with NO view (one GEN master per width x direction x frame).

Tile side is DONE -- no new routes are needed:
* Class binding (tools/qwen_split/fwd_lane_classes.py table on the g5r2b out/pins, class_table_g5r2b.json):
  220 masters <= 600 b -> 56 classes; every used class with instances has a CLOSED view on main
  (668 instances), after this branch adds qfd_landh_1_EW_65x30 (closed 10-18 f2-9ddc1acf2, TT +229.33 / FF +27.04,
  record never merged; ot_qfd_land g_lane RTL unchanged since). rlyr_1_EN / rlyrl_1_NE classes: 0 bound instances.
* Width 1088 (22 instances: landh0 20, landh 1, rlyh0 1) has no class: GEN must split each into 2 lanes <= 600 b.
* D8 alternative for landh0 (LEAD-QW 10-19 D8 adoption): fwd_map_g5r2b.json composes every non-CB16 landh0 width from
  closed D8 views (1/3/10/32 d8, 107/116 d8g, 151..183 d8s SRAM slices), 211 instances -> 550 tiles, no tied bits;
  514/516 (269 instances) are the CB16 qfd_c_land_w257/r258 pairs (CB16 lane).
* GEN obligation (die chain, QW-G5RELAUNCH): emit class master + orient + class frame (fwd_lane_classes die_obligation),
  or the D8 composition for landh0 with its mod-16 calendar; the emission branch (mu-dq-fwdclass/fwdplan) was never pushed.
