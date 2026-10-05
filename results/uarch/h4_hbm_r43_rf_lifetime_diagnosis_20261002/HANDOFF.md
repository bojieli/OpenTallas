Independent R43 RF lifetime diagnosis

Authoritative diagnosis_r2.json. Metadata-only; no numerical rerun, provider
modification, alias-guard weakening or change to the failed job1950286 evidence.
The complete bound native/homes artifacts are checked against the exact R41
regeneration from reviewed dd6 lineage before diagnosing lifetimes. All original
RF prefix records remain identical. This is NOT an address-lineage failure.

The preserved numeric call journal contains864 completed calls through PC8,
including all64 PC8 ranks;1504 independent output observations are byte-exact.
PC9's first publication proposes DeepSeek.9.zpart.67. At rank0 it overlaps
retained DeepSeek.8.o.65 at SM1 slots32/33. Copy0 bytes540672..541696 and copy1
bytes802816..803840 are the corresponding two real RF ranges. The metadata
model predicts the same unused-output conflict for all64 active head ranks;
this is not a claim of64 actually executed failures.

Full native reference traversal finds o.65 only under PC8 source_outputs and
writes. There is no full-program read/provider/auxiliary consumer. Its original
RF home retire_pc is8. The engine computes last_use from reads, then after each
whole-operation retirement calls release_version only for read entries at their
last use. Therefore an unused produced output never gets a release call, even
though its directory lifetime ends. This leaves a stale physical allocation in
locations, and the alias guard correctly refuses PC9 overwriting it.

Recommended owner fix: after successful whole-PC8 retire_operation, explicitly
retire the proved-unused produced output via EXISTING release_version. Require
all producer rank publication/comparison receipts first, generation match and
no outstanding view leases. Never delete locations on attempted overwrite and
never infer retirement merely from a retire_pc field. Preserve all future-used
outputs (including o_own.66, which PC9 reads). Actual sink/mirror ACK/consumer/
reverse physical obligations still need the finite owner binding; software
retirement receipts do not qualify physical timing.

Kepler/Sagan own the runtime repair. This milestone diagnoses and supplies the
necessary exact source/call/reference evidence; it does not implement a provider
or engine patch and does not claim the failed runtime is repaired. Diagnostic
source guards include future read and auxiliary references, wrong birth, missing
version, physical SM/slot overlap and archived-source mutation.

Replay from a reviewed main containing dd6 and the original endpoint module:
 python3 -m unittest discover -s tests -p test_h4_hbm_r43_rf_lifetime_diagnosis.py
 python3 tools/h4_hbm_r43_rf_lifetime_diagnosis.py --out results/uarch/h4_hbm_r43_rf_lifetime_diagnosis_20261002/diagnosis_r2.json --verify

Generator uses existing h4_hbm_pc10_r41_lineage.regenerate (allocation only),
its pinned source archives, and the new hard-pinned failed-job input archive.
It performs no numerical arithmetic or hardware/simulation run. Raw SQLite is
needed only to independently reextract journals1/4; exact extracted events and
selectors are archived. No historical Git object access is required.

This is separate from b705 PG work; the diagnostic commit has no dependency on
that new model/tool. Historical diagnosis.json is an earlier unoptimized metadata
projection without detailed mirrored byte ranges, superseded by diagnosis_r2.
