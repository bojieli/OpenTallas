# INT8 safe source: bounded physical tie placement

MODEL / PLACEMENT ONLY. No CTS, routing, timing gate, REVIEW.json, or release qualification.

Candidate `smh_int8_safe_tie_t1` imports the exact `da40a2a46` mapped safe source JSON, SHA256 `8e4fdb42a22d755e7efb9cfcdf1ac0efe1563ee500d177e2d8e810fd15b85d27`. This run performs no synthesis, ABC, resizer data repair, or functional rewrite. `connectivity_identity.json` proves all 10,104 ordinary cell identities, masters and signal connections match the mapped source before and after physicalization. Constants alone are replaced by real, truth-matched ASAP7 tie cells.

Existing `physical/common_flow/die_constant_cells.tcl` is unchanged: blob `541b8e0e05516d3efd78ae618ce9a443a49470ce`, identical at source and current origin/main `22f53efd97b219b16039486b0638e3c592d37a63`. It calls `insert_tiecells` and `repair_tie_fanout -separation 1 -max_fanout 1`, legalizes only ties, and retains ordinary placements. There are 202 HI and 64 LO ties, area 11.63484 um2, one actual input load each, summed native input capacitance 253.813508 fF. Total native LEF area is 1322.53722 um2; this is native geometric area, not an interchangeable generic synthesized-area estimate.

The independent strict contract from `969965293` evaluates exact exported native pins and Liberty functions: 11,407 drivers, 22,424 logical endpoints, 2,782 FF, max transparent logical fanout 24, zero violations, zero unphysicalized literals and zero disconnected outputs. Liberty clock-pin roles are used; no clock-name exemption. The pre-tie graph correctly refuses its undriven structural one_/zero_ nets. Before/after raw graphs and exact five parsed library hashes are retained. Source-to-RTL equivalence remains the parent safe-source proof; this packet proves mapped-import connectivity identity.

Actual original M1/M2/M5 PDN was generated. Both VDD and VSS `check_power_grid` checks report connected shapes. `pg_contacts.json` independently intersects every transformed native M1 supply pin with same-net M1 rails: 20,740/20,740 contacts, including all 532 tie supply contacts. Grid via counts are VDD 30,856 and VSS 30,989. This is a placement PG contact check, not DRC/antenna signoff.

## Safe-design checklist

1. Pins/reset: source boundary and two ordinary sampled reset edges preserved; parent safe-source functional proof applies. Physical copied-pin/reset ancestry remains subject to owner/native review. Full north/south faces use four actual M5 tracks, .192 um minimum pitch; max 6 signal pins in any 1 um interval. Original two-track diagnostic packed at .096 um and is preserved remotely, not adopted.
2. Reach: PASS geometric bound. All cells and pins lie in 237.6 x 129.6 um outline; maximum possible Manhattan point distance 367.2 um <405 um. No added relays or edges.
3. Fanout: PASS native all-driver census max24; 266 actual static roots fanout1.
4. Depth: OPEN native timing/depth qualification. No CTS, propagation, or routed timing is inferred from placement.
5. Storage: no new state/storage; same 2,782 mapped FF and same source lifetime/payload behavior. Existing parent source proof owns storage classification.
6. Floorplan: PASS legal placement, 464 rows, no macros/lattice obligations, continuous standard-cell core [2.16,2.16,235.44,127.44], outline aspect1.833. Fill4.53% is pin-bound, explicitly subject to owner exception/review; no shrink claim. See `placement.png`.
7. Clock: OPEN. Actual clock entry W region62.8–64.3 beside the central register mass; source clock reference, insertion/spread, neighbour matching, electrical and >=.03 route hold margin remain unqualified. Original kit's 2,531-sink clock evidence does not describe this 2,782-FF source.
8. Schedule: unchanged source ages: reset two ordinary samples, output +2/+3 contract retained; physical ties add no registered edge.

## Reproduction and preserved diagnostics

Fleet: `ot-epyc8:/srv/opentallas-scratch/claude/hbm-int8-tie-place-1019`, unpinned ot-run admitted unit `oth-ubuntu-1668062-1792440318` for placement/export. Later read-only census/geometry/contact units complete. All ODBs, native libs, exact source JSON, netlist, input/platform/image hashes, legal-placement log, prior two-track graph, and setup errors are retained there. Setup-only IFP0039 (default tracks), PPL0024 (distance units), missing host/container Python dependency and early read-before-final-ODB diagnostics are preserved; no route was run or retried.

To reproduce: copy exact input JSON/helper/PDN and tools, run `run.sh`, `audit.sh` (records the expected pre-tie undriven-constant refusal, then audits `after_ties` and `placed`), `compare.py`, `metrics.py`, and native `pg_contacts.py`. Native libs/LEF/image hashes must match the committed packet. Only ROOT can authorize any next physical stage after reviewing this source-pinned MODEL.
