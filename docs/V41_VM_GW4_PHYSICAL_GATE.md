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
512.2 µm² standard-cell area for the quarter-width gate
([source-pinned record](../results/physical_abi3/asap7/chip/v41_vm_gw4_slice/synth_sta.json)).
The pre-route result alone does not establish routed closure.
The smallest 16-bit local write-control group also completed a standalone
ASAP7 route with 25% I/O delay: 0.92 ns timing met (2.265 GHz extracted
Fmax), 3,147 µm of routed wire, 7,717 vias, zero DRC and antenna violations,
and no hold violations
([routed group record](../results/physical_abi3/asap7/chip/v41_vm_gw4_slice/group16_io25_physical.json)).
This proves the local register/control cut is routable; the group has only
16 data bits and cannot establish timing for the full 2,048-bit path.

The **actual full 4 × 512-bit distributor** was also synthesized. It fails
pre-route timing at 0.92 ns by **1.498 ns**, because synthesis shares the
selector logic and the late 2,048-bit rotation creates a high-fanout path
([negative full-width record](../results/physical_abi3/asap7/chip/v41_vm_gw4_slice/full2048_synth_sta.json)).
The quarter-width passing result cannot be used to credit GW4 throughput.
The preferred boundary places each incoming word in the transpose buffer slot
selected by `word_addr[1:0]`; four completed slots then drive four **static**
512-bit bank wires. The full-width static register boundary passes pre-route
timing at 0.92 ns by 0.807 ns
([source-pinned record](../results/physical_abi3/asap7/chip/v41_vm_gw4_bank_order/synth_sta.json)).
This moves the word selection upstream to one arriving word per cycle. It
still needs the collective DMA's exact physical-bank-order implementation and
an integrated macro route before timing credit.
At 10% core utilization the standalone static-bank boundary had **4,209 I/O
pins but only 3,604 pin positions**; ORFS pin placement required a perimeter
of at least 404.06 µm rather than its 351.99 µm trial
([pin-placement failure record](../results/physical_abi3/asap7/chip/v41_vm_gw4_bank_order/physical.json)).
At 7% utilization the boundary completed standalone ASAP7 place and route:
4,209 pins fitted in 4,288 sites, **+0.426 ns routed setup WNS** and
**+0.077 ns hold WNS** at 0.92 ns, 94,248 µm routed wire, 64,423 vias,
zero DRC and antenna violations, and zero signal-integrity violations
([routed full-width boundary](../results/physical_abi3/asap7/chip/v41_vm_gw4_bank_order/physical_u7.json)).
This is a 4 × 512-bit *register boundary*, so it proves the four-bank data
width can be carried through this isolated cut. The collective transpose and
the SRAM macro pins remain outside it. The low-utilization floorplan reflects
the artificial all-bus-I/O partition, not an integrated die pin budget.

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
For source word address `B+j`, VM bank is `(B+j) mod 4` and that bank's row is
`floor((B+j)/4)`. An ACC base aligned to 32 FP32 elements can have `B mod 4 =
2`, so four consecutive input words may read two different physical bank
rows; the per-bank read addresses must retain that carry. The xbank's local
write row still advances once per 64-element beat.
The core and package controller must not request conflicting reads of the
same bank during this blocking preload.

The same four-bank read phase can supply HE's 20,480-element activation:
64 FP32 elements per cycle gives a **320-cycle read floor** before fill,
transpose, and drain. After BF16 rounding, the eight HCP banks each receive
one 128-bit word from a fixed 8×8 transpose of the four fetched VM words.
That fixed wiring still needs a registered four-quarter rotation when the
physical VM bank order differs from logical order, and an exact tile hook-up.

## Other vector-memory ports

Blocking COLL makes the core idle while this DMA writes, so one independent
read port per bank can serve its source stream concurrently with one write
port. Package-controller VM accesses must be blocked or arbitrated for that
interval. Outside COLL, the existing tile has many element and wide-word core
ports on one behavioural array; four 1R1W banks alone cannot implement those
ports. Full-VM macro mapping, replication or banking for the core, and an
integrated tile route remain separate physical blockers. This study cannot
establish the V4.1 full-die clock or token rate.
