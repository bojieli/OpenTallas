# INTENT SHEET: QC sle_stm / slw_stm (VIS-TRIAGE-QC, COORD 02:1x intent rule)

Base plan: aace4c2668fc. Drawings: INTENT_sle_stm.svg/.png and INTENT_slw_stm.svg/.png (same dir). ROM read-port xy per type: delta/QC_CS_stm_rd_out_xy.json (sha 5a2a1840).

## 1. Dataflow chain (RTL qfd_dv_slice_tload + qfd_dv_table_rom_loader inside qfd_dv_s6_stm; plan buses)
- Request `treq` (9 b) lands in one face register -> loader -> 4 x 4096x266 mask ROMs (m0..m3) read 88 times per load.
- ROM `rd_out` (4 x 266 b) -> loader -> VM join (mux with the stream table write s_* 1024 b) -> `tw_we/kind/addr/data` (1051 b) out. Stream in and table write out both use the N face window (2103 b, x 4-366): ROM data is POINT-TO-POINT into a mux that lives at that window.
- ROM pairs m0-m2, m1-m3 share address/enable fan-out (26 nets each): broadcast control, light.

## 2. Timing-critical pairs
- ROM clk -> rd_out -> loader/join -> tw register: slw_stm_v3 TT -912.67 = ROM access 595 ps + 5 logic levels ~380 ps (975 ps > 833 ps even at zero wire: logic depth, needs Form A ROM stage) + ~450 ps of wire (616 um Manhattan ROM pin (441,693) -> endpoint FF near (273,1141), zig-zag x 211-444). The placement removes the wire part only; DIE-QC-97 owns the Form A / Form B station and the FF hold (H-nongeom).

## 3. Hand layout (drawing)
- All 4 ROMs in the N band (rd_out centroids y 1023-1321) against the N 2103-b window, flipped MX/R180 so the rd_out pin edge faces N (all four orients are on-track for this ROM: H = odd x 0.024).
- m0/m2 and m1/m3 adjacent (address pairs).
- S and middle of the type left to the stream glue and ft pass-throughs.

## 4. Search role
Structure fixed by hand (ROMs at the N window, pins facing N: --face-anchor N window weight 266 per ROM); the search only chose which ROM takes which of the 4 N slots and legalised; core_place --no-search scored it: 0 EQ / overlap / timing / station violations.

## 5. Rationale (row note)
The ROM read data is the only wide link and its consumer (loader + VM join) sits at the N stream/table-write window, so the ROMs move from mid-type (y 595-690) to the N band with read pins facing N; this cuts the ~450 ps wire share of the -912 ps path (logic depth stays: Form A). RUDY H overflow 39k-87k -> 0-1.6k, route_supply p99 1.01-1.21 -> 0.62-0.84. ROM-ROM pair bit-mm 2.5 -> 4.3 (deliberately traded for the window hop).
