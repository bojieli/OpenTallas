Executable corrected-group shared journal join after b2120f45d

Dependencies for parent intake:
* ba0c1ba06 source inventory and portable input closure (already reviewed).
* b2120f45d verify_ds_operand_journal receiver (present in parent65040dfb8).
* Sagan2d05f616a group plan: exact source snapshot is included, so this calendar
  commit does not require a second cherry-pick of Sagan's tools. All40 current
  PCs/96 ranks and64 tiles/call are validated against that reviewed inventory.
* Parent18f632c17 finite selected-interval compiler: exact source is archived;
  one selected-call projection is retained with the original full archive hash.
  The existing3.4MB selected-call catalog is not duplicated here.
* NativePrimitiveVM bounded282e57 and restored original arithmetic helper9a2312
  bytes are included and hash-checked. No golden/family arithmetic callback can
  be supplied instead of this retained primitive closure.

New executable API:
  execute_ds_group128_tiles(plan, PC, rank, generation, source,
                           shared_factory, primitive_sources, output,
                           movement_observer=None)
Source.acquire(span,owner) returns exact512B F32 bytes with visible source
version/rank/generation, first/words, lease and payload hash. Source.release is
called only after that tile's output consumer/reverse receipt. Failures do not
release acquired source leases. shared_factory(owner) returns actual64KiB
allocation, a finite sector provider with disk journal, and512B transact calls.
The executor verifies source template hashes, contributor indices/LOAD byte
spans, PC/rank/SM/flatten identity, live RF32 capacity and every actual sector
accept/backing/consume/reverse grant. Output.write_span is a data-only producer
hook; it must return matching version/rank/generation/offset/payload and zero
pending obligations. Production source/output hook journals remain necessary;
these response fields alone never qualify physical RF mirrors or a full token.

All64 tiles execute their original contributor tree and original BF16 RNE
integer instructions. Constants execute once per call. Observed scalar counts
exactly match all36 retained native instructions; no dependency recomputation
or different reduction order is credited. Intermediates stay in lane RF with
observed16 live512B vectors. Shared reservation8704B is within actual65536B/SM;
the old524288B materialized array workspace is not used by this executor.

Actual directed control:
* PC10/rank0, all8 groups x8 word tiles, synthetic pinned-seed source data.
* 512 source spans/leases, all512 released after tile output drain.
* 576 writes +576 reads of512B:9216 actual shared64 transactions,
  18432 actual32B sectors,138240 disk-journal events, one live provider tag.
* 32 finite SM shared instances. RF mirrored output provider journal UNKNOWN.
* Explicit original provider phase costs/read64/write80 software ticks give
  2174976 serial sector-service ticks. These are provisional software endpoint
  costs, not measured shared64 latency, clock edges, ns or token latency.
* Actual execution/journals are retained in actual_group128_execution.json.gz
  (1180539B); full arithmetic/transport regeneration is byte-identical.

The directed call exports to parent18f632 compose(inventory,bindings) as9216
source-resolved shared64 commands. Each retains actual journal ID/range, native
instruction/operand/typed offset, SM/group/address, lease and interval identity.
The external backend/consumer/reverse bounds are explicitly1/1/1 provisional
model edges. Result59904 edges is solely this directed model bound, NOT measured
hardware, whole native execution or a replacement for the provider SW ticks.
Existing native/C0/RF/I64/provider charges added:0. Full-token latency:null.

Production dependency list for Sagan/Kepler:
1. Kepler needs a source-owned128-word read/lease hook for the actual64 producer
   ranks and four-homed1024-word results. Existing r34 gather_parts/_read_one
   materializes[8,8,1024]; it must not serve as bounded shared execution.
   A whole restore followed by a slice must charge every actually fetched byte
   and must retain a real source/version lease; no free cache/ideal refill.
2. Sagan needs a current-source shared_factory/continuation in the parent driver,
   with exact template/code_index/operand spans and source PC/rank/SM/generation
   ownership. Existing AddressedScratch enforces32MiB workspace; its extent
   declaration must not masquerade as the64KiB shared allocation required here.
3. Kepler/Sagan need output write_span accumulation and complete actual RF
   publication after all64 tiles. Existing full provider publish can remain the
   final source-version publication, but its actual homes, BOTH mirror ACKs and
   consume/reverse events must be joined before releasing parent source views.
4. Current r36 history/query mixins remain a separate directed provider gate:
   bf0984bbf, tools/h3_ds_query_provider_r36.py, prepared manifest
   /tmp/kepler-ds-r36-history-query-manifest.terminal.json. Its8 directed tests
   are not full-token compressor/query outputs. Remaining288 auxiliary refs,
   PC18/later ownership, selected-row codecs and append generation remain open.
5. Supply actual physical translation plus positive endpoint wait bounds to the
   parent's interval compiler, reconcile each retained interval once, then
   execute the full2213PC driver with actual released-checkpoint/state inputs.
   That full-program execution has not happened in this handoff.

Production calls closed:0. All193316 remain UNKNOWN, including3840 corrected
rank calls. This commit is an executable kernel/journal/interval join milestone;
it is not a static-calendar stand-in for the full program. No W15 wide geometry
rate credit, STALL1 action, P&R/RTL build or new acceptance campaign occurred.
The agentic per-request MTP provenance audit stays separate and conditional.

Reproduce, independent of checkpoint/RTL jobs:
  python3 -m unittest discover -s tests -p test_h3_complete_native_calendar.py
  python3 results/uarch/h3_complete_native_calendar_20261002/group128_execution_join_r1/capture_control.py --verify
  python3 results/uarch/h3_complete_native_calendar_20261002/group128_execution_join_r1/compose_control.py --verify

Control generation9.99s, peak566960KiB (~554MiB). Full test suite approximately30s.
These are measured local verification costs, not deadlines or hardware claims.
