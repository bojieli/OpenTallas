# OPS local stage physical review
Reviewed actual captured 16 SRAM placements (172.824 x41.064um each), original 760.32 x233.28um outline and candidate register guide rectangles. Image: review.png.
PASS for guarded synthesis and subsequent early-placement inspection: write cohort chunks occupy three interrow streets per four-bank column; read captures occupy west pin channels adjacent to each SRAM. Macro placement, track phase, halos, pin faces, PDN and clock source remain captured native values. Existing F4 bounded chains stay enabled. Register guides avoid macro halos; no across-column write-data relay is introduced after the new local stages. Native synthesis survival and actual early placement remain required before detailed routing.
A/B pin-cycle prices and parent-owned IO hold debt are recorded in README and SOURCE_EVENT. No profile activation or physical qualification is claimed.


## Actual H250.56 revised form
Parent-reviewed review_H250_actual.png shows all three actual corrected pin maps (A0/A13164, B3146), all16 SRAMs, three write channels per column and27um west read guides. Same clock centre380.184/61.68 remains in clear first interrow/centre-column corridor. No pin, macro, halo or guide collision. Row moves0/+4.32/+8.64/+12.96um preserve native M4/M5 phase exactly.

Native floorplan/PDN whole-site capacity is36796.4208um2 after halo union, versus23807.3904 in failed old slot. Functional stdutil33.0–35.35percent; maximum local FF guide34.283percent. Source EVT helpers compare every generated centre to the actual parent table with the selected factory emitter; all six GEN passed. Parent approved fresh PLACE all6 with normal reset/LEC gates; inspect actual placed images/cap/util before CTS/route. No canonical POR/profile adoption or parent-program claim.
