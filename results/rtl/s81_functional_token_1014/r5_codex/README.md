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
