HEAD plan-derived schedule constants, 2026-10-29

New die-local tool tools/s81_head/regen_schedule_constants.py emits all327 raw
lane costs via schema.Plan.lane_latency (R8 included), optional exact per-port
CA additions, JSON and SV constants. No bind/source/START dates are invented.
HEAD transport law follows intel2 die-head-26/a1_price.py: longest spine path
plus twice the worst gather leg; HOST and head_lep legs stay separate.

Frozen rawhk5:
  longest spine79 (slice5,W), worst gather54(m0S_rx), transport187.
Current hk5 CA2 table:
  spine170, gather80, transport330. host_tx58=40+18, host_rx57=40+17;
  head_lep_landing7=5+2, head_lep_fault_return6=4+2.

Latest rawhk6 parent beforeFT has identical187 transport. Its actual latest
hk6_ft candidate changes30 lanes, aggregate72lane-cycles. The critical path
changes only6: spine79->81, gather54->56, transport187->193. Aggregate72 is NOT
end-to-end cost. HOST/LEP lane ages unchanged by this FT-only delta.
Applying the SAME hk5 CA table to hk6 is a schedule projection only:330->336.
No fresh hk6 phase/count rebind or qualification is implied by that projection.

Inputs copied in this result directory for the hk6 candidate and current CA
schedule. Frozenrawhk5 input remains parent-owned
/srv/opentallas-scratch/claude/codex-head-ca-0840/plan_hk5.json;
its exact hash is retained in hk5_constants.json. Current CA2 original:
intel2:/srv/opentallas-scratch2/claude/codex-head-ca-0840/ca2/regions_ca.json.
Latest rawhk6 source:
intel2:/srv/opentallas-scratch2/claude/codex-head-0830/plan_hk6_candidate.json.
Latest postFT source:
intel2:/srv/opentallas-scratch2/claude/codex-head-kits-0822/hk6_ft/plan.json.

Four small semantic tests pass: critical-branch selection, twice-gather law
without host/LEP contamination, missing return refusal, exact per-port CA sum,
duplicate/wrong-endpoint/count-mismatch controls and double-charge refusal.
No RTL edits, no physical/START adoption, no programme installability or rate
claim. Parent tokens composes fullhk5 bind and physical START timing separately.
