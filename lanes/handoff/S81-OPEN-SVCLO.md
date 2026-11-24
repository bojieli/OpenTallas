# S81-OPEN-SVCLO handoff (Opus 5.5; started 11-23 19:11 PST). Brief: localhost scratchpad s81_open_brief.txt.
Scope: rc25 SVC-LO-START-INTERIOR (taken over from S81-ALLFIX-SVC). Family lane under S81-ALLFIX-INT.
Work dir: E9 /srv/opentallas-scratch2/claude/s81-open-svclo (tool/svc_lo_start_interior.py b77f35d5f692, measure.py, tail_mine.sh = INT tail_e9.sh writing to my dir, scope.sh = probe-only strict bind of the 8 lo types, B1 exact elab reuse).
## Findings
- B1 ae3101241d6b already has the LOSTART chains on all 8 lo types (measure_b1.json): START/edge findings 0, raw over 0.
- INT c7a step 14 svc_tap_inv (ops_tapinv 912e846dd5c8) replaces clock/taps on the lo types -> START raw_reset pointers stale: edge_reach t1 30, t6 4, t7 43, rs_w 6 (>405 um, worst 2233). Steps 01-13 clean.
- Row = LOSTART tool as compose TOOL step after svc_tap_inv: c7a/16 aebbf78417d7 -> c7a_lo/p0_lostart.json 5473314000a2, 15 ops (cf6cccdfd3ef), 8/8 FIXED, raw over 0.
## Units
- tail+PRE on p0: E9 oth-ubuntu-1389819 (tail_c7alo.otrun.log, out tail_c7alo/)
- scoped strict bind on p0: E9 oth-ubuntu-1427451 (scope_p0_*/)
## Next
- measure tail output (tap_offset_cover fill may re-touch taps); scoped strict on tail plan; post ROW-REBASED + recipe step to INT. Frame v3 (f3/f4a) changes 0 svc_lo types (diff on E10).
## State 21:45 PST
- Posted the invocation (21:0x) + ROW-REBASED PRE (21:1x) + scoped strict status (21:4x) to S81-ALLFIX-INT.
- Private tail on p0: p4_fill a39888d9ebe1; TAPOFF census 395/395; PRE FAIL 148 (ANCHORDRY 19, DEADIN 1, GEOM-STATION-IN-CORE 128) = INT c7a tail 90698b2ec067 (148), 0 svc_lo findings. The lo types after the tail: START/edge findings 0, raw over 0.
- Scoped strict (scope_tail_a39888d9ebe1): refused only by the compose-level DEADIN (stale defines vs the B1 elab). Asked INT to put the 8 lo types in SCOPE_TYPES of the c8 gate (fresh elab).
- Open: read the c8 gate scope_bind.log for the lo types when INT runs it. If it refuses on svc_lo, fix it here.
