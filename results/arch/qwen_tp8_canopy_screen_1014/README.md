# Source-separated VM canopy: bounded screen, not adoption

A finite screen rejects collection of all roots in the current 84.264 um strip. A concrete partial alternative enlarges the root station row and moves CLK_RX to a checked rectangle, then exports **one source response south per root before forking**. This alternative passes only the stated local, metal-only arithmetic. It does not prove the internal VM source transport, complete native canopy, actual pin/PG access, or timing fits.

The source geometry is actual g8 model SHA256 `5627b3ffe5e521994683d394ec4ed7c769725d20ee01164e22010d2ffccce921`. The current candidate inventory was copied before evaluation; its hash and all input receipts are in screen.json. Existing rejected M9 ranges remain rejected: the measured audit reports 5747 PG center conflicts, including first-column counts 77/72/78. No ranges are reused as assigned pins.

Actual g8 `elements.lef`, remote `/home/ubuntu/scratch-tp8-r10/g8/out/case/elements.lef`, has SHA256 `2bff608c1662fd72dce0f7603fa50f2b94e38ae729e2e7621e792100a65ab1f2`. Its VM OBS covers M1–M9; surrounding generated tile/band/slab/TT/CLK_RX/SEQ/embgw/PLL frames obstruct M1–M7. These are generated g8 frames, not qualification receipts for every native master. CLK_RX therefore blocks station placement and lower metal, while its generated OBS does **not** forbid M8/M9 routing above it. No M6 escape is counted through these M7-capped frames. M5 replacement views could change capacity only after their actual LEF, layer ownership and PG receipts are bound.

The source PHY abstraction is `phy_ew.lef`, SHA256 `2df57337d5de10428db914a80870d0bfe46e14fd02a1ae59c2026f4882ee292b`. Four 833.496 x 12000.120 um frames lie at x20.304 and x30931.632, in the W/E shoreline strips. Their supplied OBS declares M1–M4; that alone grants no extra die layer ownership. They do not geometrically intersect this central canopy. They must remain in the complete endpoint/layer budget, rather than be assumed all-metal walls or free routing layers.

## Exact PG source and conditional demand

The measured core PG audit records M9 VSS phase0, VDD phase4.545 um, net pitch9.091 um and width0.48 um. g8 `pdn.tcl`, SHA256 `bd814db534bdbc48dcc5ada2b805ea4109c9fe903ca4d56a48347f2bb7ec0d4c`, creates core M8/M9 stripes with width0.48, pitch9.091, offset0, starting GROUND. Macro grids have their own anchored offsets: CLK_RX M8 offset0.471; band1 offset2.772; slab1 offset6.710; TT controller offset9.083. Exact selected commands are preserved in screen.json and pg_anchors.json.

The calculation removes nominal PG metal and then retains **0.75 remaining cut capacity and the 0.60 gate**, without changing either. Nominal core metal-free fraction is 0.894401056. Wire/via clearance, actual signal-track phase, existing macro overlays and new station PG still require physical proof. The favorable bounds below use metal-only interval unions with the measured phases; they are not a routed capacity measurement or assigned track list.

Each conditional response is screened independently; request109 and common instruction380 (`ib379 + ib_go1`) remain present in all three scenarios. Response149/154 scenarios do not authorize metadata compression. Response233 is payload128 + literal key96 + phase8 + valid1; context/version remains unassigned, so even 233 is not a final maximum.

| Response bits | Aggregate source + instruction | Required single-M8 ribbon height | One-root H demand | One-source south M9 demand |
|---:|---:|---:|---:|---:|
|149|5148|1023.255 um|529|638|
|154|5308|1055.057 um|534|643|
|233|7836|1557.541 um|613|722|

For the 149-bit case, the earlier historical capacity model used 0.75 alone and required915.200 um. The current screen removes nominal PG metal **and** retains0.75 remaining capacity, requiring1023.255 um. The earlier PG-only0.894401 model required767.441 um. These are three explicitly different assumptions; none changes the0.60 cut limit or reprices throughput.

The aggregate requirements fail the existing 84.264 um strip. They include the remaining0.75 factor in addition to core PG metal removal, unlike earlier PG-only scenarios. Extra horizontal M6 cannot rescue this through the actual M7-capped frames. M9 is vertical, and the VM wall excludes all layers.

## Concrete partial repack and its finite limits

Move CLK_RX hypothetically from `(13670.208,16554.24)` to `(14700,15480)`, retaining its 412.536 um square. The proposed rectangle has zero hard-frame conflicts and eight existing relay/reset conflicts: rly_tt_c2_4, rly_tt_lc2_3, rly_tt_lf1_1, rly_rs_fault_2_37, rstt_rst_seq_ctlm_9, rstt_rst_seq_ctlm_10, rstt_rst_spine_50 and rstt_rst_spine_55. This changes no current job or clock. It would require new source-bound clock insertion/delivery and affected registered-hop proofs.

Place 32 hypothetical 129.6 um square stations at `x13294.8 +151.2*c, y16900`. After that clock relocation, they have zero hard-frame conflicts and 45 unique existing relay/reset conflicts. Their top is17029.6, leaving21.44 um before the VM S wall. Each station retains a151.2 um vertical routing bay. Geometry, conflicts and exact rectangles are recorded for review; no station RTL, physical outline, pin assignment or clock grant is qualified.

The phase-aware metal-only cut bounds admit651.099 H bits across the129.6 um row and at least758.700 M9 bits across each151.2 um bay. The worst conditional233 case has613 H bits and722 vertical bits, leaving38.099/36.700 bits respectively before unresolved demand. This requires **one** response escaping S through each bay, with its two half-endpoint forks deferred below the row. The old W/E fork ports need structural replacement and native proof; they are not adopted here.

Forking inside the same bay raises vertical demand to787/797/955 bits for the three scenarios; all exceed758.700. Joining two neighboring responses on a horizontal segment raises demand to678/688/846 bits; all exceed651.099. Thus merely increasing station height while retaining collected or doubled branch traffic fails. Source placement and the actual downstream fork map must establish that no such shared cut occurs.

The candidate still lacks internal transport from VM band sources near y18376 to the S face at17051.04. The die-lead inventory already records optimistic register lower bounds exceeding13 remaining band bays. External station geometry does not supply those internal registers, clocks, enable/freshness semantics or their channels. It also does not resolve the existing joint-band cut1.062967, which excludes root gather/export. Those are finite outstanding obstructions to claiming the complete canopy fits.

Validation read actual generated g8 LEF/PHY/PDN, preserved hashes and selected macro anchors, reproduced the three conditional demands, and checked every proposed rectangle against all existing model instances. No full planner, physical job, asynchronous clock scheme, metadata compression, threshold change, live-job mutation or pin grant was introduced.
