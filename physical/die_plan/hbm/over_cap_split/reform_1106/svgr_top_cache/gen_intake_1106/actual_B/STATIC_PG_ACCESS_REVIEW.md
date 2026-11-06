# Static PG and clock-access review of actual TOP A/B

Verdict **PASS-COND for the static interface**: no VDD/VSS name, role, or layer/connect mismatch found. This is not a floorplan PDN, continuity, DRC, IR, or timing pass. Opened STATIC_PG_ACCESS.png, drawn from the actual staged LEF rectangles.

| Actual master | VDD M4 rectangles | VSS M4 rectangles | Horizontal PG span | PG rectangle height |
| --- | ---: | ---: | ---: | ---: |
|128x256_m1_r0c0_g256|36|35|91.2um (x0.300..91.500)|0.096um|
|128x256_m1_r2c2|53|53|94.224um (x0.300..94.524)|0.096um|
|1024x256_m2_r2c2|92|91|174.144um (x0.300..174.444)|0.096um|

Every VDD port is INOUT/USE POWER; every VSS is INOUT/USE GROUND. All PG rectangles are on M4. Same-net PG row pitch is0.768um; VDD starts y0.384..0.480, VSS y0.768..0.864. Complete exact rectangles, first/last coordinates and OBS boxes are in STATIC_PG_ACCESS.json. The new macro uses the same PG layer/name scheme as the original SRAMs; MY preserves its symmetric0.300um X inset.

Actual pdn.tcl binds ^VDD$ and ^VSS$ to CORE/VDD/VSS, defines top M1/M2 follow-pins and M5 stripes (width0.12, spacing0.072, pitch4.32, offset2.064), with M1-M2 and M2-M5 connects. Its default macro grid uses halo2um, grid_over_boundary, and explicitly connects M4-M5. Thus the macro PG layer is the lower layer of the requested macro connect, and the supplied M5 top grid provides the upper layer. PG halo2um stays within the reviewed4.32um placement halo. A/B use identical pdn.tcl. pg_connect.tcl supplies ot_pg_connect_all and the actual ot_pg_require_bound check for cell-creating stages; no dedicated new voltage domain or new power-pin spelling is introduced.

The explicit M4 PG rows overlap the M4 interior OBS projection; the same pattern occurs in the two original SRAM families. Named PG pins are present and the requested macro grid targets their layer, but this static review does not prove that generated via enclosures/obstruction exceptions will be legal. Check actual macro vias and opens after the first adopted floorplan.

Actual SRAM clk is USE CLOCK on M4, rectangle[0.000,0.768,0.024,0.792]. Under cache MY it is on the east edge. The PG rails start0.300um from the edge, leaving0.276um from this clock rectangle to PG metal in X; the M4 interior OBS starts0.072um from the edge, leaving0.048um between clock metal and the OBS boundary. This provides an exposed edge port, while actual signal-via access/DRC remains unbuilt.

All three masters obstruct full M1-M3 and interior M4 only; no M5 OBS exists. The unchanged top stream_clk pin is M5 at(151.176,319.68), size0.048x0.48. Over the lower programme SRAM this is local(87.346,69.684). Its projection crosses M4 PG rail rows, which is a different metal layer; absence of M5 LEF OBS permits access in principle but is not proof of clearance to the eventual M5 special wires. Actual clock versus M5 PDN shape/via clearance must be checked in the adopted floorplan.

Remaining physical qualifications: actual pdngen M4-M5 vias for all VDD/VSS rails; every PG ITerm bound to the correct power/ground net; continuity and signal/PG DRC including the top clock point; then propagated-clock TT setup/FF hold and the strict measured functional-cell cap. No P&R, new heavy job, fixture edit, or new proof was used for this review.
