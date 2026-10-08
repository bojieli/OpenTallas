# Actual finite VM service and native-progress protocol component

**Two-state functional protocol PASS; four-state provider qualification remains open.** This is a minimum NR5/NW16 protocol component using the unchanged opt-in finite adapter, checked bank, full16 raw provider, 256 data SRAM macros and32 check SRAM macros. Existing defaults and sources remain unchanged. No arithmetic, fullSU, array, die or physical build occurs.

Actual captured SU tuples are reduced only to the conflicting mechanism: PC19/27 cycle39 VA lane48 address6192, VB lane0 address0 and VC lane16 address2064. They occupy fold128 bank0 rows3/0/1; the tested hardware is the existing four-bank service, not a folded128/256 implementation. Values come from the pinned authorized initial HEAD fixture as opaque protocol payloads, physically installed through normal writes and postverified ACKs. This is not a claim that those initial HEAD values are L20 activations.

The PC18/26 cycle26 scalar0 old-read/write alias is then serviced. Expected old data returns before the replacement write, replacement data reads back, and the untouched neighbor is preserved. Every write uses actual SRAM read/merge/encode/commit/rawACK/readback/verify/checkedACK stages. No positive-path ACK is forced.

The existing ICG clocks an extracted, source-identical `ot_hdc_vstream` progress bookkeeping block. A directed retirement pulse represents the held writer, and the exact core CHASE comparison is exercised at threshold1. Progress remains0 throughout the unpaid frame; only admitted native edges advance the counter to CHASE1 after checkedACK. This is a minimum progress-boundary test, not the actual complete SU pipeline, compiled program issue calendar, or proof of cross-family/reducer temporal interactions. CHASE1 is a directed obligation, not an assertion that these L20 opcodes request CHASE1.

Verilator5.050 measured read latency9 and checked-write latency28 physical edges, matching the existing prebuild model. Conflict frame58 edges, alias frame66, readback36; each initialization frame55. Total checkedACKs4, rawACKs4, physical reads5, held edges319, admitted native edges8. Negative controls reject a foreign postverified ACK owner without source advancement, bypassing the paid native gate, and premature CHASE progress. All three terminate with their expected fatal markers.

Source-pinned local inventory was recorded before build. Initial headroom was76GiB available RAM and195GiB disk, load5.8. Verilator built with two compile workers; the first build took29.49s with615712KiB maximum resident memory, and simulation took0.01s with7424KiB. The clean-negative revision's build resource record is retained. No runtime/build timeout or guessed address-space limit was applied.

The Icarus four-state run fails, and the unchanged predecessor bench also fails under the same source inventory. `four_state_failure/probe.log` establishes initialized provenance: base_word384 macro banks0/1/2/3 are0/0/0/40914576; base0 returnsbe916038/0/0/0; base128 returns0/c177f06a/0/0. Requested macro words contain the physically installed payloads. Adjacent words are knownzero from the pinned macro's original power-up array initialization (`OT_MEM_NO_INIT` is unset); that simulation assumption does not certify silicon startup. All four partial reduction operands are known at the observed boundary, but the original continuous `bank_word` result is X. A tiny same-shape net probe passes, so the precise simulator interaction remains unresolved.

The same four-state failure demonstrates an independent diagnostic weakness: `decoded != merged` evaluates X and the original checker publishes an ACK with unknown decoded data and known merged payload. Two-state PASS does not close this diagnostic gap or establish physical fault coverage. Failed evidence remains intact, and no source change hides it.

Reproduce the two-state protocol gate:

```sh
python3 tools/qwen_vm_su_service_gate.py --root . --out /tmp/qwen-service-new-run --verilator /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
```

The output directory must be new. Source hashes are checked, source copies and build inventory are pinned before compilation, and all negative markers are verified. To reproduce the four-state failure, compile the same six providers plus `progress.sv` and `four_state_failure/probe.sv` with Icarus (`-g2012 -s tb_qwen_su_service_gate`), then run with `+FIXTURE=` pointing to the pinned initial_x4096.u32.hex. The failure is intentional retained evidence, not a passing gate.
