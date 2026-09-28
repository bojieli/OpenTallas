# Four-bank collective destination: physical gate

The adopted V4.1 output-row split needs the all-gather to write four 64-byte
vector-memory words per cycle. The current tile's external B port writes one
word per cycle into a behavioural `vm` array. This gate studies the new write
boundary; it is not a route of the complete vector memory or the die.

## Port and bank mapping

The collective emits four consecutive *word* addresses per beat, with per-word
strobes. Word address bits `[1:0]` select four independent 512-bit write banks;
the remaining bits select the row. Consecutive addresses hit distinct banks
even when a rank starts at a non-four-word boundary, as happens when `n=266`.
The [write-distributor slice](../rtl/chip/physical/ot_v41_vm_gw4_slice.sv)
models one 128-bit quarter of the path. Four identical slices form the 512-bit
datapath. A register after the two-bit rotation bounds the combinational
collective-to-SRAM path. Its [test](../rtl/test/tb_v41_vm_gw4_slice.sv) covers
all four starting alignments and all 16 write-strobe masks (64 cases).

The two-stage distributor adds two cycles from input acceptance to SRAM write
pins. `coll_busy` must remain high
until the final bank write commits, including partial final beats. A fault or
new command must not discard that registered write.

A one-stage 128-bit slice failed pre-route ASAP7 timing at 0.92 ns
(−0.827 ns WNS) because the select flop drove 512 data mux bits. The
two-stage slice duplicates bank select in 16-bit local groups. Its pre-route
STA is **+0.214 ns WNS** at 0.92 ns, with 2,844 mapped standard cells and
512.2 µm² standard-cell area for the quarter-width gate. The full-route
verdict is separately recorded in
[`physical.json`](../results/physical_abi3/asap7/chip/v41_vm_gw4_slice/physical.json)
when available; the pre-route result alone does not establish routed closure.

## SRAM abstract and capacity

The full-shape requirement is 454,848 resident FP32 elements per die, rounded
to a 524,288-element VM. This is 32,768 words of 64 bytes, or 8,192 words per
bank. With the checked-in ASAP7 `ot_sram_1r1w_512x128_m4_r2c2` abstract,
each 512-bit bank word requires four macros in parallel and each bank depth
requires 16 macro rows. The four banks therefore use **256 macros**, with
**1.324 mm² of macro-only area**. The abstract's TT one-write cycle is
361 ps. Its modeled energy for four simultaneous 64-byte word writes is
14.1 pJ, excluding selection, clock, and wires. Exact input, formulae, and
source SHA are in
[`v41_vm_gw4_macro_gate.json`](../results/physical_abi3/asap7/chip/v41_vm_gw4_macro_gate.json).

These are generated memory-compiler abstracts, not measured silicon SRAM or
an integrated macro route. The 1.324 mm² excludes placement channels,
per-bank depth selection, clock distribution, and the 2,048-bit data path.
Banking itself need not quadruple capacity: the same 2 MiB is partitioned into
four banks, but it requires four independent write paths.

## ME activation preload from the same banks

In a separate ME-preload phase, the four independent read ports can supply
four consecutive 64-byte VM words each cycle, or 64 FP32 elements / 256 bytes
per cycle. A 4,096-element activation group therefore has a **64-cycle read
floor**, and two groups have a **128-cycle read floor**, before latency and
drain. The abstract gives a TT read cycle of 381 ps and modeled macro read
energy of 7.09 pJ per four-word beat. No extra SRAM port or capacity is needed;
the write and read bank resources serve distinct phases. The tile currently
has only one 64-byte external-B read per cycle, so a four-read interface,
bank-local registered output, and a 256-byte/cycle ME xbank ingest are still
required. A direct 2,048-bit read-to-logical-order crossbar was tested as a
quarter-width slice and failed pre-route 0.92 ns timing by 1.06 ns; its
negative probe is in
[`v41_vm_gr4_slice/synth_sta.json`](../results/physical_abi3/asap7/chip/v41_vm_gr4_slice/synth_sta.json).
The ME xbank can instead retain physical VM bank order and latch the initial
word-address modulo four. On term read, that two-bit rotation selects the
corresponding xbank group. This removes the wide crossbar from the preload
write path, but its xbank implementation and timing gate are separate work.
The core and package controller must not request conflicting reads of the
same bank during this blocking preload.

## Other vector-memory ports

Blocking COLL makes the core idle while this DMA writes, so one independent
read port per bank can serve its source stream concurrently with one write
port. Package-controller VM accesses must be blocked or arbitrated for that
interval. Outside COLL, the existing tile has many element and wide-word core
ports on one behavioural array; four 1R1W banks alone cannot implement those
ports. Full-VM macro mapping, replication or banking for the core, and an
integrated tile route remain separate physical blockers. This study cannot
establish the V4.1 full-die clock or token rate.
