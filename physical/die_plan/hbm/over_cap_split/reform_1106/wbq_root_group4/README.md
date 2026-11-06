# WBQ_ROOT group-of-four source/model proposal

Default-off define OT_WBQ_ROOT_GROUP4 groups the same eight stores into two children with LANE_BASE=0 and 4. FACES=1 retains each existing 256-bit fifo_clk WD capture once. All row state, SRAM, FIFO, synchronization, reset, controls and parent arbitration remain on their original edges. No GEN or P&R is authorized by this proposal.

Each 250.56 x 138.24 group contains a candidate 2 x 2 macro grid. Actual core is 241.92 x 129.6; excluding four 103.464 x 49.704 macro-plus-halo rectangles leaves 10782.533376 um2. Four actual prior mapped stores total 3401.16408 um2, or 31.54% of that free area. Counts are additive source estimates, not a new mapped/placed group. The old 103.68 x 60.48 tiny-helper geometry is invalid: using its actual 95.04 x 51.84 core minus macro area alone yields about82.3% utilization; the full halo cannot fit the tiny core width. Its prior35.78% figure used the wrong denominator. Historical evidence is retained.

The two group rectangles require a 501.12 x 138.24 candidate ROOT extent. The unchanged soft controller is 571.41936 um2/770FF. Its west/south/full-controller bands and PG fit are still parent work, so this is not a full parent-fit pass.

Native group inputs total1112bits and outputs1156bits. native_clock_cuts.json indexes every lane and packed range. FIFOhead is a mixed cone: fifo_clk-written storage selected by hbm_clk read-pointer FFs, consumed by hbm_clk root arbitration. fifo_empty and accepted read are hbm_clk. This is not a single-clock output blanket. Existing raw10/14ns and fullfamilycommonclock fixtures are reused for the new proofs. Fullfamilydistinctasync qualification is expressly absent.

Compile the optional composition with OT_WBQ_ROOT_GROUP4 and OT_WBQ_ROOT_STORE_FACES; compile from ot_wbq_root_stores.sv, ot_wbq_root_store_leaf.sv and ot_wbq_root_store_family.sv with existing CDC/reset/face-register/SRAM definitions. The group helper is declared in store_leaf; its FACES branch uses the existing store_face declared in stores. No canonical recipe or source-default selection was changed. Macro homes in the drawing are candidates; actual generated sites/grid, pins, CTS roots and parent/PG geometry require a later reviewed image.

The new grouped RTL passes both retained native benches: raw asynchronous10/14ns6883checks/768writes and fullfamilycommon10ns9636checks/768writes, zero mismatches. Default forms also pass. Packed WD lane swap, wrong LANE mapping and removed WD capture mutants each cause768mismatches/768writes. Exact inputs, build/simulation logs and hashes are under proof/. There is no new wholefamilydistinctasync qualification.

Fresh isolated mappings of both LANE_BASE=0 and4, FACES=1 completed under normal4GB/2CPU admission. mapping/mapped_counts.json records actual standard cells/FF/area excluding four SRAMs and $scopeinfo metadata. Neither mapping is placed/CTS/routed/signoff; parent controller is excluded. Preserved mapped JSON bulk paths and SHA256 are recorded there.

Default hierarchy compatibility fix: the default root and family are byte-identical to the old source after preprocessing. The original g_lane paths are preserved. The group branch now requires OT_WBQ_ROOT_GROUP4; no trailing parameter changes remain. Native helper module/parameters and its mapped source are unchanged.
