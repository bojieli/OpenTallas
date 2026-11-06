# KV SYS_SD origin corridor candidate

Frozen source: epyc5:/srv/opentallas-scratch2/claude/dkv80rf/kits/gen/kv3_sys_SD_vB/run/results/asap7/dp_kv3_sys_SD/base/5_1_grt.odb. Read only through native OpenROAD ODB API. Exact current type geometry and actual origin cells/macros are included. No live kit edits or new route.

Actual s0[107.136,29.43] -> s1[1868.4,125.01] spans the bottom of the single PHY wall[17.28,54,1866.24,1026]. TT report gives -160.05ps with many wire buffers, launch clock251.43ps and capture clock on clk_t5 with real -80ps source latency. No clock latency adjustment is proposed.

A405um planned-hop form requires four internal sites between west selected START and east s2. Existing s0/s1 supply only two; geometry preparation therefore cannot solve this within the existing count. KV owner explicitly chose two added complete START epoch/control stages, +2 boot cycles, and owns RTL, reset/phase alignment, latency ledger and proof. Original sf negedge/strap edge selection must remain before the selected epoch is relayed; simply delaying p_start before sf is not an assumed equivalent implementation.

Candidate internal sites in order: added0[559.764,19.98], added1[928.962,19.98], existing s0[1298.214,19.98], existing s1[1667.412,19.98]. Existing s2 moves to[1876.5,180.09], pd stays local at[1876.5,182.52]. The original named receiving clock domains remain real domain semantics. Helper preserves actual PHY footprint plus5um route clearance and89 current macro/band/clock/reset reservations. Planned hops369.204,369.198,369.252,369.198,369.198um. New stages must carry the complete selected START epoch/control bundle with correctly phased reset; coordinates alone establish no timing/phase pass.

sd_origin_review.png was rendered and directly inspected. The chain runs through the bottom corridor then turns north through the east corridor; endpoints also clear declared reservations. This is a planning candidate before the source event and mapped trial, not an adopted plan.

Separate CDC coordinate query: native rd_bin[0] FF bbox[1889.622,129.06,1891.026,129.33]; p_tx_d[56] FF bbox[1808.514,51.3,1809.594,51.57]. Center Manhattan distance159.030um. This is a distinct timing problem owned by KV. A similarly named rd_bin...__50 instance is a TIEHI, not the queried FF.
