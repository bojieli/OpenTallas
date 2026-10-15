# SFU controller broadcast as a registered tree (Claude hbm-group-B3, 2026-10-14)

Finding (audit 10-14): the 1,022 dynamic controller bits reach 16 lane mappers over ~1.7 mm with no registered
distribution. The mapper's edge 0 is a pure capture of those common bits (lane_j, the only per-lane input, is captured
beside it), so edge 0 moves into the tree without adding an edge:

    controller (BCAST1 out) --<=500 um--> 4 x ot_hgi_sfu_bcast_e0 (edge 0, one per 4 lanes)
                            --<=500 um--> 16 x ot_hgi_sfu_lane_map_e123 (edges 1..3) --> frozen ot_su12_sfu body

Same 4 registered edges controller -> body (BCAST1 / mapper4 / RET5 unchanged, nothing re-delayed), 2 x 500 um of
registered reach (covers a 1.7 mm span from a central controller), 4 x 1,022 capture flops instead of 16 x 1,022
(-12,264 flops a quarter); controller fan-out 4 x 1,022 wires instead of 16 x 1,022.
`ot_hgi_sfu_arithmetic_grid #(.BTREE(1))` selects it; BTREE=0 is the unchanged monolithic mapper.

Proof (tools/hgi_unit_tput/run_sfu_bcast_tree.sh, every output bit of 16 lanes every cycle vs 16 monolithic mappers):
- mut0: PASS 320,544 lane-cycle checks, 129,428 emits, 161,232 loads, 7 warm resets, live lane_j on lane 5.
- mut1 (lane 9 J flipped): FAIL 20,031; mut2 (pass one edge short): FAIL 319,536.

Physical: two new masters (node ~1.03k flops, e123 = mapper minus 1,022 capture flops); NO slot in r25gq v12 (SFU
unassigned) -> not routed; slot request to the HBM die lead with this tree geometry.
