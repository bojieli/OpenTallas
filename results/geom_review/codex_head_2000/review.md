Picture: review.png, viewed by Codex.
Verdict: PASS-COND for ONE placement-only structural trial; no route/STA.
Baseline FAIL: an unblocked void around x85-140/y95-135 splits the sink cloud; E ports lie inside the old outline; o_d crosses to the wrong face.
Fix: use reviewed r7 pins (E on actual285.12 edge, o_d entirely S toward consumers) and density from measured movable utilization25.739% plus4 percentage points, rounded0.30. ROMs remain in N band with4.32 halos and centre island remains fixed. Dataflow placement should spread into the void and shorten long leaf spans. Pin boundaries retain layer/pitch; clock/PG contracts unchanged. Must render resulting placement, inspect sink spread/reach and master-plan compatibility before any CTS/route.
