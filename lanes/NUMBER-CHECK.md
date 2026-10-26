# NUMBER-CHECK (METHODOLOGY 12.9f; owner 10-26 ~08:1x) -- independent recompute of every owner-reported gate number
Scope: related-pair skew TT/FF (12.4a/b), die GRT overflow + iteration count (>=50), static IR, STA WNS/TNS, LEC, sign-off counts.
Method: own scripts (never the lane's report step) on run artifacts (routed ODB/SPEF, STA reports, GRT logs, tap/tree arrival files),
OpenROAD/OpenSTA in docker with --memory on fleet hosts (never localhost). Gate number = 12.4b (CPPR only at last common H-tree node,
region root for same-mesh pairs; mesh-node credit INFO only). 12.8 banned means (early taps, stub trims, balance pads chosen after a
measurement, clock ECOs, mesh-node credit) => METHOD-FAIL even if the number passes.

## How to request
Append to this file (via ~/coord/bin/coord-commit.sh):
  CHECK-REQ [tag] <metric> = <value> artifacts=<host:path>
Answer (here, within 30 min):
  <date> NUMBER-CHECK: [tag] CONFIRMED | MISMATCH (mine vs yours, why) | METHOD-FAIL (which gate definition was not followed)
Unchecked numbers reported to the owner must be labelled UNCHECKED.

## Log
2026-10-26 06:17 PDT NUMBER-CHECK: lane started. Backlog (a) QC early-tap 154/143, (b) KV c3t 63.95/54.71 (+ strict re-measure 281.37/229.58), (c) HBM r7_b1 979.6/800, (d) QC M4-M7 signal GRT0 + --m89, (e) S81 GRT probe 50 it, (f) sign-off counts per die resolved.tsv vs closed archive.
