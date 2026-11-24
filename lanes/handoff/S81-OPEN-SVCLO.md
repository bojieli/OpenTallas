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
