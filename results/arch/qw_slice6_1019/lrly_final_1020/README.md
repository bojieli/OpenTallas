# LRLY final native receipts (route verdict still pending)

Both immutable 6_final.v netlists pass the independent textbook transitive all-nonclock-driver census with zero roots above32. This includes repaired routed cells and is separate from the earlier gate mappings. Exact final netlists are preserved compressed beside their hashes.

Canonical native PG helper was sourced after reading an immutable copy of each 6_final.odb. Only `ot_pg_audit_snapshot` ran; no global_connect, protection mutation, repair or rewrite. Main:86153instances/172306PGterminals, zero failures. Fallback:64478instances/128956terminals, zero failures. Both native VDD/VSS roles and persisted domain rules PASS. Saved ODB hashes match the SS-setup and FF-hold STA receipt hashes exactly; no intermediate CTS ODB is substituted. Tool OpenROAD26Q3-1510-g6cb3f2b704, exact helper/script hashes preserved. First Docker invocation missed the binary PATH; infrastructure log retained, then rerun with the actual pinned binary path.

Actual propagated-boundary SSsetup/FFhold: main+178.48/+20.52ps, fallback+241.90/+19.23ps. Raw TT ORFS physical.json is also preserved: its boundary convention reports hold/slew failures, so these receipts do not erase that earlier result or assert complete signal integrity. Final clock/reach and signal-integrity disposition are still owed, and daemon mutant benches were still progressing when collected. Neither leaf is claimed CLOSED/bindable by this packet.

PG and fanout are structural native audits; they do not use imported sequential-cell behavioral models and are unaffected by the ASR-model functional-proof hold.
