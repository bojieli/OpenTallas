# E2 symmetric clock distribution successor

RW8 actual CTS failed glue clk TT spread110.7ps (870/881 boundary sinks), no closure claimed. This kit replaces only that existing root topology with a symmetric center-fed spine; it leaves the other22 declared roots and20 independent hard entries under the original hybrid checker and exact hard-view clock reference SDC. Both variants use WR3, unchanged RTL/parameters/ports/output edges; ring exact+three mutant witnesses are committed967833086.

SAFE before gate: 1 PASS unchanged pin/landing stages; 2 PASS topology repeaters<=150um, same registered data paths; 3 pending fresh mapped census (RW8 max32), no RTL change; 4 PASS same pipelining; 5 PASS same SRAM storage; 6 PASS inherited43.2 lattice/full cell channels/734.4square; 7 FIXED pending CTS symmetric spine with actual bound Liberty insertion refs, unchanged80ps TT/FF within-region and.03hold margin, no bypasses; 8 PASS static WR3 schedule, zero additional edges.

Native census must pass before layout. PNG and full CTS/GRT review required before submit. Old RW8 failures remain immutable.
