# Original parameter audit terminal pickup

All five remaining original audits are NOT PROVEN; none issues a parameter receipt. The original `kv-params-1019` process set is now absent. This is a read-only collection, with no proof rerun, source/helper edit, view adoption, or native qualification.

| Audit | Proven / total comparisons | Unproven | rc |
|---|---:|---:|---:|
| PVjoin default | 16277 / 16293 | 16 | 1 |
| PVjoin MUT1 | 14389 / 16293 | 1904 | 1 |
| seq_xs default | 5307 / 6075 | 768 | 1 |
| seq_xs MUT1 | 5307 / 6075 | 768 | 1 |
| seq_xs selected MUT8 | 180 / 6074 | 5894 | 1 |

PVjoin default retains sixteen original `g_join[*].u_add.err[1]` observations. Its MUT1 leaves additional comparisons unproved, but neither an equivalence refusal nor the larger unproved set establishes a reachable causal numerical divergence. seq_xs default and universal MUT1 have identical proof counts; MUT1 is not a causal witness. Selected MUT8 changes the comparison ledger by one cell and leaves 5894 unproved; no extracted SAT counterexample or observed divergence accompanies this audit. Treat all mutant records as preserved proof refusals, not a causal PASS.

`new_terminal.tgz` contains all five complete work directories, generated cell/gate/gold representations, exact scripts, outputs, caches, logs and original audit JSON, plus the original causal launcher. `source_tools.tgz` preserves the selected RTL inputs and audit/helper implementation. `identity_snapshot.json` records 105 actual file hashes, file mtimes, collection-time executable SHA and an empty process query; all 112 source/view checks match the original audit identities. Every exact equiv.log SHA independently matches its audit. Original logs pin Yosys 0.68 git 38e001a6f; the collection-time executable SHA is not a retrospective historical binary attestation. Audit `seconds` record proof pass durations; original outer wrapper PID/unit and whole-job wall time are not present in these work directories and are not invented.

The four earlier terminal refusals in dd27f95b8 (ktree/lane8 sixteen errors each; PVslice default/MUT1 missing SRAM SAT model) remain unchanged and are not duplicated here. Replacement JOINT induction/base and comparator diagnosis are separate evidence, with separate live-job ownership. Existing default comparisons remain intact. Physical clock/reset/phase/POR, PG/contact safety, exact expanded source/profile identity, full reset base and complete native qualification remain independent HOLDs.

The e27a57fbf conditional 916-comparison observation/reset-base packet concerns PV wide control and is not the original PVjoin 16293-comparison audit. Neither it nor later ktree/lane8 JOINT proofs retroactively qualifies any original audit here. All unproved identities are retained uncapped in each complete equiv.log, together with full gate/gold/transformation scripts; summary samples are not the evidence boundary.
