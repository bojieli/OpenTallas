# Private HWIN early capture source proof

The frozen private prototype passes the completed source simulations at the original output date (start+D+2) and collision fault date (+3). All 46 NS2..47 full16 shapes pass 276 legal positive runs and 276 intentional expired-return negative runs; each group checks 363768 output windows. Actual helper widths63/2/32 and all four mechanism mutants are covered. The full NS47 four-state reset sweep is still OPEN: phases0–3 have passed, phases4–8/90/93 remain live. No native, timing, physical, main integration or token/die acceptance is claimed.

This is exact selected anchor1e057b7bf under fafa60b0b/cb3ee6029 grant: one existing HWIN, one new private helper, three new validation files. DUT RTL is frozen since51e3f48f3. Public EARLY_HEAD_CAPTURE defaults0. Its source projection is byte-identical to the selected anchor HWIN SHA9be6f5e15bc0c89804b565f67c4211b4e1b4dbef30cf3f276a1ecef3421fc971; the actual bounded default/candidate behavior miter passes. This identity is relative to that anchor, not current main. Shared helpers/hslot/reset tree/parents and original runner/gold remain unchanged.

Current main9c16aa43b has the older short HWIN and no dsdv_mu_mem.sv. The branch cannot be merged wholesale. integration_prerequisites.json pins both sides: five remaining bench/macro dependencies are byte-identical. NEXT_INTEGRATION.md proposes a minimal distinct private package for a future grant; no package import or source namespace work has been performed.

## Completed evidence

| Obligation | Receipt / result |
|---|---|
| Actual 63/2/32 wrappers, cold arbitrary registers, registered current/OLD forwarding | wrapper matrix plus explicit OLD collision; three seeds; all4 mechanism mutants reject |
| Full HWIN NS2/1 and NS47/16 dated miter | internal_identity02; original output/control/fault plus source-qualified payload/head/retire comparisons, no candidate-valid mask |
| Existing original cases | original_matrix01 exit0; base, FAST/MIN, malformed delays, bad returns, head compare, collisions; original illegal NS2/full16 retains cfgfault10/MUWIN FAIL59 as intended negative; S256 legal runs separate |
| Uniform S256 and nonuniform shortest-RL full16 NS2..47 | calendar_coverage_audit.json enumerates276 positive+276 expiry-negative receipts, three seeds, exact source dates |
| Return identity/calendar | Independent accepted-record and architecturalRL model, both RX lanes, all user/slot identities; B−1 accepted, B/B+1 expectedfault at input+3; no suppressed returns |
| Occupied asynchronous reset | NS2 phases0..8/90/93 and NS47phase0 three seeds; actual between-clock assertion/outputclear and unchanged four-low/four-release sequence, no extra warmup |
| Four-state no-memory-init first-use | binding05 NS2 all11 phases PASS;13 known0/X/Z probes, qualified payload/controlX caught c1132; fullshape06 phases0..3 PASS, rest OPEN |
| Long-delay/wrap/generation/source controls | calendar_mutants01 positiveD379 plus wrap/timestamp/retire/reset causal rejects |
| Boot/config/late | boot_faults07: release stages1–3 ignored/stage4 first accepted, idle reconfiguration, armedbadcfg input+2; explicit D0 illegal late firstc1071, original gold retained |
| Actual winning identity | winner_and_mechanism08: distinct eventattrs and cross-generation collision prove highest event winner; firstfault1071/1135; full actual EC_MUT1..4 reject |
| Receipt refusal | receipt_refusal.json atomic refusal exit73 leaves existing files unchanged, including direct runner entry |

The source-only census is source_use_census.json: 1072 new captureFF,148 kept current-hit predicate instances, actual upstream registered WV/WADDR/WDATA and pointer/control/reset uses counted. Predicate module has no keep_hierarchy; native preservation, merged copies and full upstream graph remain unproved. Partial cost1072FF/904.1787um² excludes complete copy/reset/root repair costs. No area saving or old-band fit is inferred.

## Preserved failures and narrow harness corrections

initial_failure keeps the anchor's first-clock assertion FAIL at1000ps while external reset0 and arbitrary local rr1. guarded_assertions01 reproduces it anchor-alone and catches deliberate postreset countcorruption. Root authorized private-bench-only exact seven original assertions qualified by externalrst_n plus their original enables. Original assertion source is unchanged, no extra reset/warmup.

wrapper_matrix01 preserves an OLD-mutant survival (coverage hole); wrapper_old_collision02 adds the exact OLD collision witness and rejects it. four_state01 preserves Icarus BUILDFAIL. parser_split02/telemetry03 preserve the false concat$isunknown failure with all vectors known. pervector04 preserves Icarus constantZ child-count binding failure. Root-authorized temporary, hash-pinned syntax projections split two wire declarations and reorder one unchanged declaration; qualified unknown guard is the mathematically equivalent OR of per-vector checks. Exact source hashes/diffs,13 X/Z probes, vvp12/12 real7-bit bindings and three-seed Verilator original/projected trace identity are in binding05. Canonical RTL/reset/date/observability bytes are unchanged.

sweep_ns2_01 preserves all108 correct dates with wf01 because the old fixture returned an already expired record. rx_calendar_model.json and rx_fixture_ns2_02 independently fix only the new shortest-RL producer; legal and intentional-expired classifications are explicit. Original source test inputs/bytes/gold were untouched. No preserved FAIL is erased or relabeled as a passing run.

## Live collection

Only live owned job: ot-epyc8 unitoth-ubuntu-2036610-1792446395, session6284, localot-run PID2697898. Input directory /srv/opentallas-scratch/claude/s81-hwin-early-source-1019/src_rx06 (harness10ab3da47). Output /srv/opentallas-scratch/claude/s81-hwin-early-source-1019/run_four_state_fullshape_06. Keep useful compiled objects; collect completed phase logs and final actual exit status without restarting, imposing an arbitrary deadline or overwriting receipts. Phases0–3 committed here are complete PASS; remaining4..8/90/93 and final X-causal checks are OPEN.

receipt_manifest.json records historical harness commits,230 checked original input hashes, historical runner hashes and file-level receipt hashes. The historical inputs omit runner in sources.sha256; manifest supplements exact committed runner provenance. Current runner adds its own hash and run_spec.json for future runs. It has not been used to reinterpret prior inputs/results.
