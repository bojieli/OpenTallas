Provider/V1 finite calendar component milestone

Authoritative outputs are in `final_physical/`; prior untracked `final/` and `review/` are intermediate local runs. Intake the seven committed artifacts, not a new bulk materialized calendar.

Implemented

- All 2213 DS PCs/30 families and 1737 Qwen PCs/21 families consume actual retained native counts. V1 native-only cost replaces its old native component once. DS retains its conservative scalar-command upper unit; no SIMD acceleration or achieved hardware throughput is inferred. Every DS rank group, PC dependency, collective participant set and native subtraction was independently inspected against the retained baseline.
- Existing C0, provider, actual 64B shared movement and I64/RMW charges remain intact. Additional RF debit is UNKNOWN until the explicit source-scoped pair-read/write/ACK ledger resolves. The ordered reconciliation API serializes extra pairs and both-mirror visible ACKs, retains C0 accept/reverse and provider RMW phases, and rejects missing ledgers, duplicate replacement, forged source references and incompatible phase order.
- Kepler r30 allocator is replayed from its pinned source against canonical DS native bytes: 4616 fragment homes for 56 formerly missing write versions. The four index-key output fragments are now source-resolved: PC121/rank63/base34342912; PC449/rank63/base36966912; PC782/rank63/base39590912; PC1110/rank31/base42207232. Each is exactly512B. All source consumer views are retained with requested typed bytes; these fragments do not substitute for multi-megabyte histories or packed code/exponent views.
- A terminal publication receipt validator resolves PC/version/rank/generation/terminal-sector/tag identity, backing visibility, consumer acceptance, drained debt and reverse-grant order. No actual parent receipts were supplied. Even a passing terminal receipt does not prove every fragment sector or parent refill journal.
- Reviewed Popper physical join 620c078de is consumed with all eight producer inputs hash checked. Qwen64 and DS3072 rank/SM instances are verified; RF2R/1W has one transaction credit,512 logical vectors,two physical write mirrors,3-edge reads and2-edge write ACK. Existing slot and routing failures remain failures. This software protocol is not an installed H1 atomic owner gateway.

Evidence and reproduction

Run in this isolated source checkout after intake, with producer commits retained in the object database:

```sh
python3 -m unittest discover -s tests -p test_h3_complete_native_calendar.py
python3 tools/h3_complete_native_calendar.py --provider-v1-join --out results/uarch/h3_complete_native_calendar_20261002/provider_v1_mtp_join_r4/final_physical --verify
```

For fresh regeneration, replace `--out` with a new path and omit `--verify`. Source pins and input hashes are in `final_physical/manifest.json`; output hashes and byte counts are in `independent_inspection.json`. The canonical DS gzip is loaded from commit91e3b8cc at results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz (SHA c7ae6baf3f57d3b8d23b3532dad9d1fa921ac86736b5e8b5a229f644a1994313); no duplicate14MB artifact is needed. Parent-owned portability-test patch remains untouched.

47 tests pass. Seven output artifacts total353346 bytes. Metadata generation/replay takes about10 seconds and2.73GiB peak RSS on this host; reserve4GiB RAM and a minute. No numerical bulk replay, checkpoint execution, RTL job or acceptance campaign runs here. Native-component subtotal432013822897 DS software ticks and89427618 Qwen reduced-fixture software ticks are partial provisional reservation totals, never ns or token-rate evidence. Qwen fixture scope is two reduced36-layer programs,3474 PC intervals; full1737-PC Qwen provider/RF calendar remains UNKNOWN.

Exact open scope

- DS189476 actual shared-template calls remain UNKNOWN: forward-leaf continuation movement, concrete parent refill/writeback/ACK/reverse, and source-resolved operand-window routing. The ten existing whole-value templates retain their original64B charges. This milestone does not claim full physical movement or full-token numerical quality.
- Four produced index-key fragments are bound, but their retained-history append, code/exponent conversion views, visibility receipts and consumer transport are UNKNOWN.
- Missing RF phase ledgers mean additional RF debit is UNKNOWN, not zero. No second I64/r22 cost is added. Dynamic full-program source C0 owner traces and actual hardware owner gateway remain open; RF protocol fixtures do not qualify hardware.
- Native state service addresses are AW27 in the separate32MiB r30 extent starting at32MiB. They do not qualify the GPU AW34 translation, or turn the separate32MiB software scratch extent into H1's64KiB scratch.
- Physical model reports existing composed slot/shared-channel failures, absent V1 opcode endpoint and unmeasured opcode/stall costs. No RTL permission, clock conversion or performance headline follows.

Lightweight MTP audit, separate from movement completion

`MTP_source_contract_audit.json` pins AR separately from the historical six-position verify source and fixed draft reference. Successor requires native draft, causal six-position KV/index/window versions, accepted-prefix publication, bonus emission as next pending input (no fabricated KV for the unprocessed bonus), rejected-suffix rollback and drained provider ownership. Draft/verify/commit/rollback/control/calibrated-stall costs are UNKNOWN. Historical AR442.14us,verify715.82us,draft49.9us are modeled reference costs only.

`third_party_agentic_receipt_audit.json` records seven immutable primary-source candidates and source hashes. None inspected supplies matched actual DS V4.1 gamma5 agentic per-request committed-token/verify counts and complete iteration costs. Median request RATE is implemented separately from pooled token/time and token/verify ratios. Local chat and pooled walk tau remain sensitivities only; headline agentic numeric is pending. No acceptance rerun was launched.

Historical failures preserved: generation.log records the nonliteral unrelated historical model field rejected by the first audit. The final audit reads only its three literal reference costs. inspection_initial_failure.json records a review assumption corrected from all-rank63 to actual L20 rank31; producer bytes were never changed.
