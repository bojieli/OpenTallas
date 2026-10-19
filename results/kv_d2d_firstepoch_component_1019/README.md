# Fixed-image private accepted receipt and FIRST epoch component

Functional component PASS, with public defaults and parent bindings unchanged. The three new private families implement actual accepted-image receipts and authorize the first epoch/start before every original state-changing branch. `ENABLE_FIRST_EPOCH_GUARD=0` and `FIXED_IMAGE=1` remain the defaults. This packet does not qualify native GEN8, variable images, SRAM integrity or whole-token SU/MU operation.

## Exact scope and state price

Pre-edit source/cost freeze is commit 3b7ee00c0 and PRE_EDIT.json. The component retains the full unchanged dispatcher, two actual 40-bit die configuration relays, private BC with unchanged real MU sequencer, exact SF parallel pin captures, and both private SF calendars. Original declared state is 4,118 bits. New declared state is 269 bits: 106 calendar receipt/identity/control bits, 2 BC state bits, 8 authorization landing bits, 102 metadata bits across six existing configuration captures, and 51 metadata bits across three existing request/start captures. Combined declared source state is 4,387 bits, before any physical return/fanout/reset implementation. These are source counts, not mapped-cell counts.

The exact generated SF calendar source SHA256 is 9b3694353d39abc17f83e52f2f6de4273fa3dbe498a138dbee147e436bcefb67. It is a private source dependency; frozen GEN8 remains FRAME/bind=NULL. The selected BC, dispatcher and image originals are pinned separately. All seven immutable original dependencies are bundled under frozen_inputs for reproduction.

## Mechanism

Each calendar tracks all 32 actually accepted entries and its actual base write. Data equality uses the half actually consumed by the original assignment, and base checks use the actual base pins and both one-hot copies. Epoch/producer-valid follows the same six existing captures as configuration. Incoming metadata is never acceptance credit without the actual write predicate. Unmodeled dispatcher sink readiness stays zero; overall setup readiness is not manufactured.

The last accepted write is W. Prefetch and settle occur at W+1; the earliest authorized actual calendar start is W+2. Every original start branch uses the same legal decision. Unauthorized requests poison the generation and halt internal evolution; upload cannot clear failure or queue a retry. Reload invalidates receipts and preserves poison. Runtime SEG2/SEG1 writes retain their original edges. BC exports its source-current/sticky generation poison to both calendars with no additional state.

Receipt assertion/release uses the exact original local reset edge, so the first post-release accepted write is counted. Eight new landing FF authorize guards; they do not establish a native reset fanout or arrival certificate. The common-clock fixture supplies a real shared reset assertion, without numeric reset generations, quiet windows, A0 masks or initialized SRAM assumptions. Pre-assertion and unreset storage behavior is preserved.

## Verification

Final full fixture bench4 passes 32 application verdicts: 16 Icarus four-state cases and 16 Verilator 5.050 cases. The extended healthy run compares 257,115 actual reset-release edges, all 36 layer anchors and 1,411 calendar events. The next ordinary token remains exactly 249,600 edges later. Actual token calendar consumption at 6300 produces first RX STATUS at 6315, preserving +15. Default-disabled behavior and healthy enabled retained outputs match the untouched source family.

The direct calendar r6 suite passes 267 four-state checks. It covers every 32-entry/base omission, W/W+1 rejection and healthy W+2 internal state, consumed data halves, epoch/valid/capture faults, arbitrary old Q, first post-reset accepted write, reset/reload invalidation, sticky failure and no late queued retry. Ten direct verification mutants fail named assertions with nonzero simulator exit. Four full-fixture mutants likewise fail causally: removed epoch comparison, one-capture metadata misalignment, removed first STATUS header check, and output masking with internal guards removed. See calendar_edges/README.md and harness/SUMMARY.json for exact identities, patches and complete logs.

The unchanged real SF STATUS receiver is driven by actual calendar event timing and explicit typed fixture payloads. Its healthy, malformed-first and malformed-after-idle checks pass continuously. This is standalone receiver evidence, not proof of the native link payload producer or receive alignment pipeline.

Historical failures remain separate: the initial testbench sampled start after NBA and measured +16; the corrected monitor uses the real consumption edge without changing source timing. The initial ineffective output-mask mutant retained internal halt protection and was not caught. Early direct checker weaknesses were exposed, preserved and refined; final data/base tests isolate the malformed upload before any start. The running-write missing-receipt deposit case is explicitly verification fault injection, separate from the legal emitted-valid/no-actual-write control.

## Remaining HOLD

Native FRAME replacement/binding; independent regional reset/phase/clock frontier; reset and all-driver fanout; physical ready/invalidation return transport; canonical first use beyond this bounded calendar component; actual endpoint payload/STATUS pipeline; physical SRAM write integrity; variable-image authority; complete mapped comparator/constant-ROM mux area and delay; PG/contact/floorplan/timing closure; and whole-parent/token SU/MU price remain NULL/HOLD. No 129/602-copy constructor, physical run, public source change or root binding was added. Healthy added component cycles are zero when the real first epoch arrives after accepted installation and W+2; native transport latency and parent schedule are not inferred.
