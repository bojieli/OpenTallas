# QC R26 real entry inventory

Plan geometry only; no branch or hard-core interface is changed. The R6 mesh reaches 360 of 377 old plan entries within 450um; 17 require staged delivery. tt_ctlm has an existing-hole four-segment candidate with maximum hop429.354um. UCIe has no chain through existing declared holes within450um to its old centre target.

The proposed coll_core 8.64um window and5.4um halo are fully in its host and clear of opaque macros. The nominal2.5um riser and0.54um stack span fit inside the window; die-metal shields and PG still require the actual importer census. This window is not declared and does not solve the UCIe endpoint contract.

Four PHY targets use type centres despite actual canonical LEF clk pins on M5 at macro edges. phy_clock_pins.json records the actual pin rectangles and missing origin/LEF mapping. SerDes centre-to-real-pin delta1186.782um and UCIe501.108um make direct use of those centres invalid. The actual LEF/origin/orientation contract must be bound before branches can be emitted.

Island availability here means plan geometry only. Type kit reservation and full8.64um/halo checks are required for selected existing holes; small existing hole rectangles alone are insufficient proof. R6 siting PASS remains conditional and its all-R0 PG orientation is superseded by the fresh canonical row export.
