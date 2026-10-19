# Regional SVG return prototype

`ot_hbm_svg_return_regional` is opt-in and changes no release master. Model
49668e988 preceded RTL 0c8f83652; final measured bench is 8e6003874.
Call `uarch_model.hbm_svg_return_regional_model()` for the seven-edge price.
No SDC, gate, submission, or physical closure is supplied.

## Mapping and timing

There are four independent pair stream roots and one cache stream root, all at
the same fixed frequency and matched phase. The component bench uses 834 ps
periods with source offsets 0/10/20/30 ps relative to the cache root. They are
mesochronous crossings with normal single-cycle timing, not asynchronous CDC.
Every root has two registered reset-release stages. Assert/release all resets
together; independent root resets during traffic are outside this contract.

Pair j contains landing banks j and j+4. The pin ordinal has a local copy in
each source root. Pair j selects high bank iff
`ordinal[2] XOR (j < ordinal[1:0])`. Each 16-bit slice has kept local ordinal
capture and two native payload captures. Selected pair words retain ordinal
and valid. The cache computes lane k from pair `(k+ordinal[1:0])%4` by registered
rotate-by-two and rotate-by-one stages. Selector copies use the corresponding
pair's ordinal, distributing control loads across four native ordinal ports.
All pair ordinals and valid bits must agree; disagreement sets sticky fault.

| Stage | Edge after input launch E0 | Action |
|---|---|---|
| Pair native pins | E1 | Capture both 256-bit inputs and ordinal/valid |
| Pair select | E2 | Registered 2:1 selected payload |
| Source ring | E3 | Write actual four-slot ring |
| Receiver landing | E4 | Capture previous slot on cache root |
| Cache native pins | E5 | Capture four pair words |
| Rotation by two | E6 | Registered ordinal[1] rotation |
| Rotation by one | E7 | Registered ordinal[0] rotation and output |

Thus this is seven capture edges from launch, or six full periods from native
input capture E1 to output capture E7. The bench measures launch-to-output
minimum=maximum=7 on every valid group. After balanced raw reset release, reset
landing consumes E1/E2, first accepted source pins are E3, and first valid
output is E9. Bubbles retain their fixed positions; there is no ready/credit.
Parent valid/mask/ordinal/bank/epoch/last alignment must use an actual seven-edge
ring/SRAM implementation and pay this complete latency in prefetch timing.

## Ring and functional storage

Each pair ring stores 256 payload + ordinal3 + valid1 + source phase3, i.e.
263 bits x four slots = 1052 bits. Seventeen kept slices carry 16 bits each
(last slice seven bits), with local source write and receiver read pointers.
The receiver reads the previous source slot: pointers start write0/read3.
Source phase modulo eight is stored with each word and compared with the
expected receiver phase, so a wrong/stale slot is detected independently of
ordinal equality. Valid alone has reset/warmup masking; payload flops do not
have a reset mass. The read data, ordinal and valid are receiver registers.

This is a real indexed ring, not four sequential flop copies. The source ring
Q, read mux/select and receiver register paths must all be timed normally.
The source-local read mux placement is not constrained or measured here:
exporting 263 selected data wires requires that mux placement; a receiver-local
mux would expose 1052 source-slot wires. Destination read-pointer copies add
control crossings. Fanout, wire reach and round-trip select delay therefore
remain physical audit items; this prototype does not claim a closed boundary.

The cache's three-edge ordinal/valid alignment uses a separate actual four-slot
four-bit ring (write0/read2), avoiding a three-flop metadata shift chain.
The cache data pipeline has 3072 active functional registers across capture,
rotation by two and rotation by one, split into sixteen kept 16-bit slices.
These compute stages are not an indexed payload store or unchanged delay line.
Selector control delays are at most two registers.

## Native port mapping

Top ports are `pair_clk[3:0]`, `pair_rst_n[3:0]`, `cache_clk`, `cache_rst_n`,
`bank_data[2047:0]`, `in_ordinal[11:0]`, and `in_valid[3:0]`.
Bank b occupies `bank_data[b*256+:256]`. Pair j's local ordinal occupies
`in_ordinal[j*3+:3]`; valid j is the common read-group validity in that root.
Output lanes k occupy `out_data[k*256+:256]`, followed by registered
`out_ordinal[2:0]`, `out_valid`, and sticky `fault` on the cache root.
Parent masks the final partial group; valid is a group flag, not a per-lane mask.

A return-only pair receives 512 data + ordinal3 + valid1 + clock/reset2 = 518
native input pins. Its selected word is 260 bits; the tagged ring is 263 bits.
The cache receives 1024 data + ordinal12 + valid4 + phase-fault4 + clock/reset2
= 1046 pins, and exports 1024 data + ordinal3 + valid1 + fault1 = 1029 pins.
These logical counts do not establish a legal physical face plan.

## Component qualification

Fleet Verilator 5.050, source 8e6003874, checks every full ordinal 0..271 twice
per reset (one full-rate sweep and one bubble sweep), varying all eight banks'
256-bit payloads. Three episodes include occupied pipeline resets, ring wraps,
and exact warmup. The independent oracle directly selects banks
`(ordinal+lane)%8`, checks seven-edge payload/ordinal/valid alignment, and tests
an explicit ordinal-disagreement fault after the nominal sweeps.

PASS: 1632 groups; every measured delay exactly seven edges; first output at
reset-release edge nine in all three episodes; three windows of 64 groups in
64 cache edges = 128 payload bytes/edge, II=1.
Mutant1 inverts pair0 selection: RETURN_DATA_FAIL, 1632 errors.
Mutant2 inverts rotate-by-one: RETURN_DATA_FAIL, 1632 errors.
Mutant3 reads the wrong ring slot: RING_PHASE_FAIL plus data/valid/fault failures.
Witnesses are committed under `rtl/test/hbm_accel/svg_rel/svg_return_evidence/`.

## Pre-gate safe-design checklist

1. Fixed at RTL: native data/control captures, registered outputs, two-stage
   reset landing per root; reset distribution still needs mapped review.
2. OPEN: source pair, cache and crossing placement/reach <=405 um, including
   source-local read mux location and destination select return, unmeasured.
3. Fixed in structure: kept 16-bit pair/rotate selects, kept ring pointer
   slices, native ordinal copies. Mapped preservation and <=32 loads unverified.
4. Fixed latency/no pin-to-pin combinational bypass. Normal one-edge crossing
   and mux depth require actual timing; no timing exception is authorized.
5. PASS logically: per-pair ring1052 bits, cache metadata ring16 bits; no large
   indexed flop memory or >=3-stage unchanged metadata delay chain.
6. OPEN: source-bound landing+pair macro floorplan and synthesis-based cache
   outline, macro access, full-width cell band and external face density.
7. Fixed native roots/reset contract; insertion/spread, neighbour references,
   TT/FF pin-flop spread <=80 ps and hold margin >=0.03 ns remain unmeasured.
8. Model PASS: fixed seven edges and II=1 measured; parent compilation and
   prefetch/metadata integration remain necessary before adoption.
