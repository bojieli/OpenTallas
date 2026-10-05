Portable calendar inputs and actual r34 eight-group cost successor
================================================================

Parent intake checkpoint: main568e3d072 (a671/0a/2e/4e dependencies intaken).
Writes are restricted to the calendar tool/test and this results subtree. No
parent worktree, original physical/model file, source checkpoint or running job
was modified. New functionality is opt-in; existing model costs are unchanged
when neither --portable-inputs nor --ds-r34-group-reprice is selected.

Portable input closure
----------------------

archive_r3/index.json names72 exact commit/path/hash inputs.58 unique archived
blobs occupy1827205B; existing large committed artifacts are referenced by their
canonical path AND exact byte hash. The canonical14MB DS archive is not copied.
The archive includes original V1/physical/state-provider sources needed for
NO_REMOTE refs f7fa...,620c...,f240..., and the655f... unified-model alias (same
unchanged hash as its other historical alias). Lookup with --portable-inputs
never calls Git, rejects missing/ambiguous pins or changed canonical/blob bytes,
and reads old snapshots instead of mutating a current additive model.

The initial full provider replay found the missing655f unified alias. Its failure
log no_git_replay_complete.log is retained. r2/r3 logs are separate successful
successors. No failed verdict was overwritten. Preliminary larger archives and
unchanged duplicate model bulk stay untracked; only compact archive_r3 is handed
off. The exporter requires retained historical objects only to construct a NEW
archive, not to consume this committed archive.

Run ordinary replay from an integrated checkout with --portable-inputs pointing
to archive_r3. Fresh outputs below are disposable; do not overwrite old records.
Let OUT denote results/uarch/h3_complete_native_calendar_20261002 and PORT denote
$OUT/portable_input_closure_r1/archive_r3 (shell variables are examples only):

    python3 tools/h3_complete_native_calendar.py --provider-v1-join \
      --portable-inputs "$PORT" --out FRESH_PROVIDER
    python3 tools/h3_complete_native_calendar.py --ds-r33-once-reprice \
      --portable-inputs "$PORT" \
      --r33-boundary-cycles "$OUT/ds_r33_once_reprice_r1/boundary_cycles.json" \
      --out FRESH_R33
    python3 tools/h3_complete_native_calendar.py --ds-r34-group-reprice \
      --portable-inputs "$PORT" --r33-cost-baseline FRESH_R33 --out FRESH_R34
    python3 tools/h3_complete_native_calendar.py --tp96-collective-inputs \
      "$OUT/tp96_literal_collective_join_r1/inputs" \
      --tp96-endpoint-cycles "$OUT/tp96_literal_collective_join_r1/endpoint_cycles.json" \
      --portable-inputs "$PORT" --out FRESH_TP96

Add --verify to replay each fresh output. Canonical bulk files are intake
prerequisites; their paths/hashes and every compressed archived blob are in the
index. This does not require any historical Git objects or remote refs.

Independent replay_without_git.py stages canonical bytes into a TEMPORARY source
root, then blocks BOTH subprocess Git call APIs during all four generation/replay
paths. It proves six provider/V1 records, four r33 records and two TP96 records
byte-identical to previous committed data. New manifests pin the fallback's
current tool bytes. unchanged_record_references.json points to existing model
records; duplicate unchanged bulk was not committed. This staging helper reads current canonical checkout files and does not query
Git at all. Its optional --canonical-root points to an integrated checkout when
the worker tree lacks the canonical DS archive. The production CLI fallback
uses already committed canonical files.

r34 source and once-only costs
-----------------------------

Kepler source0b4ab421b lower_template/lower_native/canonical functions are executed
as metadata only. All40 all_reduce PC source groups8/per_group8/elems8192 and
source rank/template/version/dependency declarations are resolved. The new
9a694... template has ordered native steps, original attrs/rounding/tree, actual
shapes[contributor8,group8,word1024] and a final8192-word flatten. Inventory counts
every instruction's scalars and128-lane batches; it does not accept exporter
opcode strings as proof. It remaps actual provider refs and rank/template IDs
through the producer's own source lowerer. Source initial state is seeded from
released-checkpoint gains, not a decoded-prefix state.

