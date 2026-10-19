Trim successor of ea591f72d: default-off isolated native head

Only USED_BITS SRAM output lanes retain capture FF. Unused high native output lanes are zeroextended. Actual macro master/pins/read/write clock/depth/masks are unchanged; no data or release edge is added. The old pretrim source is preserved as a test reference with only module-name suffixes; source_receipt.json proves removing suffixes reproduces ea591f72d bytes exactly.

The old CONTROL_SAFE0 pretrim head and new CONTROL_SAFE1 trimmed head compare every one of30output signals (74totalports),5794 cycles out of6000, all5classes and a warm dirty-history reset: PASS. Actual outerclient2491242 rc0. Expanded generic noabc census2491633/audit2496576 rc0:43510cells,6719FF(-172 paddingcaptureFF vs6891), same13native32x64+2TLS128x64, one actual nativeclk, no inputoverload. All83unsafe driverroots and201unbranched D3/4/5 holding candidates remain.

Seven additional final dmd-tail captures have no consumer: o_p[2:0], o_final, o_first8, o_ifirst, o_mc. They still require removal/zero-capture before a no-ghost assertion. A source OBSERVE_MASK per bank with honest zero write mask is one bounded option, MODELonly; measuredFF count after such a change is not yet available (6712 provisional arithmetic).

This trim source has a separate source receipt. The older ea591 fullW10 and numerical TLS mutant results do not retroactively test these bytes. New trimfullW10 unit2494837/session85090 is LIVE ep6 /srv/opentallas-scratch/claude/qw-head-controls-trim-1019/trim_positive, local scratch/qw-head-controls-1019/trim_production.log. Collect explicit actualgoldenPASS and outerexit. Do not restart its progressing build.

No reset RTL was written. Provisional55FF forest model is before useful-control replication; native reset1603/selector/FPU/holding/area/reach/clock/PG/TTFF remain open. No gate/nativeview/parent default/adoption/token claim.
