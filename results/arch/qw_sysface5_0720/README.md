# SYSFACE Boolean-cone source experiment

This branch changes only opt-in file-list twins; all original RTL and kits remain unchanged. No physical gate, route, or adoption has been launched. Current physical SYSFACE gates remain held by native PG failures in the separate intake packet22dee3655.

- Attempt7 flattened all combinational helper boundaries: actual native FAIL50 roots/max542; estimated depth834→721.8ps. Exact failure and source hashes are retained under native7. No runtime proof was claimed for this rejected source.
- Attempt8 flattened only the record module, with a kept module boundary: actual native FAIL25 roots/max82, all internal combinational sharing. Failure/source records are retained under native8.
- Attempt9 groups nine private record cones (508 generic cells) which each terminate at one FF data pin; every internal grouped node has exactly one actual generic consumer. Shared-driver boundaries and all1244 record FF instance lines are preserved. The parent’s4979 FF instance lines and all clocks/resets remain unchanged. Each group has a distinct kept hierarchy, preventing cross-cone sharing.

Actual full synthesis for attempt9 passes the current pinned native census:38018 roots, max32, no load violations or role errors. Full mapped depth is813.5ps/27levels; the worst stage has moved to calendar-L ev_port[1]→parent u_374/D. This remains above the600ps structural guidance, with no physical qualification or timing closure claimed.

Actual MU1/MU_HEAD1 wrapper protocol for attempt9 passes250777 cycles×56ports/1766 output bits from the first epoch edge, with no post-anchor mask. Boot/reset release and calendar readiness retain the accepted prior+1boot edge. Actual producer FFu_7159, D=prog_witness_slot, Q→record.witness_slot, was independently clock-mutated; the paired comparator failed at prog_tx_observed_v cycle1134. Both source-hash lists and raw logs are preserved. This is the unchanged registered protocol, not a new schedule or interface.

`gen_logic_groups.py` reconstructs attempts7/8 (the latter uses--record-only). `gen_record_cones.py` reconstructs attempt9 from the unchanged original record source. Its optional--parent mode is a future source experiment, not part of the attempt9 measurement. Original source SHA, selected cells/inputs and output SHA appear in cone_model.json. Full source staging hashes and current native-census/textbook code hashes appear in each native receipt. Physical flow helpers were not edited.
