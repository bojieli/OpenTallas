# BF tag-stage distribution, source preparation review

Image: results/codex_s81_ce12_1029/bf_tag_review.png (personally viewed).
Source: optional TAG_GROUPS 4/16 in ot_v41_bf16_lanes3 and ot_v41_bf_col.

Verdict: PASS-COND for source preparation and fresh synthesis. No P&R or STA
approval is implied; the mapped sink census and complete floorplan/clock plan
must be reviewed before physical work.

The actual retained V1 accumulator flops form sixteen small clusters. Per-lane
final-stage replicas can sit close to them: maximum cell-centre Manhattan
estimate 29.403 um, with 32 accumulator endpoints per copy. Four-copy groups
span separate clusters; a median-only proposal put two source clusters in ROM
bodies. That proposal was revised before any physical job. The displayed
four-copy sites clear the actual ROM bodies by >=6 um, and their maximum
centre distance is 198.387 um. Four-copy fanout is 128 accumulator endpoints.
Both alternatives keep the original source clock, same D-stage latency,
unchanged arithmetic, and zero new cycles. The original macro-wall/channel
problem from the failed GRT is still open; replicas do not constitute its fix.

The estimate covers the identified accumulator-control endpoints, not every
consumer of all thirteen tag bits. A new clock tree must include +39 or +195
FF (+0.072%/+0.362% sinks). Never copy the old fixed sink list. The actual
prefix-to-copy and all tag-consumer paths need normal reach and timing checks.
PG continuity/clock balance cannot be approved from a source-placement estimate.
