Current r33 C0 / once-only native cost milestone
=============================================

Input base: published main ce132ffea40cf31f1af9d8c7af696d5e57125213.
Requires the preceding Dewey source adapter 2e76d4f96 (its tracked, compact records),
plus the historical native/V1 component ledger; all direct input blob hashes and
immutable commits appear in model/manifest.json. No canonical native archive,
released checkpoint payload or giant calendar was copied. Parent retains its
baseline portability-test patch when integrating this test successor.

Implemented
-----------

The CLI consumes Sagan's actual current C0 r33 catalog, verifies all2213 PC
bindings/dependencies/counts against Dewey's current catalog, and resolves each
changed window LOAD to its retained native code/hash, source instruction and
127x512 span. Forty changed PCs each have96 calls. LOAD scalar obligations fall
by1966080 overall, by512 per rank/call. Every other opcode/count is unchanged.

The prior analytical ledger charged32 software ticks per scalar LOAD. Because
rank intervals run in parallel, its critical-rank correction is16384 per changed
PC, not the sum across96 ranks. All2213 serialized PC intervals are rebuilt:
432013822897 -> 432013167537 known partial software ticks (delta -655360).
All previous rank ledger fields are retained verbatim; an explicit native LOAD
correction is added separately. Qwen full-program demands and both reduced
fixture records, V1 replacement, C0 accept/reverse, I64 codec/RMW, provider,
conservative shared movement and mirror reservations remain unchanged.

The receipt implements the EXACT H4_R33_DEWEY_ONCE_REPRICE_V1 ABI. Tests and
independent inspection execute the actual source-pinned parent admission method
against the receipt, reject a second admission, and reject charging RMW again.
Admission concerns this partial native cost successor; full movement remains held.

An executable finite reservation models the initial-window LOAD boundary for
all3840 actual provider/rank pairs. Each508-fragment input span has concrete
canonical initial home/version/generation/source reference. Each512B fragment
orders: owner admission;16 backing32B reads;8 scratch64B writes/ACKs;8 scratch64B
reads;512B RF write with both mirrors' ACK; consumer capture; matching reverse.
The lossless run-length output contains3840 events. It constructs conservative
block256%32 software SM routing, holds global and rank credit1 and all32 SM
scratch/RF mirror resources during each batch, and releases before reuse.
512B scratch and one512B RF vector per SM suffice for this boundary reservation;
this does not prove the arithmetic continuation's workspace or installed mapping.

Counts for this constructed boundary:1950720 fragments,31211520 backing sectors,
15605760 scratch writes and15605760 scratch reads,1950720 two-mirror RF ACKs.
Total source input998768640B. Its deliberately serial provisional reservation is
169712640 software ticks and IS NOT added to the existing ledger. Output commit
is not scheduled without its actual generation/lease and ordered continuation.
These phase counts describe the emitted software transport plan, not observed
provider movement. The old conservative provider/shared service fit remains.

Explicit provisional phase table (boundary_cycles.json): admission2; each32B
read/return3; each64B scratch write/ACK2 and read/return2; both RF mirror ACK2;
consumer1; reverse2. These are positive software reservation assumptions, not
measured costs, frequencies, physical ACK latency or runtime evidence.

Reproduction and bounds
-----------------------

    python3 -m unittest discover -s tests -p test_h3_complete_native_calendar.py
    python3 tools/h3_complete_native_calendar.py --ds-r33-once-reprice \
      --r33-boundary-cycles results/uarch/h3_complete_native_calendar_20261002/ds_r33_once_reprice_r1/boundary_cycles.json \
      --out results/uarch/h3_complete_native_calendar_20261002/ds_r33_once_reprice_r1/model --verify

For a fresh output, omit --verify and choose a nonexistent --out. Generation:
9.86s/630536KiB peakRSS; byteexact five-record replay:10.21s/630208KiB.
Reserve1GiB RAM/30s for this source-only join; no native numerical/provider run.
59 tests PASS in20.042s; diff whitespace check PASS. Direct10 input pins and all
five output hashes are independently inspected. Exact inventory is in
independent_inspection.json. Five model artifacts total1495063B.

The first generator was stopped before artifacts were written after discovering
that it rehashed the invariant whole catalog once per call. Its TERM/143 log is
retained as generation.log. Final code resolves immutable source code once per
template and still validates every PC/rank/home. Final generation and replay logs
are separate; no failed verdict was overwritten.

Remaining UNKNOWN scope
-----------------------

189476 shared-template calls still lack complete actual ordered movement.
The initial input data/payloads, provider service return/consumer/reverse journals,
output generation/lease/publication, full forwarded continuation operand spans,
full retained index histories and code/exponent views, installed rank/SM RF map,
AW27-to-physical translation, calibrated endpoint costs, contextual reset/CTS/
SS-setup/FF-hold, and full-program runtime remain UNKNOWN. Boundary reservations
supply none of those receipts; complete_service_software_ticks stays null.

The parent Qwen ROM reset record is retained as context:134610 source clock bits,
58919 source async reset bits, including90 metadata bits. These are pre-opt source
widths, not mapped loads; its physical root/CTS remains unproven and adds no HBM
runtime term. Original unified model and addressed owner/observer files untouched.

Literal TP96/64B functional harness calibration and earlier assumed wide product
slots keep separate geometries and ledgers. This change makes no collective cost
replacement, production-rate extrapolation, MTP or agentic median headline claim.
Recovery and frozen D1 sources/jobs were only inspected; no job was restarted.
