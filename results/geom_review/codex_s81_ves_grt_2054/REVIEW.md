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

CORRECTION / HOLD 2026-11-01 20:55 PST: the diagonal386.39um statement above is
Euclidean and does not establish Manhattan reach. Manhattan outline bound is
518.4um. Original G1 measured385.51um remains historical; current GRT full
connected r2r census has not yet completed. The premature trial queue row was
withdrawn append-only at coord0a5b5a8fb774 before any observed ot-run client.
Current native connected geometry dump queued4GB2T (Intel2client3622256); current
r2r census and review disposition are required before resubmitting DRT. Original
review text preserved, its DRT release verdict is superseded by HOLD here.

CURRENT CONNECTED CENSUS / RELEASE 2026-11-01 21:10 PST: actual current5_1_grt
native geometry/connectivity dump completed exit0, Intel1 unit3742694-1793595352.
Current main geom_rules.Design+r2r_metrics over that exact dump gives full
Manhattan r2r385.51um, 30425captures, 0captures>405, 0combloops, no missing macro
models (macrofree). Worst mv$_DFF_PN0_→e_lo[21]$_DFF_P_. See current_r2r.json;
raw dump coord/tmp/codex-s81-ves-2042/current_geom.tsv. This replaces the wrong
Euclidean bound with an actual full connected census. Current picture findings
remain valid. PASS-COND normal prototype detailed-route continuation reinstated;
old premature queue withdrawal and incorrect original reason remain in history.
