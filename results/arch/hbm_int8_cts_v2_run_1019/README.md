# INT8 exact ONE CTS V2 diagnostic failure

The ec8bf662d exact ROOT grant ran once through unpinned ot-run on ot-epyc8, unit oth-ubuntu-1830026-1792443617 (16 GB, 8 threads), actual exit 1. All 77 manifest files including 15 inputs and the pinned image preflighted identically on ep6/7/8. The approved kit, source, geometry and timing constraints were unchanged. No synthesis, data repair, GRT, route, gate, submission or adoption occurred.

The immutable PG-checked checkpoint was saved before reporters. Both native TT/FF reporters, raw export, conductor proof, strict fanout and checkpoint immutability passed. Signal identity refused `new cell is not positive buffer clkload9`: actual native INVx2 has an open output. No cts_only publication exists; status remains INCOMPLETE. All original failures and files remain. A separately assigned owner is reviewing physical unary clock-load semantics and checkpoint rendering; this packet changes no checker or grant.

All 253 new cells have actual native endpoint records in new_clock_graph.json.gz. Starting at all 2782 native FF clock pins, backward graph traversal proves every new input/connected output belongs to the clock graph; all 110 open-output load inputs remain counted. This is ownership evidence, not a replacement identity PASS. New native area is 75.85974 um², input capacitance 530.839298 fF TT, including 110 open loads at 13.31154 um² /194.752118 fF. Original 2782 FF and functional source ages remain: reset2 samples, low2/high3, +0 functional edges. Full graph has 11,660 drivers/22,677 endpoints and strict max24/zero violations; all open loads retained, no name exemptions.

| Native metric | TT | FF |
|---|---:|---:|
| All 2782 clock-pin active-edge wire spread ps | 9.871395 | 9.475434 |
| Clock-pin active-edge wire arrival min/max ps | 152.623845 /162.495240 |124.154729 /133.630163 |
| Clock-pin maximum rise slew ps |17.742359|14.986652|
| r2r max/min slack ps |+127.34 /+4.94|+312.94 /-7.12|
| i2r max/min slack ps |+565.14 /-15.99|+535.36 /+13.51|
| r2o max/min slack ps |-275.41 /+649.40|-120.68 /+527.30|
| External reset max/min slack ps |+702.14 /+10.32|+681.70 /+39.07|
| Native async recovery/removal max/min slack ps |+575.76 /+25.01|+635.52 /+9.75|

The FF -7.12 ps ordinary hold path is FF slice$13235/QN → INVx1 parse_blif$37773/Y → FF slice$12201/D, one combinational inverter. Native path launch clock118.92 ps, capture131.62 ps, CQ34.87 ps, inverter5.77 ps, next net0.02 ps, data159.59 ps, required166.70 ps; uncertainty25, CRPR-1.97, libraryhold12.05 ps. Path-specific transition/min arrivals differ from TSV active-edge wire metrics. Full native worst paths for all 20 class/corner/delay combinations are retained, including asynchronous groups within r2r.

All electrical violation rows are retained without top-N filtering. TT slew: 2443 boundary,150 native reset/set,37 internal; FF:2445 boundary,22 reset/set. Worst TT internal D350.29 vs260 ps; reset368.81 vs260 ps. Output worst slew TT1839.69 /FF1608.73 vs260 ps. Each corner has1070 output INVx1 capacitance violations: limit46.08 fF; worst114.80 fF. Fixed80 fF output load already exceeds the native output limit; wire adds34.80 fF in the worst case. Clock-reference compensation cannot waive physical capacitance/slew. Boundary role means the native net touches an actual top port, not that the violation is harmless. Clock rows have no violations in the emitted complete electrical reports.

Native PG conductor proof covers3,322,922 shapes,61,845 vias,3,156,420 cuts and21,246 terminals, with zero wrong supply/short/uncovered contacts. Original placement and full native master census passed before checkpoint. Accepted237.6×129.6 um geometry is unchanged, whole-outline367.2 um reach bound, no macros; legal placement was checked. Parent/neighbour matched IO, electrical cleanup, hold closure and ROOT personal PNG review remain unqualified. No token or throughput claim follows.

Remote authoritative snapshot and every collected local hash are in receipt.json; the large raw/ODB/metal files remain immutable on the fleet. An independently admitted read-only native cost parse (unit oth-ubuntu-1861278-1792443811) returned actual exit0. No process remains live from this lane.
