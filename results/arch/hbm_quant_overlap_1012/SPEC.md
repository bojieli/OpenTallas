# Quant wide record overlap, Codex physical proposal

Source baseline: dff04245c (RTL 41c360152), WQ=2 DEC3.
The inherited production measurement is 751 cycles for 8 records / 3,328 exact words,
against unchanged price 168. It is a **serial transaction measurement**: the bench
waits for ret.done before presenting the next command. The DUT also serializes:
quant_unit st=4 waits for wide idle, and wide_h busy falls only after the full write
retirement drain. Neither a future concurrent issuer nor this specification proves
qualification. Required gate remains measured cycles <=184 (1.10 * 168 rounded down).

## Physical structure and cut budget, before RTL

Keep the 777.6 x 691.2 um hardened cluster and closed rq/wq/dxl/dbq/daq children
of qw_h3_ref. W=read lane interfaces, E=write lane interfaces, S=command/status.
Use the inherited M2-M7 cluster plan / M7 PG and each child's closed layer contract.
This is a control/metadata redesign, with no new wide arithmetic replicas or wide
VM ports. New logic belongs in the central controller region, x=270..570,
y=170..520, with a local spine leaf and at most ~15k top control sinks per leaf.
Face flops and child spine leaves stay explicit. No reset on data/header banks.

| Major cut | Existing signal envelope | Incremental overlap traffic | Supply budget / action |
|---|---:|---:|---|
| x=280, read strip to center | 4 x 1024-bit pair gathers + <=672 bits lane commands/events | 0 wide bits; compact beat metadata stays center | 691.2 um on horizontal M4/M6 gives about 25,200 nominal tracks at pitches 0.048/0.064; reserve 50% for PG/access/OBS -> 12,600; envelope 4,768 / 12,600=0.378 |
| x=570, center to write strip | 2 x 512-bit data relays + <=704 bits lane control/events | 0 external bits | same gross/reserved supply, 1,728 / 12,600=0.137 |
| y=345.6, upper/lower gathering and decoder column | <=6144 bits (gathers + decoder seams + result relay envelope) | <=7 x 18 compact header bits, <=33 destination/control bits | 777.6 um on vertical M3/M5/M7, pitches 0.036/0.048/0.064 -> about 49,950 nominal; 50% reserve -> 24,975; envelope 6,303 / 24,975=0.252 |
| center metadata seam, <=300 um reach | existing FIFO/control | 18-bit header + 15-bit destination + 1 last flag per beat | no new wide bus; 34 bits must receive reserved central tracks |

These are gross necessary cut envelopes, **not an OBS-aware legal capacity proof**.
The inherited children and SRAM obstruct some crossings. Before a new route/adoption,
scan the actual child LEF OBS along these cuts and each decoder channel; subtract
blocked tracks, and require demand / residual supply <=0.60. In particular the
narrow decoder-column channel must not be credited with the full cluster edge.
Existing f3/f3p routes remain live and must supply the real overflow/hold evidence.
If a residual cut exceeds 0.60, widen the channel/outline or place header relays
around the obstruction before RTL adoption; do not raise the layer cap.

W/E face flops to the associated child stay <=150 um. Command S face to center has
two relays <=450 um each. Existing center/corner event paths keep two relays.
Gather stages remain neighbour OR2 -> row OR2 -> decoder input, each <=500 um.
Compact header pipeline follows the gather stages; no header bank select drives
wide arithmetic directly. Stage target is ~700 ps, no added wide arbitration.

## Intended transaction structure (not implemented in this checkpoint)

1. Separate command admission from whole-engine drained. Accept the next eligible
   descriptor after the prior descriptor's last read issue, while gather/decode/
   result/write retirement continue. Packet fallback waits for wide drained.
   Cross-record A/O hazards require descriptor-span comparison against live
   descriptors; dependent records serialize. Nonoverlap production vectors may overlap.
2. Carry compact decoder header (18 significant bits), output sector, sector count
   and record-end identity with each issued beat in the NB-entry metadata queue.
   Read generation owns both source and destination progression. Gather no longer
   uses mutable global destination or mutable global header from a newer record.
3. Relay compact header with the five-stage gather-valid/launch chain. Edge audit:
   l_fire at L -> hit_p L -> hp2 L+1 -> gq L+2 -> gp L+3 -> go_h L+4 -> lx L+5
   -> launch L+6; decoder captures at L+7. Header captured at L must arrive for L+7.
   Validate mixed FP8/BF16/FP4 records and header-mutant exactness.
4. Keep read/result FIFO pointers continuous across commands. Resetting them on
   p_go would discard older records in flight. Reserve credits at issue/pop exactly
   as today; finite descriptor completion queue applies admission backpressure.
5. Track cumulative issued and done sectors per lane. On last input beat, enqueue
   all 32 lane targets (including the last beat). Retire the oldest record only
   after every lane reaches its target. A global sector sum alone is insufficient:
   later-record writes in a different lane can complete ahead of old writes.
   Pipeline/group the lane compares into local reductions; no 32-wide one-cycle
   completion arbitration. Modular counters need a bounded outstanding distance.
6. Faults close admission, drain accepted traffic, and preserve ordered completion
   semantics. Sticky decoder faults must not be cleared while older work is live.

## Evidence and implementation gates

`OVERLAP=1` in the bench admits on ret.ready independently of ret.done and monitors
completions separately. Default OVERLAP=0 preserves historical evidence. First run
both issuer modes against unchanged routed-source RTL to distinguish the harness
restriction from the DUT restriction. Then implement the above behind an opt-in
parameter. Run full production vectors, lane-map and bad-header mutants, mixed
operations, dependencies, finite credits and delayed lane completions. Require
m0 exact, w3 packet exact, m1/w1 fail in simulation, and <=1.10 unchanged price.
No reprice or output-hold budget changes. f3/f3p jobs remain untouched. A new route
must use ref_tile, registered drain/ready pins, and the current die contract.
