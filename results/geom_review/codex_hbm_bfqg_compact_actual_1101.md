# Native BFQG compact actual GEN review

Proposer personally viewed `results/hbm_bfqg_compact_kit_1101/actual_gen/actual_gen_geometry.png` and parsed the adjacent actual model before any physical job. This is actual generated pins, macro placement TCL and SRAM LEF geometry, not a reused old-shell drawing.

Eight 94.824×41.064 SRAMs occupy two four-bank columns inside259.2×220.32. Their4.32 halos leave clear peripheral rails, central vertical channel and horizontal inter-bank streets. Banks6/7 use LEF-supported MY. Actual central clk(128.664,146.88) is clear of macro halos. All20 native clock ports remain:19 declared lower-edge shapes y0.24 plus the interior clk; no new N clock entry or virtual-centre substitution. All1340 pins are retained.

This geometry supports measuring ordinary placement and actual pin/FF reach. The model source's low standard-cell fill is INFO under the existing macro-dominated rule (macro54.548%); actual fill/empty bins still require the placed result. Placement must preserve actual source clock groups, all SRAM instances and public boundary captures. Actual row legality, pin reach, internal405um reach, channels, rooted clock graph, PG and timing remain unmeasured. No parent16-slot/tap or timing credit carries over. No CTS/GRT/DRT/signoff release.

Independent geometry review requested before one normal PLACE-only diagnostic. Fresh canonical native source LEC must explicitly request reset4; old8650EQ is a frozen-source component reference only. No physical job launched at this review.

Independent geometry_disk personally VIEWED/parsed and CONCURS PASS-COND for one normal PLACE diagnostic on this exact K. Central macro gap34.992 leaves26.352 after halos; W/E rails12.96, top6.252, bottom12.972. Tightest inter-row gap8.664 leaves0.024 after halos; place logic in central/outer rails rather than between macro rows. Lower-edge clocks require actual own-leaf reach later. No CTS/GRT/DRT release.
