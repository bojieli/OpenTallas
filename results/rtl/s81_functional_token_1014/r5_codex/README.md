S-FUNC recovery, 2026-10-14 (Codex)

HC coefficient arithmetic: recovered authoritative `r5/hcx` completed runs on
EPYC1. ot_hgi_hc_unit with REAL checkpoint hc_mixes operands passes both
attention and FFN records for all 40 layers, plus all 15 DSpark stage/row
pairs. MUT_POST fails with 8 errors each on L00/L14/L20 and M0R0. Raw result
summaries are included. This proves coefficient arithmetic at the HBM unit;
S81 die slot, ROM weight windows and HC input staging remain unimplemented.
It does not prove the S81 cycle price or a die-composed token.

Compiler: tools/s81_ctrl/vm_arms.py implements the owner engine-12 compact
command (client bit20, base/16 bits19:10, nrows-1 bits9:0, GIVE sentinel).
stage_programs.py --vm-operands consumes explicit per-stage/job bindings.
Every SU/HC job must supply {base_row,nrows,producers} or {give:true}; missing
ownership fails closed. Producers receive the arm as a predecessor, matching
the VM engine's new arm/fence acknowledgement. A conservative single-slot
policy waits for the previous client job before reusing the slot. All arm
ordering cycles and command/predecessor capacity overflows fail closed.
This is a compiler mechanism: actual die row allocations/producer bindings
are still required before native programs can be generated. No benchmark
ordinal or duration is used as a native VM opcode. Bench hex remains the
existing duration-trace format; native VM args are in program JSON.

Validation: python3 -m unittest discover -s tools/s81_ctrl/tests -p test_vm_arms.py -v
passes arm-before-write/slot reuse, missing ownership/misalignment rejection,
cycle detection, and capacity on all 59 committed production stage programs.
The capacity check uses GIVE for every job solely to check encoding, ordering
and size; it is explicitly not a native operand-ownership qualification.

Recovered field_all.py correction splits the golden ratio-2 compressor's
concatenated wkv/wgate matvec into named per-tensor records. Existing field
runs already use this fix; no duplicate jobs launched.

Native VM read-group integration prerequisite: `dsfd_vm_read_group` sits
between one client's wide requests and the serialized VM adapter, collecting
responses by slot and emitting the original valid mask/data together. This is
required by hierarchical SU RB/QR pairs and wide HC/SU beats; slot-by-slot
native responses break their arithmetic grouping. Clients must issue
contiguous slot prefixes containing slot0; its credit returns only with the
whole batch, retaining one batch in flight. Independent SU NR16 and HC NR2
shims allow the two clients to operate concurrently. Backend responses may
arrive reordered. Duplicate/unsolicited responses and overlapping or invalid
request batches set sticky fault. This shim is not a replacement for core
credit pacing, native write completion or operand ownership.

Production-shape gate via ot-run2GB EPYC1: 128 variable-width batches, reversed
response order and variable response gaps: NR16 PASS128groups0errors, NR2
PASS128groups0errors. MUT_EARLY=1 reproduces ungrouped response timing and FAILS
with1080errors. Logs in read_group/. Reproduction script
`tools/s81_vm/vm_read_group_gate.sh SRC OUT` (fleet host, wrapped in ot-run).

Field recovery found a newer duplicate AGIdock job touching the same L4..L16
work directories after the initial no-live-job audit. Its concurrent per-region
rmtree corrupted L4 outputs (missing images/directories). Stopped only that
newer duplicate scope oth-ubuntu-3279797-1792028759, verified inactive/dead;
original resumed batch and separate missing-six-rank batch continue. Added
nonblocking per-work flock in dsrom_1m_field.py run: duplicate commands now
fail FIELD_RUN_BUSY before launching workers, preventing destructive races.
L4 damaged regions must be re-run before full-field qualification.

field_sweep.py observes every named layer's four real rank checks and runs
production tree combine when all four pass; pending/failure never becomes
PASS. Current seven complete-layer combines L0/L1/L2/L3/L20/L21/L28 pass;
L28 has one sequential-association mismatch, confirming why the checker must
require the RTL's pairwise tree rather than accepting any matching order.

OWNER CORRECTION 2026-10-14 18:59: production accepts no credits,
backpressure, ready-driven issue or demand arbitration. The read-group shim
has therefore moved under rtl/test/s81_client_transport_diagnostic; its passes
are diagnostic correctness evidence only. The compact-arm helper likewise
supplies encodings/ownership validation, not a production issue schedule.

On-chip numerical substitutions now have an explicit source-verified inventory
(native_inventory.json, 15 items). The previous continuous layer/head/MTP run
is a fixture-supported component chain, NOT a fully native hardware token:
field roots, HC coefficients, Engram residuals, SVC/selector endpoints, head
projections, final norms/glue and ideal VM storage/ports still have numerical
substitutes. FP=dpi additionally replaces arithmetic RTL with C++ functions.
Expected-result comparisons remain valid evidence; injecting computed oracle
results cannot qualify native execution. die_layer_stim now emits one
native_operation_audit record for every emitted job, all native unqualified
until actual elaboration, memory and producer edges are bound and verified.

Static schedule work observes existing full-shape layer issue/response/write
signals with +VM_TRACE=FILE; it does not stall or alter RTL. The fixed-cycle
artifact records each SU/HC row, word mask, job tag and assumed response/done
deadline. Native service/commit reservations, physical path bounds, bank/queue
occupancy and full producer traffic are required separately. The native VM's
isolated actual read return was measured by the VM owner at66..67streamcycles;
the old behavioural VM's LVM10 remains unqualified. static_vm_trace.py never
marks the observed fixture timeline as a native schedule.
