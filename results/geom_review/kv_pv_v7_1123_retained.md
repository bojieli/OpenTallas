# KV D28 pv_v7 retained pre-DPL placement

Inspected the exact 3_4_place_resized ODB from the D28 pv_v7 attempt that failed at 3_5_place_dp. The read-only renderer found 29 macros, 14,152 pins and 43.6% standard-cell fill. Images are at intel1:/srv/opentallas-scratch2/claude/kv-plan-r6/kv-d29-pv-v7-review/{floorplan,density}.png.

Four long macro columns reach close to both side boundaries. The central passage jogs around the inner join and landing blocks. The density image shows local concentration in that passage, along the lower macro interfaces and near the top-edge pins, with wide quiet areas elsewhere. Retained pre-DPL copper and row occupancy do not show a clear escape for the pad-delay runs. The exact Tcl crash occurred in dly_spread d106a0da0ae1 when it read unset nhop. The guarded Tcl tool fix lets DPL report an unroutable run, while the physical correction comes from splitting the family and shortening pad and relay paths.

**Verdict FAIL for routing this D28 form.** Carry pv_v7 into the D29 Row B split with PADRAM and locality review. The reviewed checkpoint is pre-DPL and has no CTS or routability result.
