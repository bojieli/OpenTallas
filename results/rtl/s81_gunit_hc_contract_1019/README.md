HC calendar resolver candidate, not compiler admission

`tools/s81_dv/layer_prog/gu_hc_contract.py` recognizes the exact 37-file
GUNIT timing source set from the actual HOP witnesses. Safe2 and safe3 both
measure north975 / south973 from the common last HP_N input-port edge.
The per-leaf native source set is recorded separately: L5 synthesis does not
consume the other GU leaves or its stop. The full calendar guard does.

Both production manifest entries have null native/gate approval digests and
resolve with admitted=False. A caller cannot unlock them by passing a PASS
file. A future reviewed manifest must pin native and gate file digests;
the resolver also checks the gate source bytes, native link to that gate,
probe/library/insertion provenance, measured reference coverage, zero launch/
capture/comb violations, existing220/190ps budgets and TT/FF80ps spreads.
`require_admitted()` raises until those checks pass. CTS evidence only admits
the compiler calendar candidate; it never establishes routed signoff, parent
slot fit, or release adoption.

Unknown source/options are refused. Historical759/757 remain exported as
history, never a fallback for unrecognized/pipelined RTL. `lower_gu.py` is
unchanged; no release calendar has been switched. The measured change is
+216cycles =180ns per serialized HC job at1.2GHz versus the old MCP calendar;
whole-token impact requires actual critical HC job composition, not guessed
overlap. Same-edge boundary copies add0cycles beyond safe2.

Actual witnesses:49f8f8f84 for safe2,87ed2bccc for safe3; positive3jobs,
1655HP/SC input beats,15CTL rows eachside,50roots,2rsqrt, nofault. Old759/757
and wrong+1 mutants eachFAIL35. `real_source_resolution.json` independently
checks the complete recorded source bytes and preserves blocked status.
Ten focused unit tests include changed/missing RTL, wrong compile options,
untagged PASS files, mismatched gate sources/digests, failing native limits,
missing provenance, unverified archives and failing gates.

Ownership coordinated with token_calendar_closure (HBM-only; no overlap).
Parent must decide exact lower_gu integration once native admission is ready.