Independent read-only inspection checks the ACTUAL existing sealed producer
native/dispatch bytes against hashes c65a584c... and bcf7d800..., matches every
corrected native template/provider/rank/version declaration, every64 contributor
rank row, and every source instruction outside the40group/40window successors.
Both inspection records are committed. No new numerical/provider run occurred.

r34_portable_r4/ contains all four substantive successor records. It consumes
the current r33 ledger and rejects repeated replacement, bad PC/rank/dependency,
C0 counts or mismatched old V1 profiles. Native non-V1 scalar32, old typed V1
upper costs and C0 command22 remain explicit provisional inputs. The known
partial software subtotal432013167537 -> 432334666417 (delta321498880).
Every existing rank ledger field is retained; native/C0 source corrections are
separate once-only delta fields. RF mirrors, I64/RMW and provider costs are not
added again; additional RF/provider debit stays UNKNOWN. Qwen full/fixture
records are unchanged.

The40 corrected group programs create3840 unbound actual-movement calls, raising
UNKNOWN shared calls189476 -> 193316. The old single-group shared reservation
remains a historical partial lower reservation, not a proof for the new template.
Materialized workspace524288B/call fits software33554432B/rank but DOES NOT fit
one physical65536B shared scratch. Bounded current operand-span/lease/ACK order,
installed home/RF connectivity, group address copies and calibrated full-provider
costs still need source-bound actual movement journals. There are no such
journals in this handoff; whole latency remains null. r34 C0 source catalog
admission is explicitly null until Sagan binds the new template identities.

Validation and resource estimate
--------------------------------

    python3 -m unittest discover -s tests -p test_h3_complete_native_calendar.py

63 tests PASS in20.061s, including corruption/missing-pin/no-Git, canonical
archive reuse, current provider remap, duplicate replacement, PC/rank/C0 ledger
negative controls. All four paths generate and byteexact replay with historical
Git forbidden. Final full closure48.29s/2939400KiB peakRSS (~2.80GiB); reserve4GiB
RAM and about60s as a planning estimate, not a deadline or resource limit.
r34 alone generation+replay timing is recorded in independent_no_git_replay_r4.
No RTL compilation, checkpoint execution or provider/arithmetic repeat launched.

validation_inventory.json includes all archive file hashes, current source hashes
and every r34 artifact size/hash. The four r34 records total475636B. Full finite
runtime/whole-system latency, physical SS/FF/contextual ports/ACK/CTS/reset,
released-checkpoint token quality and calibrated MTP remain unqualified.

Literal96endpoint64B functional harness timing remains separate from assumedwide
product geometry. Expert8235 still exceeds historical5001; index42861 is not a
headline replacement for1471 in a different width. No rate, SWtick-to-ns,
agentic median or chat/pooled acceptance headline is inferred.

Current r35 continuation
-----------------------

r35_same_native_scope.json pins Kepler240c18471 entering-state/data metadata.
The rich r35 manifest uses the same corrected nativec65a584c... program, so native
and C0 group costs are not replaced again. Its exact reference entering-state
digest passes; this is explicitly seeded reference state, not decoded-prefix
quality. The8GiB journal capacity is declared, but the actual journal directory
does not exist at inspection and all full-token launch flags are false. Actual
ordered journals, concrete file-offset-to-HBM translations and matching W15
geometry are the next movement/cost dependencies. The live STALL1 run was not
read for a terminal verdict, restarted or given a deadline.

A lightweight primary third-party candidate audit is kept separate in
agentic_candidate_review.json. Static DSpark K5 serving receipts and quality
BFCL rows do not provide matched gamma5 agentic committed-token/verify/complete
iteration receipts. No chat, pooled ratio or three-run performance median was
used as a median per-request agentic acceptance/rate. This is not an exhaustive
claim that no other eligible third-party receipt exists.
