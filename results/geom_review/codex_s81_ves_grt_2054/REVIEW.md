VEs W172.8 current GRT geometry review, 2026-11-01 20:54 PST

PASS-COND for normal prototype detailed-route continuation. Personally viewed
actual_GRT.png from current 5_1_grt.odb (read-only normal 4GB/2T dump exit0,
Intel1 unit3492914-1793594628). This is the current post-CTS/GRT design, not the
old placement. 167804 CSV rows, 97088 std / 30810 FF / 33172 buf-inv / 488 pins,
no macros. Clock/repair cells remain distributed across the interior; no macro
wall, sliver or collapsed cell pile. Pin-register strips follow the S/E faces.
The shape has room between placement islands, without a single dense stripe.

Current prototype GRT policy passes TT setup+22.74ps, FF hold+6.23ps under nominal
0/25ps policy. PG open0 in actual grt_post, original G1 GRT50overflow0 and measured
r2r385.51um retained. Entire172.8x345.6 outline diagonal386.39um keeps every
within-core source/capture displacement below405um even before path census.
Original source45122EQ, actual30810clock sinks equals964plannedleafmembership.

Continuation stays prototype, production_adoption=false. No RTL/pin/outline,
clock/reset or cycle changes from the passed GRT. Detailed route then actual
DRC/antenna/RCX/signoff+own routed EQ decides closure; final current051 proof is
required. Original source LEC uses explicit existing reset64; missing original
PROVENANCE is retained, not replaced by a claim about its generation commit.
